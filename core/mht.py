#MHT 拆封與分頁分類
import email
from email import policy

#分頁特徵：出現任一關鍵字即判定為該分頁，順序即優先序
PAGE_MARKERS = [
    ('mix', ['カウント別の配球']),
    ('pitch', ['球種別の打撃成績']),
    ('situational', ['状況別の打撃成績', '球場別の対戦成績']),
    ('vs', ['>投手</th>', '>投手</td>']),
    ('basic', ['対左右別の対戦成績', 'チーム別の対戦成績']),
]


#把單一 MIME 部件解成文字，MHT 常缺 charset 宣告，一律當 UTF-8
def _decode_part(part):
    raw = part.get_payload(decode=True)
    if raw is None:  #binary 編碼時 get_payload 可能回傳 None
        return ''
    charset = part.get_content_charset() or 'utf-8'
    return raw.decode(charset, 'replace')


#拆封 MHT 容器，回傳 {Content-Location: HTML 文字}，只取 text/html 部件
def unpack_mht(raw_bytes):
    msg = email.message_from_bytes(raw_bytes, policy=policy.default)
    pages = {}
    for part in msg.walk():
        if part.get_content_type() != 'text/html':
            continue
        location = part.get('Content-Location') or ''
        pages[location] = _decode_part(part)
    return pages


#取主文件：優先用 Snapshot-Content-Location 指定的部件，否則取最長的一份
def main_page(raw_bytes):
    msg = email.message_from_bytes(raw_bytes, policy=policy.default)
    snapshot = msg.get('Snapshot-Content-Location')
    pages = unpack_mht(raw_bytes)
    if snapshot and snapshot in pages:
        return pages[snapshot]
    if not pages:
        return ''
    return max(pages.values(), key=len)


#依內容特徵判斷分頁種類，檔名不可靠所以不看檔名
def classify_page(html_text):
    if not html_text:
        return None
    for kind, markers in PAGE_MARKERS:
        if any(marker in html_text for marker in markers):
            return kind
    return None
