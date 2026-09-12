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


#組出網頁要用的完整資料包，純資料進純資料出
def build_report_data(stats, unmatched, audit_diffs, cross, mix, pitch,
                      pitch_meta, team_meta, generated_at, player='', errors=None,
                      min_ab=MIN_AB_FOR_AVG):
    return {
        'player': player,
        'generated_at': generated_at,
        'min_ab': min_ab,
        'overview': overview(stats, min_ab),
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
    payload = payload.replace('</', '<\/')
    return template_text.replace(DATA_PLACEHOLDER, payload)
