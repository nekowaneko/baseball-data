#球種 × 左右投表格解析（pitch 分頁）
from bs4 import BeautifulSoup

#區塊標籤，決定表格屬於對右還是對左
SPLIT_LABELS = ('対右投手', '対左投手')
#表頭欄位對應到輸出鍵
PITCH_COLUMNS = {
    '球種': 'pitch', '割合': 'share', '平均球速(km/h)': 'speed',
    '空振り%': 'whiff', 'OPS': 'ops', '打率': 'avg', '本塁打': 'hr',
}


#取出一列的儲存格文字
def _cells(row):
    return [c.get_text(strip=True) for c in row.find_all(['th', 'td'])]


#表格是否為球種別成績表：第一欄表頭必須是「球種」
def _is_pitch_table(table):
    rows = table.find_all('tr')
    if not rows:
        return False
    head = _cells(rows[0])
    return bool(head) and head[0] == '球種'


#往前找最近的左右投標籤，找不到回傳 None
def _split_label(table):
    for node in table.find_all_previous(string=True):
        text = node.strip()
        if text in SPLIT_LABELS:
            return text
    return None


#把一列依表頭對成 dict
def _row_to_pitch(head, cells):
    return {PITCH_COLUMNS[key]: value
            for key, value in zip(head, cells) if key in PITCH_COLUMNS}


#解析球種別打擊成績，回傳 {'対右投手': [{pitch, share, ...}], '対左投手': [...]}
def parse_pitch_types(html_text):
    soup = BeautifulSoup(html_text, 'lxml')
    result = {}
    for table in soup.find_all('table'):
        if not _is_pitch_table(table):
            continue
        label = _split_label(table)
        if label is None:
            continue
        rows = table.find_all('tr')
        head = _cells(rows[0])
        result[label] = [_row_to_pitch(head, _cells(r)) for r in rows[1:] if _cells(r)]
    return result
