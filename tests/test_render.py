#HTML 產出測試
import json

import pytest
from bs4 import BeautifulSoup

from core import render

STATS = {
    '楽天': {'R': {'ab': 34, 'h': 16, 'hr': 2, 'so': 6, 'pitchers': 13, 'fallback': 0},
             'L': {'ab': 10, 'h': 1, 'hr': 0, 'so': 3, 'pitchers': 4, 'fallback': 0}},
    'ソフトバンク': {'L': {'ab': 7, 'h': 0, 'hr': 0, 'so': 4, 'pitchers': 3, 'fallback': 0}},
}


#範本文字
@pytest.fixture(scope='session')
def template():
    import os
    from tests.conftest import ROOT

    with open(os.path.join(ROOT, 'web', 'report_template.html'), encoding='utf-8') as f:
        return f.read()


#打率字串去掉前導零，打數為 0 時回傳 None
def test_batting_avg():
    assert render.batting_avg(8, 52) == '.154'
    assert render.batting_avg(0, 0) is None


#打數低於 10 的格子標記 thin 且不給打率（驗收項 V15）
def test_mark_thin():
    marked = render.mark_thin(STATS)
    assert marked['楽天']['R']['thin'] is False
    assert marked['楽天']['R']['avg'] == '.471'
    assert marked['楽天']['L']['thin'] is False  #門檻是「低於 10」，剛好 10 打數不算薄
    assert marked['ソフトバンク']['L']['thin'] is True
    assert marked['ソフトバンク']['L']['avg'] is None


#thin 只影響顯示層，不得改動加總結果（V15 與 V11 衝突時以 V11 為準）
def test_mark_thin_keeps_totals():
    marked = render.mark_thin(STATS)
    assert marked['ソフトバンク']['L']['ab'] == 7
    assert STATS['ソフトバンク']['L'] == {'ab': 7, 'h': 0, 'hr': 0, 'so': 4,
                                          'pitchers': 3, 'fallback': 0}


#綜觀層把各球團同一側加總起來
def test_overview():
    result = render.overview(STATS)
    assert result['R']['ab'] == 34
    assert result['L']['ab'] == 17
    assert result['L']['thin'] is False


#原站的字串數字轉成浮點數：去掉單位，破折號與空白回 None
def test_to_number():
    assert render.to_number('38.0%') == 38.0
    assert render.to_number('146.4km/h') == 146.4
    assert render.to_number('.428') == 0.428
    assert render.to_number('0.0%') == 0.0      #零是有效值，不可當成缺值
    assert render.to_number('—') is None
    assert render.to_number('') is None
    assert render.to_number(None) is None
    assert render.to_number('あ') is None      #轉不動就回 None，不拋例外


#球種列的數值版供排序與長條使用；全壘打是整數計數，缺值補 0
def test_pitch_rows():
    rows = render.pitch_rows({'対左投手': [
        {'pitch': 'ストレート', 'share': '38.0%', 'speed': '146.4km/h',
         'whiff': '12.1%', 'ops': '.428', 'avg': '.111', 'hr': '1'},
        {'pitch': 'カーブ', 'share': '4.9%', 'speed': '122.2km/h',
         'whiff': '50.0%', 'ops': '—', 'avg': '—', 'hr': '0'},
    ]})['対左投手']
    assert rows[0] == {'pitch': 'ストレート', 'usage': 38.0, 'velo': 146.4,
                       'whiff': 12.1, 'ops': 0.428, 'avg': 0.111, 'hr': 1}
    assert rows[1]['ops'] is None               #原站沒給就留 None，畫面顯示破折號
    assert rows[1]['hr'] == 0


#原始字串必須原封不動留在 data['pitch']，數值版只是另外加一份
def test_pitch_rows_keeps_raw_strings():
    pitch = {'対左投手': [{'pitch': 'ストレート', 'share': '38.0%'}]}
    data = render.build_report_data({}, [], [], {}, {}, pitch, {}, {}, '2026-09-12')
    assert data['pitch']['対左投手'][0]['share'] == '38.0%'
    assert data['pitch_rows']['対左投手'][0]['usage'] == 38.0


#顯示用的左右合計照字串搬進資料包，沒有傳就留空字典
def test_split_display_passthrough():
    display = {'L': {'ops': '.451', 'ab': '52'}}
    data = render.build_report_data({}, [], [], {}, {}, {}, {}, {}, '2026-09-12',
                                    split_display=display)
    assert data['split_display'] == display
    assert render.build_report_data({}, [], [], {}, {}, {}, {}, {},
                                    '2026-09-12')['split_display'] == {}


#產出的 HTML 可解析，且含必要區塊與內嵌資料
def test_render_html(template):
    data = render.build_report_data(
        STATS, [{'team': 'DeNA', 'name': '東 克樹', 'ab': 2}],
        [{'team': 'ソフトバンク', 'field': 'ab', 'parsed': 36, 'official': 52, 'diff': 16}],
        {'L': {'parsed_ab': 52, 'parsed_h': 8, 'official_ab': 52, 'official_h': 8, 'match': True}},
        {}, {}, {'order': [], 'colors': {}, 'zh': {}}, {},
        '2026-09-12 12:00', player='林 安可')
    html = render.render_html(data, template)
    soup = BeautifulSoup(html, 'lxml')
    headings = [h.get_text(strip=True) for h in soup.find_all(['h2', 'h3'])]
    assert '綜觀' in headings
    assert '微觀' in headings
    assert '資料的已知缺口' in headings
    assert '林 安可' in html
    assert render.DATA_PLACEHOLDER not in html


#資料裡的 </script> 不得提早關閉標籤
def test_render_escapes_closing_tag(template):
    data = render.build_report_data({}, [], [], {}, {}, {}, {}, {}, '2026-09-12',
                                    player='</script><b>x')
    html = render.render_html(data, template)
    assert '</script><b>x' not in html
    assert html.count('</script>') == 1


#範本缺佔位時拋例外，由 S8 判定整體失敗
def test_render_requires_placeholder():
    with pytest.raises(ValueError):
        render.render_html({}, '<html></html>')


#內嵌資料是合法 JSON
def test_embedded_json_is_valid(template):
    data = render.build_report_data(STATS, [], [], {}, {}, {}, {}, {}, '2026-09-12')
    html = render.render_html(data, template)
    payload = html.split('const DATA = ')[1].split('\n')[0]
    assert json.loads(payload.replace(r'<\/', '</'))['teams']['楽天']['R']['ab'] == 34
