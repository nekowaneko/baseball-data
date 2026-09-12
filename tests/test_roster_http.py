#真實 NPB 名冊解析測試：用實際抓下來的頁面快照，全程不連網
import os

import pytest

from adapters import roster_http
from core.match import norm_name


#2026 年度樂天名冊頁面的快照（實際抓取，未修改）
@pytest.fixture(scope='session')
def roster_html(fixtures_dir):
    with open(os.path.join(fixtures_dir, 'npb', 'rst_e.html'), encoding='utf-8') as f:
        return f.read()


#支配下與育成的投手都要收到，且只收投手
def test_parse_roster(roster_html):
    players = roster_http.parse_roster(roster_html)
    assert len(players) == 41
    assert all(p['hand'] in ('R', 'L') for p in players)
    assert {'name', 'hand'} == set(players[0])
    assert sum(1 for p in players if p['hand'] == 'L') == 10


#野手不得混進來：名冊裡的捕手、内野手、外野手都有「投」欄，收進來會汙染姓名回退
def test_excludes_fielders(roster_html):
    names = {norm_name(p['name']) for p in roster_http.parse_roster(roster_html)}
    assert '辰己涼介' not in names   #外野手
    assert '太田光' not in names     #捕手
    assert '岸孝之' in names         #投手


#解析結果與既有的 82 筆左右手對照表在樂天這一隊完全一致（回歸基準）
def test_agrees_with_hands_fixture(roster_html, fixtures_dir):
    parsed = {norm_name(p['name']): p['hand']
              for p in roster_http.parse_roster(roster_html)}
    expected = {}
    with open(os.path.join(fixtures_dir, 'hands_raw.txt'), encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            team, name, hand = line.split(',')
            if team == '楽天':
                expected[norm_name(name)] = hand
    assert expected
    for name, hand in expected.items():
        assert parsed.get(name) == hand, f'{name} 的左右手與既有對照表不一致'


#HTTP 標頭只能是 latin-1，User-Agent 不可含非 ASCII 字元
def test_user_agent_is_ascii():
    roster_http.USER_AGENT.encode('latin-1')


#表格結構不符時回傳空清單，不拋例外也不猜
def test_unknown_structure():
    assert roster_http.parse_roster('<html><table><tr><td>x</td></tr></table></html>') == []


#快取有效期：沒有檔案或沒有日期一律視為過期
def test_cache_fresh(tmp_path):
    missing = tmp_path / 'nope.json'
    assert roster_http.cache_fresh(str(missing), 7) is False
    no_date = tmp_path / 'rst_x.json'
    no_date.write_text('{"players": []}', encoding='utf-8')
    assert roster_http.cache_fresh(str(no_date), 7) is False
