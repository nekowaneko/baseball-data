#逐投手對戰成績解析測試
from core import parse_vs


#解析結果必須與既有產出 vs_pitchers.json 完全一致（回歸基準）
def test_matches_golden_fixture(page, load_json):
    parsed = parse_vs.parse_vs_pitchers(page('vs'))
    assert parsed == load_json('vs_pitchers.json')


#球團鍵為 Short-Stop 的完整隊名，共八隊
def test_team_keys(page):
    parsed = parse_vs.parse_vs_pitchers(page('vs'))
    assert len(parsed) == 8
    assert '楽天Eagles' in parsed
    assert 'DeNABayStars' in parsed


#可加總欄位為整數，OPS 與打率保留原字串（無法相加）
def test_field_types(page):
    row = parse_vs.parse_vs_pitchers(page('vs'))['楽天Eagles'][0]
    for field in ('ab', 'h', 'hr', 'so'):
        assert isinstance(row[field], int)
    assert isinstance(row['ops'], str)


#破折號與空字串一律當 0，不得讓例外中斷解析
def test_to_int_handles_dash():
    assert parse_vs.to_int('—') == 0
    assert parse_vs.to_int('') == 0
    assert parse_vs.to_int('12') == 12
