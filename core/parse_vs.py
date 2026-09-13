#逐投手對戰成績解析（matchup 分頁）
from bs4 import BeautifulSoup

#表頭欄位對應到輸出鍵，缺欄就跳過該欄
VS_COLUMNS = {
    '投手': 'name', 'OPS': 'ops', '打率': 'avg',
    '打数': 'ab', '安打': 'h', '本塁打': 'hr', '三振': 'so',
}
NUM_FIELDS = ('ab', 'h', 'hr', 'so')  #可精確相加的欄位，其餘保留原字串


#把表格文字轉成整數，破折號與空字串一律當 0
def to_int(text):
    digits = ''.join(c for c in text if c.isdigit() or c == '-')
    try:
        return int(digits)
    except ValueError:
        return 0


#取出一列的儲存格文字
def _cells(row):
    return [c.get_text(strip=True) for c in row.find_all(['th', 'td'])]


#表格是否為逐投手成績表：第一欄表頭必須是「投手」
def _is_pitcher_table(table):
    rows = table.find_all('tr')
    if not rows:
        return False
    head = _cells(rows[0])
    return bool(head) and head[0] == '投手'


#把一列資料依表頭對成 dict
def _row_to_pitcher(head, cells):
    row = {}
    for key, value in zip(head, cells):
        field = VS_COLUMNS.get(key)
        if not field:
            continue
        row[field] = to_int(value) if field in NUM_FIELDS else value
    return row


#解析逐投手對戰成績，回傳 {球團: [{name, ops, avg, ab, h, hr, so}]}
def parse_vs_pitchers(html_text):
    soup = BeautifulSoup(html_text, 'html.parser')
    result = {}
    for table in soup.find_all('table'):
        if not _is_pitcher_table(table):
            continue
        heading = table.find_previous('h2')
        team = heading.get_text(strip=True) if heading else '不明'
        rows = table.find_all('tr')
        head = _cells(rows[0])
        pitchers = [_row_to_pitcher(head, _cells(r)) for r in rows[1:] if _cells(r)]
        result.setdefault(team, []).extend(p for p in pitchers if p.get('name'))
    return result
