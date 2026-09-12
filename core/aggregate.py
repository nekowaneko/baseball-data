#S6 聚合與 S7 交叉驗證
from core.match import TEAM_NAMES, lookup_hand, norm_team

#可精確相加的欄位；OPS 與上壘率需要四壞球與長打資料，來源表沒有，故不重算
SUM_FIELDS = ('ab', 'h', 'hr', 'so')


#建立一個空的統計格
def _empty_slot():
    slot = {field: 0 for field in SUM_FIELDS}
    slot['pitchers'] = 0   #涉及投手數
    slot['fallback'] = 0   #跨隊回退命中數
    return slot


#從對照表推得已知球團清單，供隊名正規化使用
def _known_teams(by_team):
    return {key.split('|', 1)[0] for key in by_team}


#依球團 × 左右手加總，查不到左右手的投手列入 unmatched，絕不猜測
def aggregate_splits(vs_data, by_team, by_name):
    known = _known_teams(by_team)
    stats = {}
    unmatched = []
    for raw_team, rows in vs_data.items():
        team = norm_team(raw_team, known | set(norm_team(raw_team).split('\n')))
        for row in rows:
            hand, how = lookup_hand(by_team, by_name, team, row.get('name', ''))
            if hand is None:
                unmatched.append({'team': team, 'name': row.get('name', ''),
                                  'ab': row.get('ab', 0)})
                continue
            slot = stats.setdefault(team, {}).setdefault(hand, _empty_slot())
            for field in SUM_FIELDS:
                slot[field] += row.get(field, 0)
            slot['pitchers'] += 1
            if how == 'fallback':
                slot['fallback'] += 1
    return stats, unmatched


#把各球團同一側加總成全體合計
def total_by_hand(stats, hand):
    total = _empty_slot()
    for sides in stats.values():
        slot = sides.get(hand)
        if not slot:
            continue
        for field in SUM_FIELDS:
            total[field] += slot[field]
        total['pitchers'] += slot['pitchers']
        total['fallback'] += slot['fallback']
    return total


#S7 交叉驗證：自行重建的左右合計要對得上原站的對左右別官方值
def cross_check(stats, split_totals):
    result = {}
    for hand in ('L', 'R'):
        parsed = total_by_hand(stats, hand)
        official = split_totals.get(hand, {})
        result[hand] = {
            'parsed_ab': parsed['ab'], 'parsed_h': parsed['h'],
            'official_ab': official.get('ab'), 'official_h': official.get('h'),
            'match': (official.get('ab') == parsed['ab']
                      and official.get('h') == parsed['h']),
        }
    return result
