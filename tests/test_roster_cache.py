#預先打包的名冊快取來源測試（全程不連網，由 conftest 的封鎖保障）
import json
import os

from adapters.roster import RosterSource, collect_roster_rows
from adapters.roster_cache import CachedRosterSource
from tests.conftest import ROOT

CACHE_DIR = os.path.join(ROOT, 'cache')


#config/team_meta.json 列出的 12 隊代碼
def team_codes():
    with open(os.path.join(ROOT, 'config', 'team_meta.json'), encoding='utf-8') as f:
        return {team: meta['npb_code'] for team, meta in json.load(f).items()}


#與既有 RosterSource 介面相容，S4 可以直接換用
def test_is_roster_source():
    assert isinstance(CachedRosterSource(CACHE_DIR), RosterSource)


#V-B10 讀得到 12 隊，快照格式含 players，每筆只回 name 與 hand
def test_reads_all_twelve_teams():
    source = CachedRosterSource(CACHE_DIR)
    codes = team_codes()
    assert len(codes) == 12
    for code in codes.values():
        snapshot = source.snapshot(code)
        assert {'npb_code', 'fetched_at', 'source', 'players'} <= set(snapshot)
        players = source.fetch_team(code)
        assert players, f'rst_{code}.json 沒有投手'
        assert all(set(p) == {'name', 'hand'} for p in players)
        assert all(p['hand'] in ('R', 'L') for p in players)
    rows, missing = collect_roster_rows(source, codes)
    assert missing == []


#V-B11 缺某隊快取時回空清單不拋例外，S4 照既有方式記 warn
def test_missing_team_returns_empty(tmp_path):
    source = CachedRosterSource(str(tmp_path))
    assert source.fetch_team('e') == []
    rows, missing = collect_roster_rows(source, {'楽天': 'e'})
    assert rows == []
    assert missing == ['楽天']


#不檢查 TTL：很舊的快照照樣讀得到
def test_ignores_ttl(tmp_path):
    snapshot = {'npb_code': 'e', 'fetched_at': '2001-01-01', 'source': 'x',
                'players': [{'name': '甲', 'hand': 'L', 'no': '1'}]}
    (tmp_path / 'rst_e.json').write_text(json.dumps(snapshot, ensure_ascii=False),
                                         encoding='utf-8')
    source = CachedRosterSource(str(tmp_path))
    assert source.fetch_team('e') == [{'name': '甲', 'hand': 'L'}]
    assert source.fetched_dates(['e', 'zz']) == {'e': '2001-01-01', 'zz': None}
