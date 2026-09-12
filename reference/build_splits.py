# 建立投手左右手對照表，並產出「球團 × 左右投」的打擊統計
import json
import unicodedata

# 姓名正規化：全半形統一後去掉所有空白，避免兩邊寫法不同而比不到
def norm(name):
    s = unicodedata.normalize('NFKC', name)
    return ''.join(s.split())

# 讀取 NPB 名冊抽出的左右手資料，建立兩層 key-value
def load_hands(path):
    by_team = {}   # 主鍵：球團|姓名
    by_name = {}   # 回退鍵：姓名（處理季中換隊）
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            team, name, hand = line.split(',')
            by_team[f'{team}|{norm(name)}'] = hand
            by_name[norm(name)] = hand
    return by_team, by_name

# Short-Stop 的隊名帶英文後綴，對回名冊用的簡稱
TEAM_ALIAS = {
    '楽天Eagles': '楽天', '日本ハムFighters': '日本ハム',
    'オリックスBuffaloes': 'オリックス', 'ロッテMarines': 'ロッテ',
    'ソフトバンクHawks': 'ソフトバンク', 'DeNABayStars': 'DeNA',
    'ヤクルトSwallows': 'ヤクルト', '阪神Tigers': '阪神'
}

# 查左右手：先用（球團,姓名），查不到再退回全聯盟姓名
def lookup(by_team, by_name, team, name):
    key = f'{team}|{norm(name)}'
    if key in by_team:
        return by_team[key], 'exact'
    if norm(name) in by_name:
        return by_name[norm(name)], 'fallback'
    return None, 'unmatched'

# 依球團與左右手分組加總，只加總可加總的欄位
def aggregate(vs_data, by_team, by_name):
    stats = {}
    unmatched = []
    for raw_team, rows in vs_data.items():
        team = TEAM_ALIAS.get(raw_team, raw_team)
        for r in rows:
            hand, how = lookup(by_team, by_name, team, r['name'])
            if hand is None:
                unmatched.append({'team': team, 'name': r['name'], 'ab': r['ab']})
                continue
            slot = stats.setdefault(team, {}).setdefault(hand, {
                'ab': 0, 'h': 0, 'hr': 0, 'so': 0, 'pitchers': 0, 'fallback': 0
            })
            slot['ab'] += r['ab']
            slot['h'] += r['h']
            slot['hr'] += r['hr']
            slot['so'] += r['so']
            slot['pitchers'] += 1
            if how == 'fallback':
                slot['fallback'] += 1
    return stats, unmatched

by_team, by_name = load_hands('hands_raw.txt')
vs_data = json.load(open('vs_pitchers.json', encoding='utf-8'))
stats, unmatched = aggregate(vs_data, by_team, by_name)

json.dump({'stats': stats, 'unmatched': unmatched},
          open('splits.json', 'w'), ensure_ascii=False)

# 輸出檢查用報表
print(f'對照表筆數 {len(by_team)}　未命中 {len(unmatched)} 人')
print()
print(f"{'球團':<8}{'手':<4}{'投手數':<7}{'打數':<6}{'安打':<6}{'打率':<8}{'全壘打':<7}{'三振率'}")
tot = {'L': [0, 0], 'R': [0, 0]}
for team in stats:
    for hand in ['R', 'L']:
        s = stats[team].get(hand)
        if not s:
            continue
        avg = f"{s['h'] / s['ab']:.3f}".lstrip('0') if s['ab'] else '—'
        kr = f"{s['so'] / s['ab'] * 100:.1f}%" if s['ab'] else '—'
        print(f"{team:<8}{hand:<4}{s['pitchers']:<7}{s['ab']:<6}{s['h']:<6}{avg:<8}{s['hr']:<7}{kr}")
        tot[hand][0] += s['ab']
        tot[hand][1] += s['h']
print()
print(f"合計　對右 {tot['R'][0]} 打數 {tot['R'][1]} 安打　對左 {tot['L'][0]} 打數 {tot['L'][1]} 安打")
if unmatched:
    print()
    print('未命中清單（不猜，留空）：')
    for u in unmatched:
        print(f"  {u['team']} {u['name']}　{u['ab']} 打數")
