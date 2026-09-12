#以 fixtures 的五份 MHT 跑完整條管線，產出 HTML、NDJSON 日誌與人工過目用的預覽報告
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from adapters.roster import StubRosterSource
from web import server

FIXTURE_PAGES = ['basic', 'mix', 'pitch', 'situational', 'vs']
PLAYER = '林 安可'


#讀入 fixture 的五份 MHT，檔名刻意取成不可靠的形式，驗證分類不看檔名
def load_fixture_files(root=ROOT):
    files = []
    for name in FIXTURE_PAGES:
        path = os.path.join(root, 'tests', 'fixtures', 'mht', f'short-stop-{name}.mht')
        with open(path, 'rb') as f:
            files.append((f'shortstop_{FIXTURE_PAGES.index(name)}_(1).mht', f.read()))
    return files


#跑一次完整管線，輸出寫進 out/
def run(root=ROOT, out_dir=None):
    out_dir = out_dir or os.path.join(root, 'out')
    os.makedirs(out_dir, exist_ok=True)
    log_path = os.path.join(out_dir, 'run.ndjson')
    if os.path.exists(log_path):  #每次重跑重寫日誌，避免累積成一坨
        os.remove(log_path)
    config = server.load_config(root)
    source = StubRosterSource(os.path.join(root, 'tests', 'fixtures'))
    log = server.RunLog(path=log_path)
    result = server.run_pipeline(load_fixture_files(root), source, config, log,
                                 os.path.join(out_dir, 'report.html'), player=PLAYER)
    write_preview(result, log, out_dir)
    return result


#人工過目用的預覽報告：視覺品質與配色無法自動判定，交給使用者看
def write_preview(result, log, out_dir):
    stats = result['context']['stats']
    lines = ['# 產出預覽報告', '',
             '自動驗收只能確認這份報告有被產生出來；以下項目請人眼過目。', '',
             '## 這次執行', '',
             f"- 整體結果：{'成功' if result['ok'] else '失敗'}",
             f"- 產出檔案：`{os.path.relpath(result['output'], out_dir)}`（與本檔同目錄）",
             f"- 略過的檔案：{'、'.join(result['skipped']) or '無'}",
             f"- 日誌事件數：{len(log.events)}", '',
             '## 交叉驗證', '']
    for hand, row in result['cross'].items():
        side = '對左投' if hand == 'L' else '對右投'
        lines.append(f"- {side}：本頁重建 {row['parsed_ab']} 打數 {row['parsed_h']} 安打，"
                     f"原站官方 {row['official_ab']} 打數 {row['official_h']} 安打 → "
                     f"{'相符' if row['match'] else '不符'}")
    lines += ['', '## 一致性稽核差異', '']
    if result['audit']:
        lines.append('| 球團 | 欄位 | 逐投手加總 | 官方合計 | 差額 |')
        lines.append('|---|---|---|---|---|')
        for row in result['audit']:
            lines.append(f"| {row['team']} | {row['field']} | {row['parsed']} | "
                         f"{row['official']} | {row['diff']} |")
    else:
        lines.append('無差異。')
    lines += ['', '## 左右手未命中（一律留空，不猜）', '']
    if result['unmatched']:
        for row in result['unmatched']:
            lines.append(f"- {row['team']} {row['name']}（{row['ab']} 打數）")
    else:
        lines.append('無。')
    lines += ['', '## 聚合結果', '',
              '| 球團 | 側 | 投手數 | 打數 | 安打 | 全壘打 | 三振 |', '|---|---|---|---|---|---|---|']
    for team, sides in stats.items():
        for hand in ('R', 'L'):
            slot = sides.get(hand)
            if not slot:
                continue
            lines.append(f"| {team} | {'對右' if hand == 'R' else '對左'} | {slot['pitchers']} | "
                         f"{slot['ab']} | {slot['h']} | {slot['hr']} | {slot['so']} |")
    lines += ['', '## 請人眼確認的項目', '',
              '- [ ] 產出網頁在手機寬度下沒有文字截斷',
              '- [ ] 球種顏色在白底上彼此分得開',
              '- [ ] 進度條在全部成功、部分失敗、完全失敗三種情況下各看過一次',
              '- [ ] log 面板能複製出完整錯誤',
              '- [ ] 頁尾的已知缺口有正確反映本次執行的實際狀況', '']
    path = os.path.join(out_dir, 'preview-report.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return path


if __name__ == '__main__':
    outcome = run()
    print(json.dumps({'ok': outcome['ok'], 'output': outcome['output'],
                      'audit': len(outcome['audit']),
                      'unmatched': len(outcome['unmatched'])},
                     ensure_ascii=False))
