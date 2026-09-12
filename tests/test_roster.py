#名冊取數介面與 Stub 測試（全程不連網，驗收項 V17 由 conftest 的封鎖保障）
import pytest

from adapters.roster import RosterSource, StubRosterSource, collect_roster_rows
from core import match

TEAM_CODES = {'楽天': 'e', '日本ハム': 'f', 'オリックス': 'b',
              'ロッテ': 'm', 'ソフトバンク': 'h'}


#介面本身不提供實作，逼子類必須覆寫
def test_interface_is_abstract():
    with pytest.raises(NotImplementedError):
        RosterSource().fetch_team('e')


#Stub 讀得到五份名冊快照，每筆都有姓名與左右手
def test_stub_fetch_team(fixtures_dir):
    source = StubRosterSource(fixtures_dir)
    players = source.fetch_team('h')
    assert len(players) == 18
    assert all(p['hand'] in ('R', 'L') for p in players)
    assert {'name', 'hand'} == set(players[0])


#沒有快照的球團回傳空清單，不拋例外（S4 會標記未命中後繼續）
def test_stub_missing_team(fixtures_dir):
    assert StubRosterSource(fixtures_dir).fetch_team('zz') == []


#拉平成對照表用的列，並回報沒有名冊的球團
def test_collect_roster_rows(fixtures_dir):
    source = StubRosterSource(fixtures_dir)
    codes = dict(TEAM_CODES, ヤクルト='s')
    rows, missing = collect_roster_rows(source, codes)
    assert missing == ['ヤクルト']
    assert len(rows) == 82
    assert {'team', 'name', 'hand'} == set(rows[0])


#由 Stub 建出的對照表要能還原黃金值：對左合計 52 打數 8 安打
def test_stub_reproduces_golden(fixtures_dir, load_json):
    from core import aggregate

    rows, _ = collect_roster_rows(StubRosterSource(fixtures_dir), TEAM_CODES)
    by_team, by_name = match.build_hand_index(rows)
    stats, unmatched = aggregate.aggregate_splits(load_json('vs_pitchers.json'),
                                                  by_team, by_name)
    assert stats == load_json('splits.json')['stats']
    assert unmatched == load_json('splits.json')['unmatched']
