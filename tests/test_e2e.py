#端到端驗收（L3）：五份 fixture MHT 跑完八階段並產出可解析的 HTML
import json
import os

import pytest
from bs4 import BeautifulSoup

from tools import run_fixtures

pytestmark = pytest.mark.l3


#跑一次完整流程，輸出寫到專案的 out/
@pytest.fixture(scope='module')
def outcome():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return run_fixtures.run(root), os.path.join(root, 'out')


#八階段全數成功且整體判定成功（驗收項 V18）
def test_pipeline_ok(outcome):
    result, _ = outcome
    assert result['ok'] is True
    assert len(result['stages']) == 8
    assert all(stage['ok'] for stage in result['stages'])


#產出的 HTML 可解析，含綜觀、微觀與已知缺口三個必要區塊
def test_report_html(outcome):
    result, _ = outcome
    with open(result['output'], encoding='utf-8') as f:
        html = f.read()
    soup = BeautifulSoup(html, 'lxml')
    headings = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])]
    assert '綜觀' in headings
    assert '微觀' in headings
    assert '資料的已知缺口' in headings
    assert '林 安可' in html
    assert len(html) > 30000  #資料確實內嵌，不是空殼


#互動元件齊全：左右投開關、球種排序、球團選單、兩個問號註記與配球圖容器
#沒有「資料校驗」專節是刻意的，校驗結論在問號註記、稽核差異在頁尾缺口
def test_report_controls(outcome):
    result, _ = outcome
    with open(result['output'], encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'lxml')
    hands = [b['data-hand'] for b in soup.select('.switch button')]
    assert hands == ['L', 'R']
    sorts = [b['data-sort'] for b in soup.select('#sortbar button')]
    assert sorts == ['usage', 'whiff', 'ops']
    assert soup.select_one('select#team') is not None
    assert {b['data-note'] for b in soup.select('.qm')} == {'n-micro', 'n-counts'}
    for hook in ('#totals', '#plist', '#cards', '#legend', '#counts', '#cross-note', '#gaps'):
        assert soup.select_one(hook) is not None, hook


#內嵌資料含黃金值：對左 52 打數 8 安打，且薄樣本有標記
def test_embedded_data(outcome):
    result, _ = outcome
    with open(result['output'], encoding='utf-8') as f:
        html = f.read()
    payload = html.split('const DATA = ')[1].split('\n')[0]
    data = json.loads(payload.replace(r'<\/', '</'))
    assert data['overview']['L']['ab'] == 52
    assert data['overview']['L']['h'] == 8
    assert data['teams']['ソフトバンク']['L']['thin'] is True
    assert data['teams']['楽天']['R']['thin'] is False
    assert data['cross']['L']['match'] is True
    #綜觀摘要條的率值直接取自原站，不是自行重算
    assert data['split_display']['L']['ops'] == '.451'
    assert data['split_display']['L']['ab'] == '52'
    #球種列要能排序與畫長條，所以必須是數值而非字串
    straight = data['pitch_rows']['対右投手'][0]
    assert straight['pitch'] == 'ストレート'
    assert straight['usage'] == 37.5
    assert straight['velo'] == 149.3


#日誌是合法的 NDJSON，八個階段都留下事件
def test_run_log(outcome):
    _, out_dir = outcome
    with open(os.path.join(out_dir, 'run.ndjson'), encoding='utf-8') as f:
        events = [json.loads(line) for line in f.read().splitlines() if line.strip()]
    stages = {event['stage'] for event in events}
    assert stages == {'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8'}
    assert all({'ts', 'stage', 'level', 'msg', 'detail'} <= set(e) for e in events)


#人工過目用的預覽報告有被產生出來（自動層只檢查這件事）
def test_preview_report(outcome):
    _, out_dir = outcome
    path = os.path.join(out_dir, 'preview-report.md')
    assert os.path.exists(path)
    with open(path, encoding='utf-8') as f:
        text = f.read()
    assert '交叉驗證' in text
    assert '請人眼確認的項目' in text
