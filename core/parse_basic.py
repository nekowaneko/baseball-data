#基本成績分頁解析：對左右別合計與球團別合計（稽核與交叉驗證的官方值來源）
import re
import unicodedata

from bs4 import BeautifulSoup

from core.parse_vs import to_int

#對左右別表格的列標籤對應到左右手代號
HAND_LABELS = {'対右': 'R', '対左': 'L', '対不明': 'U'}
#表頭欄位對應到輸出鍵（只取可相加的欄位，稽核與交叉驗證用）
TOTAL_COLUMNS = {'打数': 'ab', '安打': 'h', '本塁打': 'hr'}
#顯示用欄位：原站已算好的率值，照字串原樣搬走，絕不自行加總或重算
DISPLAY_COLUMNS = {'OPS': 'ops', '打率': 'avg', '本塁打': 'hr', '出塁率': 'obp',
                   'K％': 'k', '打数': 'ab', '安打': 'h'}
#視為「沒有資料」的儲存格文字
BLANKS = ('—', '-', '')


#取出一列的儲存格文字
def _cells(row):
    return [c.get_text(strip=True) for c in row.find_all(['th', 'td'])]


#找出第一欄表頭等於指定文字的表格
def _find_table(soup, first_header):
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        if not rows:
            continue
        head = _cells(rows[0])
        if head and head[0] == first_header:
            return table
    return None


#把一列依表頭抽出可加總欄位，整列皆為破折號時回傳 None（代表沒對戰過）
def _row_totals(head, cells):
    values = {}
    has_data = False
    for key, value in zip(head, cells):
        field = TOTAL_COLUMNS.get(key)
        if not field:
            continue
        values[field] = to_int(value)
        if value not in ('—', '-', ''):
            has_data = True
    return values if has_data else None


#解析「対左右別の対戦成績」，回傳 {'R': {ab, h, hr}, 'L': {...}, 'U': {...}}
def parse_split_totals(html_text):
    soup = BeautifulSoup(html_text, 'html.parser')
    table = _find_table(soup, '条件')
    if table is None:
        return {}
    rows = table.find_all('tr')
    head = _cells(rows[0])
    totals = {}
    for row in rows[1:]:
        cells = _cells(row)
        hand = HAND_LABELS.get(cells[0] if cells else '')
        if not hand:
            continue
        values = _row_totals(head, cells)
        if values is not None:
            totals[hand] = values
    return totals


#解析「対左右別の対戦成績」的顯示欄位，回傳 {'R': {ops, avg, obp, k, ab, ...}, 'L': {...}}
#與 parse_split_totals 的差別：這裡連率值一起帶走，只為了畫面呈現，不參與任何計算
def parse_split_display(html_text):
    soup = BeautifulSoup(html_text, 'html.parser')
    table = _find_table(soup, '条件')
    if table is None:
        return {}
    rows = table.find_all('tr')
    head = _cells(rows[0])
    display = {}
    for row in rows[1:]:
        cells = _cells(row)
        hand = HAND_LABELS.get(cells[0] if cells else '')
        if not hand:
            continue
        values = {DISPLAY_COLUMNS[key]: value
                  for key, value in zip(head, cells) if key in DISPLAY_COLUMNS}
        if any(v not in BLANKS for v in values.values()):
            display[hand] = values
    return display


#解析「チーム別の対戦成績」，回傳 {球團: {ab, h, hr}}，未對戰過的球團不列入
def parse_team_totals(html_text):
    soup = BeautifulSoup(html_text, 'html.parser')
    table = _find_table(soup, 'チーム')
    if table is None:
        return {}
    rows = table.find_all('tr')
    head = _cells(rows[0])
    totals = {}
    for row in rows[1:]:
        cells = _cells(row)
        if not cells:
            continue
        values = _row_totals(head, cells)
        if values is not None:
            totals[cells[0]] = values
    return totals


#Short-Stop 每個分頁的標題格式都是「林 安可 成績 2026 | Short-Stop」，
#球員名在「成績」與年份之前。抓不到就回空字串，讓報表退回沒有名字的標題，絕不猜。
PLAYER_TITLE = re.compile(r'^\s*(?P<name>.+?)\s*成績\s*\d{4}\s*(?:\||$)')


#解析球員名。回傳去掉所有空白的顯示名（例：林安可），供報表標題使用
def parse_player_name(html_text):
    soup = BeautifulSoup(html_text, 'html.parser')
    title = soup.title.get_text(strip=True) if soup.title else ''
    matched = PLAYER_TITLE.match(unicodedata.normalize('NFKC', title))
    if not matched:
        return ''
    #「林 安可」在中文語境寫成「林安可」，去空白後才能直接接上「配球對照表」
    return ''.join(matched.group('name').split())
