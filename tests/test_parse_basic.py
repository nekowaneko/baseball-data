#基本成績分頁解析測試
from core import parse_basic


#對左右別合計就是交叉驗證用的官方值，黃金值為對左 52 打數 8 安打
def test_split_totals(page):
    totals = parse_basic.parse_split_totals(page('basic'))
    assert totals['L'] == {'ab': 52, 'h': 8, 'hr': 2}
    assert totals['R'] == {'ab': 157, 'h': 41, 'hr': 6}


#球團別合計只收有對戰紀錄的球團，整列破折號代表沒對戰過
def test_team_totals(page):
    totals = parse_basic.parse_team_totals(page('basic'))
    assert totals['ソフトバンク'] == {'ab': 52, 'h': 8, 'hr': 2}
    assert totals['ロッテ']['ab'] == 35
    assert '西武' not in totals
    assert '広島' not in totals


#顯示欄位連原站算好的率值一起帶走，字串照原樣不動（綜觀摘要條要用）
def test_split_display(page):
    display = parse_basic.parse_split_display(page('basic'))
    assert display['L'] == {'ops': '.451', 'avg': '.154', 'hr': '2',
                            'obp': '.182', 'k': '32.7%', 'ab': '52', 'h': '8'}
    assert display['R']['ops'] == '.797'
    assert display['R']['k'] == '22.6%'


#顯示欄位與可加總欄位取自同一張表，打數安打必須一致，避免兩套數字對不上
def test_split_display_agrees_with_totals(page):
    display = parse_basic.parse_split_display(page('basic'))
    totals = parse_basic.parse_split_totals(page('basic'))
    for hand in ('L', 'R'):
        assert int(display[hand]['ab']) == totals[hand]['ab']
        assert int(display[hand]['h']) == totals[hand]['h']


#找不到目標表格時回傳空字典，不拋例外
def test_missing_table():
    assert parse_basic.parse_split_totals('<html></html>') == {}
    assert parse_basic.parse_team_totals('<html></html>') == {}
    assert parse_basic.parse_split_display('<html></html>') == {}


#從分頁標題抓球員名，去空白後可直接接上「配球對照表」
def test_parse_player_name(page):
    assert parse_basic.parse_player_name(page('basic')) == '林安可'


#標題認不出來時回空字串，不猜、不拿檔名湊
def test_parse_player_name_unknown():
    assert parse_basic.parse_player_name('<html><head><title>沒有格式</title></head></html>') == ''
    assert parse_basic.parse_player_name('<html></html>') == ''
