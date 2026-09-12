#名冊取數介面與 Stub 實作（驗收全程只用 Stub，不碰外部服務）
import json
import os


#取數介面：所有名冊來源都必須實作 fetch_team
class RosterSource:
    #回傳 [{name, hand}]，取不到就回傳空清單，不得拋例外中止管線
    def fetch_team(self, npb_code):
        raise NotImplementedError


#從 fixtures/ 讀名冊快照，供測試與離線驗收使用
class StubRosterSource(RosterSource):
    def __init__(self, fixtures_dir):
        self.fixtures_dir = fixtures_dir

    #快照檔路徑
    def path_for(self, npb_code):
        return os.path.join(self.fixtures_dir, 'roster', f'rst_{npb_code}.json')

    #讀快照，檔案不存在時回傳空清單（S4 會把該球團標記為未命中）
    def fetch_team(self, npb_code):
        path = self.path_for(npb_code)
        if not os.path.exists(path):
            return []
        with open(path, encoding='utf-8') as f:
            snapshot = json.load(f)
        return [{'name': p['name'], 'hand': p['hand']}
                for p in snapshot.get('players', [])]


#把多個球團的名冊拉平成 build_hand_index 需要的列，附上球團名
def collect_roster_rows(source, team_codes):
    rows = []
    missing = []
    for team, code in team_codes.items():
        players = source.fetch_team(code)
        if not players:
            missing.append(team)
            continue
        for player in players:
            rows.append({'team': team, 'name': player['name'], 'hand': player['hand']})
    return rows, missing
