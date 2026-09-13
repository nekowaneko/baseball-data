#八階段管線編排：純邏輯、不含 HTTP，本機窗口與瀏覽器內的 Pyodide 共用這一份
import json
import os
import time
from datetime import datetime

from adapters.roster import collect_roster_rows
from core import aggregate, audit, match, mht, parse_basic, parse_mix, parse_pitch, parse_vs
from core.render import build_report_data, render_html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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


#log 只寫倉庫相對路徑：run.ndjson 會進版控，不能把本機絕對路徑（含使用者名稱）寫進去
def log_path(path, root=ROOT):
    try:
        rel = os.path.relpath(path, root)
    except ValueError:      #Windows 上跨磁碟機時 relpath 會拋例外
        return os.path.basename(path)
    #跑出倉庫外（例如測試的暫存目錄）就只留檔名，同樣不洩漏路徑
    return os.path.basename(path) if rel.startswith('..') else rel.replace(os.sep, '/')


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
    ctx['log'].write('S8', 'info', f"產出 {log_path(ctx['output_path'])}")


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
