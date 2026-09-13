#管線行為測試：階段降級、日誌格式與整體成敗判定
import json
import os
import re

import pytest

from adapters.roster import StubRosterSource
from web import pipeline, server

MHT_NAMES = ['basic', 'mix', 'pitch', 'situational', 'vs']


#五份 MHT 的原始位元組
@pytest.fixture(scope='session')
def mht_files(fixtures_dir):
    files = []
    for name in MHT_NAMES:
        path = os.path.join(fixtures_dir, 'mht', f'short-stop-{name}.mht')
        with open(path, 'rb') as f:
            files.append((f'{name}_(1).mht', f.read()))  #檔名刻意取成不可靠的形式
    return files


#設定包
@pytest.fixture(scope='session')
def config():
    return server.load_config()


#跑一次完整管線（Stub 名冊，輸出寫到 tmp）
@pytest.fixture(scope='session')
def run_result(mht_files, config, fixtures_dir, tmp_path_factory):
    out = tmp_path_factory.mktemp('run')
    log = server.RunLog(path=str(out / 'run.ndjson'))
    result = server.run_pipeline(mht_files, StubRosterSource(fixtures_dir), config,
                                 log, str(out / 'report.html'), player='林 安可')
    return result, log, out


#八階段全部執行且整體成功
def test_all_stages_ok(run_result):
    result, _, _ = run_result
    assert [s['id'] for s in result['stages']] == ['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8']
    assert all(s['ok'] for s in result['stages'])
    assert result['ok'] is True


#檔名不可靠，分類全靠內容；五份都要被認出來
def test_pages_classified(run_result):
    result, _, _ = run_result
    assert result['skipped'] == []
    assert set(result['context']['pages']) == {'basic', 'mix', 'pitch', 'situational', 'vs'}


#管線跑出來的數字要與黃金值一致
def test_golden_values(run_result, load_json):
    result, _, _ = run_result
    assert result['context']['stats'] == load_json('splits.json')['stats']
    assert result['cross']['L']['match'] is True
    assert result['cross']['L']['parsed_ab'] == 52
    assert result['cross']['L']['parsed_h'] == 8


#S3 稽核抓到軟銀與羅德的缺口
def test_audit_reported(run_result):
    result, _, _ = run_result
    gaps = {(row['team'], row['field']): row['diff'] for row in result['audit']}
    assert gaps[('ソフトバンク', 'ab')] == 16
    assert gaps[('ロッテ', 'ab')] == 1


#run.ndjson 每行皆為合法 JSON 且含必要欄位（驗收項 V16）
def test_ndjson_format(run_result):
    _, _, out = run_result
    with open(out / 'run.ndjson', encoding='utf-8') as f:
        lines = [line for line in f.read().splitlines() if line.strip()]
    assert len(lines) > 8
    for line in lines:
        event = json.loads(line)
        assert {'ts', 'stage', 'level', 'msg', 'detail'} <= set(event)
        assert event['level'] in ('info', 'warn', 'error')
        assert event['stage'].startswith('S')


#任一非致命階段拋例外時管線不中止，errors 有記錄且後續階段仍執行（驗收項 V14）
def test_stage_failure_does_not_abort(mht_files, config, fixtures_dir, tmp_path, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError('注入的錯誤')

    #管線搬到 web.pipeline 後，階段函式在該命名空間解析 audit，patch 目標跟著改
    monkeypatch.setattr(pipeline.audit, 'audit_totals', boom)
    log = server.RunLog(path=str(tmp_path / 'run.ndjson'))
    result = server.run_pipeline(mht_files, StubRosterSource(fixtures_dir), config,
                                 log, str(tmp_path / 'report.html'))
    states = {s['id']: s['ok'] for s in result['stages']}
    assert states['S3'] is False
    assert all(states[sid] for sid in ('S4', 'S5', 'S6', 'S7', 'S8'))  #後續階段仍執行
    assert any(e['stage'] == 'S3' for e in result['errors'])
    assert result['ok'] is True  #非致命階段失敗不影響整體成敗
    assert os.path.exists(tmp_path / 'report.html')


#S8 失敗才算整體失敗（驗收項 V05，與 V14 衝突時以 V05 為準）
def test_fatal_stage_fails_whole_run(mht_files, config, fixtures_dir, tmp_path, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError('產出失敗')

    #run_pipeline 在 web.pipeline 的命名空間解析 render_html，patch 到 server 不會生效
    monkeypatch.setattr(pipeline, 'render_html', boom)
    log = server.RunLog(path=str(tmp_path / 'run.ndjson'))
    result = server.run_pipeline(mht_files, StubRosterSource(fixtures_dir), config,
                                 log, str(tmp_path / 'report.html'))
    assert result['ok'] is False
    assert [s['ok'] for s in result['stages'] if s['id'] == 'S8'] == [False]


#stages.json 只有 S8 是 fatal（驗收項 V05）
def test_only_s8_is_fatal(config):
    fatal = [s['id'] for s in config['stages']['stages'] if s['fatal']]
    assert fatal == ['S8']


#缺分頁時照樣跑完，缺的資料留空
def test_missing_pages(config, fixtures_dir, tmp_path, mht_files):
    only_vs = [item for item in mht_files if item[0].startswith('vs')]
    result = server.run_pipeline(only_vs, StubRosterSource(fixtures_dir), config,
                                 server.RunLog(), str(tmp_path / 'report.html'))
    assert result['ok'] is True
    assert result['context']['mix'] == {}
    assert result['cross']['L']['match'] is False  #沒有官方值就不能判定相符


#無法分類的檔案標記略過，不中止
def test_unknown_file_skipped(config, fixtures_dir, tmp_path):
    body = 'From: <Saved by Blink>\r\n\r\n<html>沒有特徵</html>'.encode('utf-8')
    files = [('怪檔.mht', body)]
    result = server.run_pipeline(files, StubRosterSource(fixtures_dir), config,
                                 server.RunLog(), str(tmp_path / 'report.html'))
    assert result['skipped'] == ['怪檔.mht']
    assert result['ok'] is True


#multipart 解析：取得檔名與內容
def test_parse_multipart():
    body = (b'--X\r\nContent-Disposition: form-data; name="files"; filename="a.mht"\r\n'
            b'Content-Type: application/octet-stream\r\n\r\nHELLO\r\n--X--\r\n')
    files = server.parse_multipart(body, 'multipart/form-data; boundary=X')
    assert files == [('a.mht', b'HELLO')]
    assert server.parse_multipart(body, 'application/json') == []


#log 寫進 run.ndjson 會進版控，不得含本機絕對路徑（倉庫要公開）
def test_log_path_hides_local_paths(tmp_path):
    from tests.conftest import ROOT

    assert server.log_path(os.path.join(ROOT, 'out', 'report.html')) == 'out/report.html'
    #跑到倉庫外（例如測試的暫存目錄）只留檔名，不得洩漏使用者目錄
    outside = server.log_path(str(tmp_path / 'report.html'))
    assert outside == 'report.html'
    assert 'Users' not in outside


#整份日誌不得出現磁碟機代號或家目錄樣式的絕對路徑
def test_run_log_has_no_absolute_path(run_result):
    _, log, _ = run_result
    blob = json.dumps(log.events, ensure_ascii=False)
    assert not re.search(r'[A-Za-z]:\\', blob)
    assert '/Users/' not in blob
    assert '/home/' not in blob

