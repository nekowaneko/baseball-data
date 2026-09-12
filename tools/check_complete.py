#完備檢查：最終階段必須所有模組檔案都到位（配合 V04 的匯入檢查）
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REQUIRED = [
    'core/mht.py', 'core/parse_pitch.py', 'core/parse_mix.py', 'core/parse_vs.py',
    'core/parse_basic.py', 'core/audit.py', 'core/match.py', 'core/aggregate.py',
    'core/render.py', 'adapters/roster.py', 'adapters/roster_http.py',
    'web/server.py', 'web/index.html', 'web/app.js', 'web/report_template.html',
]

missing = [p for p in REQUIRED if not os.path.exists(os.path.join(ROOT, p))]
for path in missing:
    print(f'缺少檔案：{path}')
sys.exit(1 if missing else 0)
