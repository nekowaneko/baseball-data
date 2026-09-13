#瀏覽器版打包測試：zip 內容、排除規則、大小與網站上那份是否過期
import os
import zipfile

import pytest

from tests.conftest import ROOT
from tools import build_web

PUBLISHED = os.path.join(ROOT, 'docs', 'payload', 'pipeline.zip')


#打包一次到暫存目錄，整個測試模組共用
@pytest.fixture(scope='module')
def built(tmp_path_factory):
    out = str(tmp_path_factory.mktemp('payload') / 'pipeline.zip')
    path = build_web.build(ROOT, out)
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
    return path, names


#回傳值就是產出路徑
def test_build_returns_path(built):
    path, _ = built
    assert os.path.isfile(path)


#V-B06 不含 tests/、out/、uploads/、__pycache__、.pyc、roster_http.py
def test_excludes(built):
    _, names = built
    for name in names:
        assert not name.startswith(('tests/', 'out/', 'uploads/'))
        assert '__pycache__' not in name
        assert not name.endswith('.pyc')
    assert 'adapters/roster_http.py' not in names
    #只排除出 zip，本機的原檔仍在
    assert os.path.isfile(os.path.join(ROOT, 'adapters', 'roster_http.py'))


#V-B12 管線與資料的關鍵檔案都在
def test_required_members(built):
    _, names = built
    for name in ('core/render.py', 'web/pipeline.py', 'web/__init__.py',
                 'config/pitch_meta.json', 'cache/rst_e.json', 'web/report_template.html',
                 'adapters/roster.py', 'adapters/roster_cache.py', 'core/__init__.py',
                 'adapters/__init__.py'):
        assert name in names
    assert len([n for n in names if n.startswith('cache/')]) == 12
    #web/ 只放管線需要的三個檔，本機窗口的 server.py 與前端不打包
    assert sorted(n for n in names if n.startswith('web/')) == [
        'web/__init__.py', 'web/pipeline.py', 'web/report_template.html']


#V-B13 zip 小於 1 MB
def test_size_under_one_mb(built):
    path, _ = built
    assert os.path.getsize(path) < 1024 * 1024


#排除規則本身：巢狀的 __pycache__ 與測試目錄也要擋下
def test_excluded_rule():
    assert build_web.excluded('adapters/roster_http.py')
    assert build_web.excluded('core/__pycache__/render.cpython-310.pyc')
    assert build_web.excluded('tests/test_render.py')
    assert build_web.excluded('out/report.html')
    assert build_web.excluded('uploads/a.mht')
    assert not build_web.excluded('core/render.py')


#內容沒變時重新打包的位元組完全相同，避免 git 每次都出現差異
def test_deterministic(built, tmp_path):
    path, _ = built
    again = build_web.build(ROOT, str(tmp_path / 'again.zip'))
    with open(path, 'rb') as a, open(again, 'rb') as b:
        assert a.read() == b.read()


#網站上那份 docs/payload/pipeline.zip 必須與現在的程式一致：改了管線卻忘了重新打包就會失敗
#比對時忽略換行差異，因為 Windows 的 git 可能在取出時把 LF 換成 CRLF
def test_published_payload_is_current(built):
    path, names = built
    assert os.path.isfile(PUBLISHED), '尚未產生 docs/payload/pipeline.zip，請跑 python tools/build_web.py'
    with zipfile.ZipFile(path) as fresh, zipfile.ZipFile(PUBLISHED) as published:
        assert sorted(published.namelist()) == sorted(names)
        for name in names:
            expected = fresh.read(name).replace(b'\r\n', b'\n')
            actual = published.read(name).replace(b'\r\n', b'\n')
            assert actual == expected, f'{name} 已過期，請跑 python tools/build_web.py'


#子行程在解開的 zip 目錄裡跑管線，模擬 Pyodide：只看得到 zip 內容，名冊用打包的快取
UNPACKED_CHILD = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from adapters.roster_cache import CachedRosterSource
from web import pipeline
files = []
for path in sys.argv[3:]:
    with open(path, 'rb') as f:
        files.append((path, f.read()))
result = pipeline.run_pipeline(files, CachedRosterSource(), pipeline.load_config(),
                               output_path=sys.argv[2])
print(json.dumps({'ok': result['ok'], 'stages': [s['ok'] for s in result['stages']],
                  'root': pipeline.ROOT, 'missing': result['context']['roster_rows'] == []}))
'''


#zip 自足：解開到空目錄後，不靠專案原始碼也能跑完八階段並產出報表
def test_unpacked_payload_runs_pipeline(built, tmp_path, fixtures_dir):
    import json
    import subprocess
    import sys

    path, _ = built
    site = tmp_path / 'site'
    with zipfile.ZipFile(path) as archive:
        archive.extractall(site)
    out = tmp_path / 'out' / 'report.html'
    mhts = [os.path.join(fixtures_dir, 'mht', f'short-stop-{n}.mht')
            for n in ('basic', 'mix', 'pitch', 'situational', 'vs')]
    env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
    env['PYTHONIOENCODING'] = 'utf-8'
    proc = subprocess.run([sys.executable, '-c', UNPACKED_CHILD, str(site), str(out), *mhts],
                          cwd=str(site), env=env, capture_output=True, text=True,
                          encoding='utf-8', timeout=120)
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert os.path.normcase(report['root']) == os.path.normcase(str(site))
    assert report['ok'] is True
    assert report['stages'] == [True] * 8
    assert report['missing'] is False
    assert out.stat().st_size > 0


#讀 docs/ 下的網站檔
def read_docs(name):
    with open(os.path.join(ROOT, 'docs', name), encoding='utf-8') as f:
        return f.read()


#V-B14 app.js 鎖定的 Pyodide 版本與 EXPENSIVE-PLAN-B.md §7 一致，來源是 jsDelivr
def test_pyodide_version_pinned():
    import re

    source = read_docs('app.js')
    assert re.search(r"const PYODIDE_VERSION = 'v314\.0\.6'", source)
    assert 'https://cdn.jsdelivr.net/pyodide/${PYODIDE_VERSION}/full/' in source
    #bs4 走 Pyodide 內建套件，不得連 PyPI；比對實際的載入寫法，註解裡提到 micropip 不算
    assert "loadPackage('beautifulsoup4')" in source
    assert not re.search(r"import\s+micropip|loadPackage\(\s*['\"]micropip|pyimport\(\s*['\"]micropip",
                         source)


#V-B15 index.html 的每個元素 id 都被 app.js 引用到（便宜批次 §3.1 表列 12 個）
def test_index_ids_used_by_app():
    import re

    ids = re.findall(r'\bid="([^"]+)"', read_docs('index.html'))
    assert set(ids) == {'boot', 'boot-msg', 'picker', 'files', 'filelist', 'run', 'progress',
                        'log', 'result', 'open-report', 'save-report', 'error'}
    source = read_docs('app.js')
    for element_id in ids:
        assert f"el('{element_id}')" in source, f'app.js 沒有用到 #{element_id}'


#app.js 的管線呼叫接到 web.pipeline 與 CachedRosterSource，輸出寫到固定的虛擬路徑
def test_app_wires_pipeline():
    source = read_docs('app.js')
    assert 'from web import pipeline' in source
    assert 'CachedRosterSource()' in source
    assert "const OUTPUT_PATH = '/out/report.html'" in source
    assert "unpackArchive(await response.arrayBuffer(), 'zip')" in source
    assert "fetch(PAYLOAD_URL)" in source and "const PAYLOAD_URL = 'payload/pipeline.zip'" in source
    #整支 app.js 只有兩個 fetch 目標：同網域的 payload 與 CDN 腳本，沒有任何上傳
    assert source.count('fetch(') == 1
    assert "method: 'POST'" not in source


#sw.js 快取五個網站檔、快取名稱含版本、啟用時清舊版，且不碰跨網域資源
def test_service_worker():
    source = read_docs('sw.js')
    for asset in ('index.html', 'style.css', 'app.js', 'manifest.webmanifest',
                  'payload/pipeline.zip'):
        assert f"'{asset}'" in source
    assert 'const CACHE_NAME = `pitch-window-${VERSION}`' in source
    assert 'caches.delete' in source
    assert 'self.location.origin' in source
    assert 'jsdelivr' not in source
