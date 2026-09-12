#S8 產出單一 HTML：資料內嵌，離線可開
import json

#資料內嵌的佔位字串，範本必須含這一段，否則 S8 判定失敗
DATA_PLACEHOLDER = '/*__DATA__*/{}'
MIN_AB_FOR_AVG = 10  #打數低於此門檻不顯示打率，只顯示打數


#算打率字串；打數為 0 時回傳 None，不做四捨五入以外的加工
def batting_avg(hits, at_bats):
    if not at_bats:
        return None
    return f'{hits / at_bats:.3f}'.lstrip('0')


#標記薄樣本：只影響顯示層，不更動 aggregate_splits 的加總結果
def mark_thin(stats, min_ab=MIN_AB_FOR_AVG):
    marked = {}
    for team, sides in stats.items():
        marked[team] = {}
        for hand, slot in sides.items():
            cell = dict(slot)
            cell['thin'] = slot['ab'] < min_ab
            cell['avg'] = None if cell['thin'] else batting_avg(slot['h'], slot['ab'])
            marked[team][hand] = cell
    return marked


#綜觀層：不分球團的左右投合計
def overview(stats, min_ab=MIN_AB_FOR_AVG):
    result = {}
    for hand in ('R', 'L'):
        total = {'ab': 0, 'h': 0, 'hr': 0, 'so': 0, 'pitchers': 0}
        for sides in stats.values():
            slot = sides.get(hand)
            if not slot:
                continue
            for field in total:
                total[field] += slot[field]
        total['thin'] = total['ab'] < min_ab
        total['avg'] = None if total['thin'] else batting_avg(total['h'], total['ab'])
        result[hand] = total
    return result


#把原站的字串數字轉成浮點數：去掉 % 與 km/h，破折號回 None
#為什麼要轉：畫面要依用球比例排序、依比例畫長條，字串做不到，但原字串仍保留不動
def to_number(text):
    if text is None:
        return None
    cleaned = str(text).replace('%', '').replace('km/h', '').strip()
    if cleaned in ('—', '-', ''):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


#球種列表的數值版：{'対右投手': [{pitch, usage, velo, whiff, ops, avg, hr}], ...}
#hr 是整數計數，其餘為浮點數；原始字串留在 data['pitch'] 不動
def pitch_rows(pitch):
    fields = (('share', 'usage'), ('speed', 'velo'), ('whiff', 'whiff'),
              ('ops', 'ops'), ('avg', 'avg'))
    rows = {}
    for side, items in (pitch or {}).items():
        converted = []
        for item in items:
            row = {'pitch': item.get('pitch', '')}
            for source, key in fields:
                row[key] = to_number(item.get(source))
            count = to_number(item.get('hr'))
            row['hr'] = 0 if count is None else int(count)
            converted.append(row)
        rows[side] = converted
    return rows


#組出網頁要用的完整資料包，純資料進純資料出
def build_report_data(stats, unmatched, audit_diffs, cross, mix, pitch,
                      pitch_meta, team_meta, generated_at, player='', errors=None,
                      min_ab=MIN_AB_FOR_AVG, split_display=None):
    return {
        'player': player,
        'generated_at': generated_at,
        'min_ab': min_ab,
        'overview': overview(stats, min_ab),
        'split_display': dict(split_display or {}),
        'pitch_rows': pitch_rows(pitch),
        'teams': mark_thin(stats, min_ab),
        'unmatched': list(unmatched),
        'audit': list(audit_diffs),
        'cross': cross,
        'mix': mix,
        'pitch': pitch,
        'pitch_meta': pitch_meta,
        'team_meta': team_meta,
        'errors': list(errors or []),
    }


#把資料包嵌進範本，回傳完整 HTML 字串
def render_html(data, template_text):
    if DATA_PLACEHOLDER not in template_text:
        raise ValueError(f'範本缺少資料佔位 {DATA_PLACEHOLDER}')
    payload = json.dumps(data, ensure_ascii=False)
    #避免資料裡的 </script> 提早關閉標籤
    payload = payload.replace('</', r'<\/')
    return template_text.replace(DATA_PLACEHOLDER, payload)
