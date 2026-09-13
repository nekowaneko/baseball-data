#預先打包的名冊快取來源：瀏覽器版用，完全不連網
import json
import os

from adapters.roster import RosterSource


#從預先打包的 cache/*.json 讀名冊，不連網，給瀏覽器版用
#不檢查 TTL：瀏覽器沒有重抓的能力，過期也只能用，新舊交給頁面顯示 fetched_at
class CachedRosterSource(RosterSource):
    def __init__(self, cache_dir='cache'):
        self.cache_dir = cache_dir

    #快取檔路徑，檔名與 roster_http.py 寫出的一致
    def path_for(self, npb_code):
        return os.path.join(self.cache_dir, f'rst_{npb_code}.json')

    #讀整份快照（含 fetched_at），檔案不存在回 None
    def snapshot(self, npb_code):
        path = self.path_for(npb_code)
        if not os.path.exists(path):
            return None
        with open(path, encoding='utf-8') as f:
            return json.load(f)

    #讀快取，檔案不存在時回傳空清單（S4 會把該球團標記為未命中）
    def fetch_team(self, npb_code):
        snapshot = self.snapshot(npb_code)
        if snapshot is None:
            return []
        return [{'name': p['name'], 'hand': p['hand']}
                for p in snapshot.get('players', [])]

    #各快照的抓取日期，給頁面顯示名冊新舊用
    def fetched_dates(self, npb_codes):
        dates = {}
        for code in npb_codes:
            snapshot = self.snapshot(code)
            dates[code] = snapshot.get('fetched_at') if snapshot else None
        return dates
