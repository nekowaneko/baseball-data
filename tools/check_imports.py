#匯入檢查：確認每支模組都能被載入且無語法錯誤（驗收項 V04）
import importlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

MODULES = [
    'core.mht', 'core.parse_pitch', 'core.parse_mix', 'core.parse_vs',
    'core.parse_basic', 'core.audit', 'core.match', 'core.aggregate', 'core.render',
    'adapters.roster', 'adapters.roster_http', 'web.server',
    #B 計畫新增的模組
    'web.pipeline', 'adapters.roster_cache', 'tools.build_web',
]


#模組檔案是否已存在（尚未實作的階段先略過，最終階段由 check_complete.py 強制齊備）
def module_exists(name):
    return os.path.exists(os.path.join(ROOT, *name.split('.')) + '.py')


#逐一匯入，失敗就印出模組名與錯誤
def main():
    failed = []
    skipped = []
    for name in MODULES:
        if not module_exists(name):
            skipped.append(name)
            continue
        try:
            importlib.import_module(name)
        except Exception as error:  #匯入失敗要指名是哪一支
            failed.append(f'{name}: {type(error).__name__}: {error}')
    for line in failed:
        print(line)
    if skipped:
        print('尚未實作（略過）：' + '、'.join(skipped))
    return 1 if failed else 0


sys.exit(main())
