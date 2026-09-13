#本機處理窗口：接收 MHT、跑八階段管線、以 SSE 回報進度
import json
import os
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys

if ROOT not in sys.path:  #讓 web/server.py 可直接以腳本方式執行
    sys.path.insert(0, ROOT)

from adapters.roster import StubRosterSource
#管線本體搬到 web/pipeline.py 讓瀏覽器端也能 import；這裡重新匯出，既有的 server.xxx 引用照舊有效
from web.pipeline import (  # noqa: F401
    CONFIG_FILES, DEFAULT_SETTINGS, LOG_PATH, REPORT_TEMPLATE, ROOT, STAGE_FUNCS, RunLog,
    load_config, log_path, new_context, run_pipeline, s1_classify, s2_parse, s3_audit,
    s4_roster, s5_match, s6_aggregate, s7_cross_check, s8_render, with_trace,
)


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
