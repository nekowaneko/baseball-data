#姓名正規化與投手左右手比對
import unicodedata

#球團簡稱清單，與 config/team_meta.json 的鍵一致；core/ 不得讀檔，故在此以常數鏡射
TEAM_NAMES = (
    '楽天', '日本ハム', 'オリックス', 'ロッテ', 'ソフトバンク', '西武',
    'ヤクルト', 'DeNA', '阪神', '巨人', '中日', '広島',
)


#姓名正規化：全半形統一後去掉所有空白，避免兩邊寫法不同而比不到
def norm_name(name):
    text = unicodedata.normalize('NFKC', name or '')
    return ''.join(text.split())


#球團名正規化：Short-Stop 的隊名帶英文後綴，取最長的已知簡稱前綴
def norm_team(raw, known_teams=None):
    names = tuple(known_teams) if known_teams else TEAM_NAMES
    candidates = [n for n in names if raw.startswith(n)]
    if not candidates:
        return raw
    return max(candidates, key=len)


#建立兩層對照：主鍵「球團|姓名」，回退鍵「姓名」（處理季中換隊與球團標錯）
def build_hand_index(roster_rows):
    by_team = {}
    by_name = {}
    for row in roster_rows:
        hand = row.get('hand')
        if not hand:  #名冊沒寫左右手就不收，不猜
            continue
        name = norm_name(row.get('name', ''))
        team = row.get('team', '')
        if team:
            by_team[f'{team}|{name}'] = hand
        by_name[name] = hand
    return by_team, by_name


#查左右手：先用（球團,姓名）精確命中，查不到才退回全聯盟姓名精確命中
def lookup_hand(by_team, by_name, team, name):
    key = f'{team}|{norm_name(name)}'
    if key in by_team:
        return by_team[key], 'exact'
    if norm_name(name) in by_name:  #回退僅限姓名精確命中，不做模糊比對
        return by_name[norm_name(name)], 'fallback'
    return None, 'unmatched'
