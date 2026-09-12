#一致性稽核測試
from core import audit, parse_basic


#稽核能抓出軟銀缺 16 打數、羅德缺 1 打數（驗收項 V12）
def test_detects_known_gaps(load_json, page):
    vs_data = load_json('vs_pitchers.json')
    team_totals = parse_basic.parse_team_totals(page('basic'))
    diffs = audit.audit_totals(vs_data, team_totals)
    found = {(d['team'], d['field']): d for d in diffs}
    assert found[('ソフトバンク', 'ab')]['diff'] == 16
    assert found[('ソフトバンク', 'ab')]['parsed'] == 36
    assert found[('ソフトバンク', 'ab')]['official'] == 52
    assert found[('ロッテ', 'ab')]['diff'] == 1


#完全吻合的球團不會出現在差異清單
def test_matching_teams_absent(load_json, page):
    vs_data = load_json('vs_pitchers.json')
    team_totals = parse_basic.parse_team_totals(page('basic'))
    teams = {d['team'] for d in audit.audit_totals(vs_data, team_totals)}
    assert '楽天' not in teams
    assert '日本ハム' not in teams
    assert 'オリックス' not in teams


#官方表缺該球團時照樣列出差異，不靜默略過
def test_missing_official_row(load_json, page):
    vs_data = load_json('vs_pitchers.json')
    team_totals = parse_basic.parse_team_totals(page('basic'))
    diffs = audit.audit_totals(vs_data, team_totals)
    hanshin = [d for d in diffs if d['team'] == '阪神' and d['field'] == 'ab']
    assert hanshin and hanshin[0]['official'] == 0


#兩邊完全一致時回傳空清單
def test_no_diff():
    vs_data = {'楽天Eagles': [{'name': 'A', 'ab': 3, 'h': 1, 'hr': 0, 'so': 1}]}
    assert audit.audit_totals(vs_data, {'楽天': {'ab': 3, 'h': 1, 'hr': 0}}) == []
