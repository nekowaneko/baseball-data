#管線模組獨立性測試：瀏覽器端只載得到 web.pipeline，不能偷偷依賴 web.server
import json
import os
import subprocess
import sys

from tests.conftest import ROOT

#子行程裡只 import pipeline，跑完五份 MHT 後回報結果與已載入的模組
CHILD = r'''
import json, os, sys
sys.path.insert(0, os.getcwd())
from web import pipeline
from adapters.roster import StubRosterSource
names = ['basic', 'mix', 'pitch', 'situational', 'vs']
files = []
for name in names:
    with open(os.path.join('tests', 'fixtures', 'mht', f'short-stop-{name}.mht'), 'rb') as f:
        files.append((f'{name}.mht', f.read()))
result = pipeline.run_pipeline(files, StubRosterSource(os.path.join('tests', 'fixtures')),
                               pipeline.load_config(), output_path=sys.argv[1])
print(json.dumps({'ok': result['ok'], 'stages': [s['ok'] for s in result['stages']],
                  'parsed_ab': result['cross']['L']['parsed_ab'],
                  'server_loaded': 'web.server' in sys.modules,
                  'http_loaded': 'http.server' in sys.modules}))
'''


#V-B08 web.pipeline 在未 import web.server 的情況下獨立匯入並跑完管線
def test_pipeline_runs_without_server(tmp_path):
    out = tmp_path / 'report.html'
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    proc = subprocess.run([sys.executable, '-c', CHILD, str(out)], cwd=ROOT, env=env,
                          capture_output=True, text=True, encoding='utf-8', timeout=120)
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report['ok'] is True
    assert report['stages'] == [True] * 8
    assert report['parsed_ab'] == 52
    assert report['server_loaded'] is False
    assert report['http_loaded'] is False
    assert out.exists()


#V-B09 既有的 server.run_pipeline、server.load_config、server.RunLog 仍然可用
def test_server_reexports():
    from web import pipeline, server

    for name in ('run_pipeline', 'load_config', 'RunLog'):
        assert callable(getattr(server, name))
        assert getattr(server, name) is getattr(pipeline, name)


#方向固定：server 引用 pipeline，pipeline 絕不反向引用 server
def test_pipeline_does_not_import_server():
    with open(os.path.join(ROOT, 'web', 'pipeline.py'), encoding='utf-8') as f:
        source = f.read()
    assert 'web.server' not in source
    assert 'import server' not in source
