#MHT 拆封與分頁分類測試
import os

import pytest

from core import mht

PAGES = ['basic', 'mix', 'pitch', 'situational', 'vs']
EXPECTED_KIND = {
    'basic': 'basic', 'mix': 'mix', 'pitch': 'pitch',
    'situational': 'situational', 'vs': 'vs',
}


#五份 fixture 都能拆出非空的主文件
@pytest.mark.parametrize('name', PAGES)
def test_main_page_not_empty(name, page):
    html = page(name)
    assert len(html) > 10000
    assert '<html' in html


#檔名不可靠，分類必須依內容特徵判斷
@pytest.mark.parametrize('name', PAGES)
def test_classify_page(name, page):
    assert mht.classify_page(page(name)) == EXPECTED_KIND[name]


#拆封結果是「位置 → HTML」的對照，主文件必在其中
def test_unpack_returns_locations(fixtures_dir):
    path = os.path.join(fixtures_dir, 'mht', 'short-stop-vs.mht')
    with open(path, 'rb') as f:
        raw = f.read()
    pages = mht.unpack_mht(raw)
    assert any('short-stop.jp' in loc for loc in pages)
    assert mht.main_page(raw) in pages.values()


#無法辨識的內容回傳 None，不猜
def test_classify_unknown():
    assert mht.classify_page('<html><body>沒有任何特徵</body></html>') is None
    assert mht.classify_page('') is None
