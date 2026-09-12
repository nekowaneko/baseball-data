#聚合與交叉驗證測試
import os

import pytest

from core import aggregate, match, parse_basic


#從 fixture 的名冊快照建立左右手對照
@pytest.fixture(scope='session')
def hand_index(fixtures_dir):
    rows = []
    with open(os.path.join(fixtures_dir, 'hands_raw.txt'), encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            team, name, hand = line.split(',')
            rows.append({'team': team, 'name': name, 'hand': hand})
    return match.build_hand_index(rows)


#聚合結果
@pytest.fixture(scope='session')
def splits(load_json, hand_index):
    by_team, by_name = hand_index
    return aggregate.aggregate_splits(load_json('vs_pitchers.json'), by_team, by_name)


#聚合結果必須與既有產出 splits.json 完全一致（回歸基準）
def test_matches_golden_fixture(splits, load_json):
    stats, unmatched = splits
    expected = load_json('splits.json')
    assert stats == expected['stats']
    assert unmatched == expected['unmatched']


#只加總打數、安打、全壘打、三振，產出不含 OPS（驗收項 V13）
def test_only_summable_fields(splits):
    stats, _ = splits
    for sides in stats.values():
        for slot in sides.values():
            assert set(slot) == {'ab', 'h', 'hr', 'so', 'pitchers', 'fallback'}
            assert 'ops' not in slot
            assert 'avg' not in slot


#跨隊回退正確處理球團標錯的三位投手（驗收項 V08）
def test_cross_team_fallback(splits):
    stats, _ = splits
    fallbacks = sum(slot['fallback']
                    for sides in stats.values() for slot in sides.values())
    assert fallbacks == 3
    assert stats['阪神']['R']['fallback'] == 2
    assert stats['DeNA']['R']['fallback'] == 1


#查不到左右手的投手一律列入 unmatched，不併進任何一側
def test_unmatched_not_counted(splits):
    stats, unmatched = splits
    assert {u['name'] for u in unmatched} == {'東 克樹', '中川 颯', '小川 泰弘', '星 知弥'}
    assert 'ヤクルト' not in stats


#黃金值回歸：對左合計為 52 打數 8 安打（驗收項 V11）
def test_golden_left_total(splits):
    stats, _ = splits
    left = aggregate.total_by_hand(stats, 'L')
    assert (left['ab'], left['h']) == (52, 8)


#交叉驗證：對左與原站相符，對右的差額等於 S3 抓到的軟銀缺口
def test_cross_check(splits, page):
    stats, _ = splits
    totals = parse_basic.parse_split_totals(page('basic'))
    result = aggregate.cross_check(stats, totals)
    assert result['L']['match'] is True
    assert result['L']['official_ab'] == 52
    assert result['R']['match'] is False
    assert result['R']['official_ab'] - result['R']['parsed_ab'] == 16


#官方值缺席時不得判定為相符
def test_cross_check_without_official(splits):
    stats, _ = splits
    result = aggregate.cross_check(stats, {})
    assert result['L']['match'] is False
    assert result['L']['official_ab'] is None
