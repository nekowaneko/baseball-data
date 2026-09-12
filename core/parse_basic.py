#基本成績分頁解析：對左右別合計與球團別合計（稽核與交叉驗證的官方值來源）
from bs4 import BeautifulSoup

from core.parse_vs import to_int

#對左右別表格的列標籤對應到左右手代號
HAND_LABELS = {'対右': 'R', '対左': 'L', '対不明': 'U'}
#表頭欄位對應到輸出鍵
TOTAL_COLUMNS = {'打数': 'ab', '安打': 'h', '本塁打': 'hr'}


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
    soup = BeautifulSoup(html_text, 'lxml')
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


#解析「チーム別の対戦成績」，回傳 {球團: {ab, h, hr}}，未對戰過的球團不列入
def parse_team_totals(html_text):
    soup = BeautifulSoup(html_text, 'lxml')
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
