#真實 NPB 名冊取數，全專案只有這一支可以連網；驗收不會用到它
import json
import os
import sys
import time
import urllib.request
from datetime import date, datetime

from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:  #讓這支可直接以腳本方式執行，不必先設 PYTHONPATH
    sys.path.insert(0, ROOT)

from adapters.roster import RosterSource

BASE_URL = 'https://npb.jp/bis/teams/rst_{code}.html'
USER_AGENT = 'baseball-data/1.0 (個人用途，單次少量請求)'
DEFAULT_TTL_DAYS = 7  #名冊會因轉隊與育成升支配下而變動，過期就重抓
HAND_LABELS = {'右': 'R', '左': 'L'}  #名冊「投」欄只有右／左兩種寫法


#下載單一球團名冊 HTML
def fetch_html(code, timeout=20):
    request = urllib.request.Request(BASE_URL.format(code=code),
                                     headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode('utf-8', 'replace')


#解析名冊表格，取姓名與「投」欄；欄位缺失就跳過該列，不猜
def parse_roster(html_text):
    soup = BeautifulSoup(html_text, 'lxml')
    players = []
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        if not rows:
            continue
        head = [c.get_text(strip=True) for c in rows[0].find_all(['th', 'td'])]
        if '投' not in head or '選手名' not in head:
            continue
        name_at = head.index('選手名')
        hand_at = head.index('投')
        for row in rows[1:]:
            cells = [c.get_text(strip=True) for c in row.find_all(['th', 'td'])]
            if len(cells) <= max(name_at, hand_at):
                continue
            hand = HAND_LABELS.get(cells[hand_at])
            if not hand:
                continue
            players.append({'name': cells[name_at], 'hand': hand})
    return players


#快取檔是否仍在有效期內
def cache_fresh(path, ttl_days):
    if not os.path.exists(path):
        return False
    with open(path, encoding='utf-8') as f:
        snapshot = json.load(f)
    fetched = snapshot.get('fetched_at')
    if not fetched:
        return False
    age = (date.today() - datetime.strptime(fetched, '%Y-%m-%d').date()).days
    return age < ttl_days


#真實取數來源：先看快取，過期才連網，抓完寫回快取
class HttpRosterSource(RosterSource):
    def __init__(self, cache_dir='cache', ttl_days=DEFAULT_TTL_DAYS, pause=1.0):
        self.cache_dir = cache_dir
        self.ttl_days = ttl_days
        self.pause = pause  #連續請求之間停一下，別打人家伺服器

    #快取檔路徑
    def path_for(self, npb_code):
        return os.path.join(self.cache_dir, f'rst_{npb_code}.json')

    #讀快取
    def load_cache(self, npb_code):
        with open(self.path_for(npb_code), encoding='utf-8') as f:
            return json.load(f).get('players', [])

    #寫快取，帶抓取日期供 TTL 判斷
    def save_cache(self, npb_code, players):
        os.makedirs(self.cache_dir, exist_ok=True)
        snapshot = {'npb_code': npb_code, 'fetched_at': date.today().isoformat(),
                    'source': BASE_URL.format(code=npb_code), 'players': players}
        with open(self.path_for(npb_code), 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=1)

    #取單一球團名冊；失敗時退回舊快取，再不行就回傳空清單
    def fetch_team(self, npb_code):
        path = self.path_for(npb_code)
        if cache_fresh(path, self.ttl_days):
            return self.load_cache(npb_code)
        try:
            players = parse_roster(fetch_html(npb_code))
            time.sleep(self.pause)
        except Exception as error:  #連不上就沿用舊資料，不中止
            print(f'取數失敗 {npb_code}：{error}')
            return self.load_cache(npb_code) if os.path.exists(path) else []
        if players:
            self.save_cache(npb_code, players)
        return players


#手動執行：抓取 config/team_meta.json 裡指定的球團名冊並寫入 cache/
def main():
    with open(os.path.join(ROOT, 'config', 'team_meta.json'), encoding='utf-8') as f:
        teams = json.load(f)
    source = HttpRosterSource(cache_dir=os.path.join(ROOT, 'cache'))
    for team, meta in teams.items():
        players = source.fetch_team(meta['npb_code'])
        print(f"{team}（rst_{meta['npb_code']}）：{len(players)} 人")


if __name__ == '__main__':
    main()
