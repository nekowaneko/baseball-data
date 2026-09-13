#階段定義檢查：只有 S8 可為 fatal，且 server.py 必須依 fatal 判定整體成敗（驗收項 V05）
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


#檢查 stages.json 的 fatal 設定
def check_stages():
    with open(os.path.join(ROOT, 'config', 'stages.json'), encoding='utf-8') as f:
        stages = json.load(f)['stages']
    fatal = [s['id'] for s in stages if s.get('fatal')]
    if fatal != ['S8']:
        return f'stages.json 的 fatal 階段應只有 S8，實際為 {fatal}'
    return None


#檢查 server.py 確實引用 fatal 旗標來判定整體成敗
def check_server():
    path = os.path.join(ROOT, 'web', 'server.py')
    if not os.path.exists(path):  #尚未實作的階段先略過
        print('web/server.py 尚未實作（略過 server 檢查）')
        return None
    with open(path, encoding='utf-8') as f:
        source = f.read()
    #B 計畫把管線搬到 web/pipeline.py：server.py 必須從那裡取 run_pipeline，判定邏輯改在 pipeline.py 檢查
    if re.search(r'from web\.pipeline import \([^)]*\brun_pipeline\b', source):
        with open(os.path.join(ROOT, 'web', 'pipeline.py'), encoding='utf-8') as f:
            source = f.read()
        if not re.search(r"stage\['fatal'\]", source):
            return 'web/pipeline.py 的 run_pipeline 未依 fatal 旗標判定整體成敗'
        return None
    if not re.search(r"fatal", source):
        return 'server.py 未依 fatal 旗標判定整體成敗'
    return None


problems = [p for p in (check_stages(), check_server()) if p]
for problem in problems:
    print(problem)
sys.exit(1 if problems else 0)
