#打包瀏覽器版要用的管線與資料：python tools/build_web.py → docs/payload/pipeline.zip
import glob
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join('docs', 'payload', 'pipeline.zip')

#逐項列出要打包的來源，順序不影響產出（最後會排序）
INCLUDE = [
    'core/*.py',
    'adapters/*.py',
    'web/pipeline.py',
    'web/__init__.py',
    'web/report_template.html',
    'config/*.json',
    'cache/*.json',
]
#roster_http.py 是全專案唯一會連網的模組，瀏覽器沒有 CORS 也用不上，只排除出 zip、不刪檔
EXCLUDE_FILES = {'adapters/roster_http.py'}
#11 MB 的樣本、產物與上傳檔絕不能跟著上網站
EXCLUDE_DIRS = ('tests/', 'out/', 'uploads/', '__pycache__/')
#固定時間戳：內容沒變時重新打包的 zip 位元組也不變，git 才不會每次都出現差異
FIXED_TIME = (1980, 1, 1, 0, 0, 0)


#某個相對路徑是否該排除
def excluded(rel):
    if rel in EXCLUDE_FILES or rel.endswith('.pyc'):
        return True
    return any(rel.startswith(d) or f'/{d}' in rel for d in EXCLUDE_DIRS)


#列出要打包的相對路徑（斜線分隔、排序過），純讀檔案系統不寫任何東西
def collect(root=ROOT):
    paths = set()
    for pattern in INCLUDE:
        for path in glob.glob(os.path.join(root, *pattern.split('/'))):
            if os.path.isfile(path):
                paths.add(os.path.relpath(path, root).replace(os.sep, '/'))
    return sorted(p for p in paths if not excluded(p))


#把管線與資料打包成單一 zip，給瀏覽器端的 Pyodide 解開
def build(root=ROOT, out_path=None) -> str:
    out_path = out_path or os.path.join(root, DEFAULT_OUT)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for rel in collect(root):
            with open(os.path.join(root, *rel.split('/')), 'rb') as f:
                data = f.read()
            info = zipfile.ZipInfo(rel, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)
    return out_path


if __name__ == '__main__':
    path = build()
    names = collect()
    print(f'已打包 {len(names)} 個檔案 → {os.path.relpath(path, ROOT)}'
          f'（{os.path.getsize(path) // 1024} KB）')
    sys.exit(0)
