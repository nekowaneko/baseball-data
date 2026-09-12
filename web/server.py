#本機處理窗口：接收 MHT、跑八階段管線、以 SSE 回報進度
import json
import os
import threading
import time
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys

if ROOT not in sys.path:  #讓 web/server.py 可直接以腳本方式執行
    sys.path.insert(0, ROOT)

from adapters.roster import StubRosterSource, collect_roster_rows
from core import aggregate, audit, match, mht, parse_basic, parse_mix, parse_pitch, parse_vs
from core.render import build_report_data, render_html

#預設設定，settings.json 缺欄位時用這一組（不讀環境變數）
DEFAULT_SETTINGS = {
    'upload_dir': 'uploads/', 'cache_dir': 'cache/', 'output_dir': 'out/',
    'cache_ttl_days': 7, 'min_ab_for_avg': 10, 'max_upload_size_mb': 20,
    'server_port': 8787,
}
CONFIG_FILES = {'stages': 'stages.json', 'pitch_meta': 'pitch_meta.json',
                'team_meta': 'team_meta.json'}
LOG_PATH = 'run.ndjson'          #執行日誌，每行一個事件
REPORT_TEMPLATE = 'report_template.html'


#讀 config/ 下的設定與常數資料，settings.json 不存在就用範例檔
def load_config(root=ROOT):
    config = {}
    for key, name in CONFIG_FILES.items():
        with open(os.path.join(root, 'config', name), encoding='utf-8') as f:
            config[key] = json.load(f)
    settings = dict(DEFAULT_SETTINGS)
    for name in ('settings.json', 'settings.example.json'):
        path = os.path.join(root, 'config', name)
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                settings.update(json.load(f))
            break
    config['settings'] = settings
    return config


#執行日誌：每行一個 JSON 事件，同時推給 SSE
class RunLog:
    def __init__(self, path=None, sink=None):
        self.path = path
        self.sink = sink      #SSE 用的回呼
        self.events = []

    #寫一筆事件
    def write(self, stage, level, msg, detail=None):
        event = {'ts': datetime.now().isoformat(timespec='seconds'),
                 'stage': stage, 'level': level, 'msg': msg, 'detail': detail}
        self.events.append(event)
        if self.path:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')
        if self.sink:
            self.sink(event)
        return event


#包裝器：把任一站包起來，記錄耗時與錯誤，方便之後維修與追蹤
def with_trace(stage_id, name, fn, log):
    def run(ctx):
        started = time.time()
        log.write(stage_id, 'info', f'{name} 開始')
        try:
            fn(ctx)
        except Exception as error:  #階段失敗不中止管線，只記錄（A3）
            cost = int((time.time() - started) * 1000)
            log.write(stage_id, 'error', f'{name} 失敗 耗時 {cost}ms 原因 {error}',
                      {'error': f'{type(error).__name__}: {error}'})
            ctx['errors'].append({'stage': stage_id, 'msg': f'{name} 失敗：{error}'})
            return False
        cost = int((time.time() - started) * 1000)
        log.write(stage_id, 'info', f'{name} 成功 耗時 {cost}ms')
        return True

    return run


#S1 接收與分類檔案：分不出來的標記略過
def s1_classify(ctx):
    for filename, raw in ctx['files']:
        html = mht.main_page(raw)
        kind = mht.classify_page(html)
        if kind is None:
            ctx['log'].write('S1', 'warn', f'無法分類，略過：{filename}')
            ctx['skipped'].append(filename)
            continue
        ctx['pages'][kind] = html
        ctx['log'].write('S1', 'info', f'{filename} 判定為 {kind}')


#S2 解析各分頁：單一分頁失敗只記錄該分頁
def s2_parse(ctx):
    pages = ctx['pages']
    jobs = [
        ('vs', 'vs_data', lambda h: parse_vs.parse_vs_pitchers(h)),
        ('mix', 'mix', lambda h: parse_mix.parse_team_mix(h)),
        ('pitch', 'pitch', lambda h: parse_pitch.parse_pitch_types(h)),
        ('basic', 'team_totals', lambda h: parse_basic.parse_team_totals(h)),
        ('basic', 'split_totals', lambda h: parse_basic.parse_split_totals(h)),
        ('basic', 'split_display', lambda h: parse_basic.parse_split_display(h)),
    ]
    for kind, key, parse in jobs:
        if kind not in pages:
            ctx['log'].write('S2', 'warn', f'缺少 {kind} 分頁，{key} 留空')
            continue
        try:
            ctx[key] = parse(pages[kind])
            ctx['log'].write('S2', 'info', f'{key} 解析完成', {'筆數': len(ctx[key])})
        except Exception as error:  #該分頁標記失敗，其餘繼續
            ctx['log'].write('S2', 'error', f'{key} 解析失敗：{error}')
            ctx['errors'].append({'stage': 'S2', 'msg': f'{key} 解析失敗：{error}'})


#S3 一致性稽核：永不中止，差異寫進報告
def s3_audit(ctx):
    ctx['audit'] = audit.audit_totals(ctx['vs_data'], ctx['team_totals'])
    for row in ctx['audit']:
        ctx['log'].write('S3', 'warn',
                         f"{row['team']} 的 {row['field']} 差 {row['diff']}", row)
    if not ctx['audit']:
        ctx['log'].write('S3', 'info', '逐投手加總與官方合計完全吻合')


#S4 取得投手左右手：取不到的球團標記未命中，繼續
def s4_roster(ctx):
    codes = {team: meta['npb_code'] for team, meta in ctx['team_meta'].items()
             if team in ctx['wanted_teams']}
    rows, missing = collect_roster_rows(ctx['roster_source'], codes)
    ctx['roster_rows'] = rows
    for team in missing:
        ctx['log'].write('S4', 'warn', f'取不到 {team} 的名冊')
    ctx['log'].write('S4', 'info', f'取得 {len(rows)} 筆左右手資料')


#S5 姓名比對：建立兩層對照，查不到的留到 S6 列清單
def s5_match(ctx):
    ctx['by_team'], ctx['by_name'] = match.build_hand_index(ctx['roster_rows'])
    ctx['log'].write('S5', 'info', f"對照表 {len(ctx['by_team'])} 筆")


#S6 聚合統計：缺資料的格子留空，繼續
def s6_aggregate(ctx):
    ctx['stats'], ctx['unmatched'] = aggregate.aggregate_splits(
        ctx['vs_data'], ctx['by_team'], ctx['by_name'])
    for row in ctx['unmatched']:
        ctx['log'].write('S6', 'warn',
                         f"{row['team']} {row['name']} 查不到左右手，留空不猜", row)


#S7 交叉驗證：不符時不中止，但要標出來
def s7_cross_check(ctx):
    ctx['cross'] = aggregate.cross_check(ctx['stats'], ctx['split_totals'])
    for hand, row in ctx['cross'].items():
        level = 'info' if row['match'] else 'warn'
        ctx['log'].write('S7', level,
                         f"對{'左' if hand == 'L' else '右'}重建 {row['parsed_ab']} 打數 "
                         f"{row['parsed_h']} 安打，官方 {row['official_ab']} 打數 "
                         f"{row['official_h']} 安打", row)


#S8 產出 HTML：唯一失敗就算整體失敗的階段
def s8_render(ctx):
    with open(os.path.join(ROOT, 'web', REPORT_TEMPLATE), encoding='utf-8') as f:
        template = f.read()
    data = build_report_data(
        ctx['stats'], ctx['unmatched'], ctx['audit'], ctx['cross'],
        ctx['mix'], ctx['pitch'], ctx['pitch_meta'], ctx['team_meta'],
        datetime.now().isoformat(timespec='seconds'), player=ctx['player'],
        errors=ctx['errors'], min_ab=ctx['min_ab'],
        split_display=ctx['split_display'])
    html = render_html(data, template)
    os.makedirs(os.path.dirname(ctx['output_path']), exist_ok=True)
    with open(ctx['output_path'], 'w', encoding='utf-8') as f:
        f.write(html)
    ctx['log'].write('S8', 'info', f"產出 {ctx['output_path']}")


#八個階段的實作，順序即執行順序
STAGE_FUNCS = {'S1': s1_classify, 'S2': s2_parse, 'S3': s3_audit, 'S4': s4_roster,
               'S5': s5_match, 'S6': s6_aggregate, 'S7': s7_cross_check,
               'S8': s8_render}


#建立初始的管線脈絡
def new_context(files, roster_source, config, log, output_path, player=''):
    settings = config['settings']
    return {
        'files': files, 'roster_source': roster_source, 'log': log,
        'pages': {}, 'skipped': [], 'errors': [],
        'vs_data': {}, 'mix': {}, 'pitch': {}, 'team_totals': {}, 'split_totals': {},
        'split_display': {},
        'audit': [], 'roster_rows': [], 'by_team': {}, 'by_name': {},
        'stats': {}, 'unmatched': [], 'cross': {},
        'pitch_meta': config['pitch_meta'], 'team_meta': config['team_meta'],
        'wanted_teams': set(config['team_meta']),
        'min_ab': settings.get('min_ab_for_avg', 10),
        'output_path': output_path, 'player': player,
    }


#跑完八階段；只有 fatal 階段失敗才算整體失敗（依 stages.json）
def run_pipeline(files, roster_source, config, log=None, output_path=None, player=''):
    log = log or RunLog()
    output_path = output_path or os.path.join(ROOT, 'out', 'report.html')
    ctx = new_context(files, roster_source, config, log, output_path, player)
    results = []
    ok = True
    for stage in config['stages']['stages']:
        runner = with_trace(stage['id'], stage['name'], STAGE_FUNCS[stage['id']], log)
        passed = runner(ctx)
        results.append({'id': stage['id'], 'name': stage['name'],
                        'ok': passed, 'fatal': stage['fatal']})
        if not passed and stage['fatal']:  #S8 是唯一會讓整體判定失敗的階段
            ok = False
    return {'ok': ok, 'stages': results, 'errors': ctx['errors'],
            'skipped': ctx['skipped'], 'output': ctx['output_path'],
            'audit': ctx['audit'], 'unmatched': ctx['unmatched'],
            'cross': ctx['cross'], 'context': ctx}


#切出 multipart/form-data 的檔案部件，回傳 [(檔名, 位元組)]
def parse_multipart(body, content_type):
    marker = 'boundary='
    if marker not in content_type:
        return []
    boundary = content_type.split(marker, 1)[1].strip().strip('"')
    sep = b'--' + boundary.encode()
    files = []
    for chunk in body.split(sep):
        head, _, payload = chunk.partition(b'\r\n\r\n')
        if b'filename="' not in head or not payload:
            continue
        filename = head.split(b'filename="', 1)[1].split(b'"', 1)[0]
        files.append((filename.decode('utf-8', 'replace'),
                      payload.rstrip(b'\r\n-')))
    return files


#一次執行的狀態：事件佇列與結果
class Run:
    def __init__(self, run_id):
        self.id = run_id
        self.events = []
        self.done = False
        self.result = None


RUNS = {}          #run_id → Run
RUNS_LOCK = threading.Lock()


#在背景執行管線，事件同步推進 Run 的佇列
def start_run(files, config, root=ROOT):
    run = Run(uuid.uuid4().hex[:8])
    with RUNS_LOCK:
        RUNS[run.id] = run
    settings = config['settings']
    out_dir = os.path.join(root, settings.get('output_dir', 'out/'))
    log = RunLog(path=os.path.join(out_dir, LOG_PATH), sink=run.events.append)
    source = StubRosterSource(os.path.join(root, 'tests', 'fixtures'))

    def worker():
        try:
            run.result = run_pipeline(files, source, config, log,
                                      os.path.join(out_dir, f'report-{run.id}.html'))
        except Exception as error:  #管線本身壞掉才會走到這裡
            log.write('S8', 'error', f'管線中止：{error}')
            run.result = {'ok': False, 'stages': [], 'errors': [str(error)]}
        finally:
            run.done = True

    threading.Thread(target=worker, daemon=True).start()
    return run


#HTTP 介面：上傳、SSE 進度、下載產物
class Handler(BaseHTTPRequestHandler):
    config = None

    #靜態檔與 API
    def do_GET(self):
        if self.path in ('/', '/index.html'):
            return self.send_file(os.path.join(ROOT, 'web', 'index.html'), 'text/html')
        if self.path == '/app.js':
            return self.send_file(os.path.join(ROOT, 'web', 'app.js'), 'text/javascript')
        if self.path == '/api/stages':
            return self.send_json(self.config['stages'])
        if self.path.startswith('/api/progress'):
            return self.stream_progress(self.path.split('run=')[-1])
        if self.path.startswith('/out/'):
            name = os.path.basename(self.path)
            return self.send_file(os.path.join(ROOT, 'out', name), 'text/html')
        self.send_error(404)

    #上傳並啟動一次執行
    def do_POST(self):
        if self.path != '/api/upload':
            return self.send_error(404)
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        files = parse_multipart(body, self.headers.get('Content-Type', ''))
        if not files:
            return self.send_json({'error': '沒有收到檔案'}, status=400)
        run = start_run(files, self.config)
        self.send_json({'run': run.id, 'files': [name for name, _ in files]})

    #SSE：把事件一筆一筆推給前端
    def stream_progress(self, run_id):
        run = RUNS.get(run_id)
        if run is None:
            return self.send_json({'error': '查無此執行'}, status=404)
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        sent = 0
        while True:
            while sent < len(run.events):
                self.wfile.write(f'data: {json.dumps(run.events[sent], ensure_ascii=False)}\n\n'
                                 .encode('utf-8'))
                self.wfile.flush()
                sent += 1
            if run.done and sent >= len(run.events):
                summary = {'type': 'done', 'ok': bool(run.result and run.result['ok']),
                           'stages': run.result['stages'] if run.result else [],
                           'output': os.path.basename(run.result['output'])
                           if run.result and run.result.get('output') else None}
                self.wfile.write(f'data: {json.dumps(summary, ensure_ascii=False)}\n\n'
                                 .encode('utf-8'))
                self.wfile.flush()
                return
            time.sleep(0.2)

    #回傳 JSON
    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    #回傳靜態檔
    def send_file(self, path, mime):
        if not os.path.exists(path):
            return self.send_error(404)
        with open(path, 'rb') as f:
            body = f.read()
        self.send_response(200)
        self.send_header('Content-Type', f'{mime}; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    #日誌交給 RunLog，HTTP 內建日誌關掉
    def log_message(self, fmt, *args):
        pass


#取本機在區域網路上的 IP，只給提示訊息用，失敗就回 None
def lan_ip():
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(('8.8.8.8', 80))     #不會真的送封包，只為問出對外網卡位址
        return sock.getsockname()[0]
    except OSError:
        return None
    finally:
        sock.close()


#啟動伺服器，host 預設只開本機；要讓手機連就傳 0.0.0.0
def serve(port=None, root=ROOT, host='127.0.0.1'):
    config = load_config(root)
    Handler.config = config
    port = port or config['settings'].get('server_port', 8787)
    server = ThreadingHTTPServer((host, port), Handler)
    print(f'配球資料處理窗口已啟動：http://127.0.0.1:{port}')
    if host not in ('127.0.0.1', 'localhost'):
        ip = lan_ip()
        if ip:
            print(f'同一個 Wi-Fi 的手機請開：http://{ip}:{port}')
    server.serve_forever()


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='配球資料處理窗口')
    ap.add_argument('--host', default='127.0.0.1',
                    help='綁定位址，0.0.0.0 = 允許同網段的手機連入')
    ap.add_argument('--port', type=int, default=None, help='覆寫 settings 的埠號')
    args = ap.parse_args()
    serve(port=args.port, host=args.host)
