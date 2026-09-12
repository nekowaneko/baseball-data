#球團配球解析測試
from core import parse_mix

#按鈕的 title 屬性含「対左投手から受けた配球を表示」，用純字串比對會在錯誤位置切開
BUTTON_TITLE_TRAP = '対左投手から受けた配球を表示'


#六個球團各有合計區塊，養樂多沒有對左資料
def test_team_sections(page):
    mix = parse_mix.parse_team_mix(page('mix'))
    assert set(mix) == {'ソフトバンク', 'オリックス', '楽天', '日本ハム', 'ロッテ', 'ヤクルト'}
    assert '対左投手' not in mix['ヤクルト']


#區塊切分不被按鈕 title 誤導：對右 12 列、對左 12 列（驗收項 V09）
def test_section_rows(page):
    html = page('mix')
    assert BUTTON_TITLE_TRAP in html  #陷阱確實存在於 fixture
    mix = parse_mix.parse_team_mix(html)
    for team, sections in mix.items():
        for name, rows in sections.items():
            assert len(rows) == 12, f'{team} {name} 列數不是 12'
            assert [r['count'] for r in rows][:3] == ['0-0', '1-0', '2-0']


#色塊總數與 fixture 一致（驗收項 V10）
def test_total_blocks(page):
    mix = parse_mix.parse_team_mix(page('mix'))
    total = sum(len(row['mix'])
                for sections in mix.values()
                for rows in sections.values()
                for row in rows)
    assert total == 675


#色塊數值取自 title 屬性，為百分比浮點數
def test_block_values(page):
    mix = parse_mix.parse_team_mix(page('mix'))
    first = mix['ソフトバンク']['合計'][0]
    assert first['count'] == '0-0'
    assert first['mix']['ストレート'] == 44.2
