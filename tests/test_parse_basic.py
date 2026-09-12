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


#找不到目標表格時回傳空字典，不拋例外
def test_missing_table():
    assert parse_basic.parse_split_totals('<html></html>') == {}
    assert parse_basic.parse_team_totals('<html></html>') == {}
