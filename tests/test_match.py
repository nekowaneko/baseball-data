#姓名正規化與左右手比對測試
import pytest

from core import match

ROSTER = [
    {'team': 'ソフトバンク', 'name': '藤原 大翔', 'hand': 'R'},
    {'team': '楽天', 'name': '早川 隆久', 'hand': 'L'},
    {'team': '楽天', 'name': '岸 孝之', 'hand': ''},  #名冊沒寫左右手就不收
]


#全半形空白與空白寫法差異都要正規化成同一個鍵（驗收項 V06）
@pytest.mark.parametrize('raw', [
    '早川 隆久', '早川　隆久', '早川隆久', ' 早川 隆久 ', '早川　隆久',
])
def test_norm_name_same_key(raw):
    assert match.norm_name(raw) == '早川隆久'


#全形英數會被 NFKC 收斂成半形，異體字寫法則原樣保留（不做模糊比對）
def test_norm_name_nfkc():
    assert match.norm_name('ＤｅＮＡ') == 'DeNA'
    assert match.norm_name('山﨑 福也') == '山﨑福也'
    assert match.norm_name(None) == ''


#球團名正規化：去掉 Short-Stop 的英文後綴，取最長的已知簡稱
@pytest.mark.parametrize('raw,expected', [
    ('楽天Eagles', '楽天'),
    ('日本ハムFighters', '日本ハム'),
    ('DeNABayStars', 'DeNA'),
    ('ヤクルトSwallows', 'ヤクルト'),
    ('無此球団', '無此球団'),
])
def test_norm_team(raw, expected):
    assert match.norm_team(raw) == expected


#兩層對照建立：主鍵含球團，回退鍵只有姓名；缺左右手的列不收
def test_build_hand_index():
    by_team, by_name = match.build_hand_index(ROSTER)
    assert by_team['ソフトバンク|藤原大翔'] == 'R'
    assert by_name['早川隆久'] == 'L'
    assert '岸孝之' not in by_name


#精確命中球團與姓名
def test_lookup_exact():
    by_team, by_name = match.build_hand_index(ROSTER)
    assert match.lookup_hand(by_team, by_name, '楽天', '早川 隆久') == ('L', 'exact')


#球團標錯時以姓名精確命中回退，不做模糊比對
def test_lookup_fallback():
    by_team, by_name = match.build_hand_index(ROSTER)
    assert match.lookup_hand(by_team, by_name, '阪神', '藤原 大翔') == ('R', 'fallback')


#查不到一律回傳 (None, 'unmatched')，永不回傳猜測值（驗收項 V07）
@pytest.mark.parametrize('team,name', [
    ('阪神', '查無此人'),
    ('楽天', '早川'),      #部分相符不算命中
    ('楽天', '隆久 早川'), #順序不同不算命中
    ('楽天', ''),
])
def test_lookup_unmatched(team, name):
    by_team, by_name = match.build_hand_index(ROSTER)
    assert match.lookup_hand(by_team, by_name, team, name) == (None, 'unmatched')
