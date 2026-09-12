#球團 × 左右投 × 球數 × 球種配球解析（vs-team 分頁）
import re

from bs4 import BeautifulSoup, NavigableString

#區塊標題：帶標籤形式才算，按鈕的 title 屬性也含「対左投手」字樣，用純字串比對會在錯誤位置切開
SPLIT_HEADINGS = ('対右投手', '対左投手')
TOTAL_KEY = '合計'
COUNT_PATTERN = re.compile(r'^\d-\d$')  #球數標籤形如 0-0、3-2
TITLE_PATTERN = re.compile(r'^(.+?): ([0-9.]+)%$')  #色塊的 title 形如「ストレート: 44.2%」


#判斷 h2 是否為左右投區塊標題
def _is_split_heading(text):
    return text in SPLIT_HEADINGS


#取出頁面上所有 h2，回傳 [(標題文字, 元素)]
def _headings(soup):
    return [(h.get_text(strip=True), h) for h in soup.find_all('h2')]


#收集某個 h2 之後、下一個標題之前的所有球數列，用文件順序走訪避免跨區
def _rows_between(heading, next_heading):
    rows = []
    for node in heading.next_elements:
        if node is next_heading:
            break
        if isinstance(node, NavigableString) and COUNT_PATTERN.match(node.strip()):
            rows.append(_row_from_label(node.parent))
    return rows


#由球數標籤往上找同一列容器，取出該列全部色塊
def _row_from_label(holder):
    count = holder.get_text(strip=True)
    row = holder.parent
    mix = {}
    if row is not None:
        for block in row.find_all(attrs={'title': True}):
            matched = TITLE_PATTERN.match(block['title'].strip())
            if matched:
                mix[matched.group(1)] = float(matched.group(2))
    return {'count': count, 'mix': mix}


#解析球團配球，回傳 {球團: {'合計'|'対右投手'|'対左投手': [{count, mix}]}}
def parse_team_mix(html_text):
    soup = BeautifulSoup(html_text, 'lxml')
    headings = _headings(soup)
    #只保留球團標題與左右投標題，其餘（如頁面大標）忽略
    marks = list(headings)
    result = {}
    team = None
    for index, (text, node) in enumerate(marks):
        following = marks[index + 1][1] if index + 1 < len(marks) else None
        if _is_split_heading(text):
            if team is None:
                continue
            result[team][text] = _rows_between(node, following)
        else:
            team = text
            result[team] = {TOTAL_KEY: _rows_between(node, following)}
    #淘汰沒有任何球數列的候選（例如頁面大標）
    return {team: sections for team, sections in result.items()
            if any(sections.values())}


#球團標題的判定：不是左右投標題就視為候選球團，最後再淘汰沒有任何球數列的候選
def _looks_like_team(text):
    return not _is_split_heading(text)
