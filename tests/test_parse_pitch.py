#球種別成績解析測試
from core import parse_pitch


#對右與對左各一張表，依表格前的標籤判定歸屬
def test_split_tables(page):
    data = parse_pitch.parse_pitch_types(page('pitch'))
    assert set(data) == {'対右投手', '対左投手'}
    assert len(data['対右投手']) == 14
    assert len(data['対左投手']) == 10


#欄位取自表頭，球種名稱與既有設定的球種一致
def test_rows(page, load_config):
    data = parse_pitch.parse_pitch_types(page('pitch'))
    row = data['対右投手'][0]
    assert row['pitch'] == 'ストレート'
    assert row['share'] == '37.5%'
    order = load_config('pitch_meta.json')['order']
    for side in data.values():
        for item in side:
            assert item['pitch'] in order


#沒有球種表時回傳空字典
def test_missing_table():
    assert parse_pitch.parse_pitch_types('<html></html>') == {}
