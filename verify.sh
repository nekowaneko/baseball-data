#!/usr/bin/env bash
#分層驗收：L1 秒級靜態檢查、L2 十秒級單元測試、L3 分鐘級覆蓋率與端到端
#用法：./verify.sh          只跑 L1 與 L2（各階段用）
#      ./verify.sh all      三層全跑（最終階段用）
set -u
cd "$(dirname "$0")"
export PYTHONIOENCODING=utf-8

LAYERS="${1:-l12}"
FAILED=0

#單項檢查：印出結果並記錄失敗，不吞掉回傳碼
check() {
  local name="$1"; shift
  if "$@" > /tmp/verify_out.$$ 2>&1; then
    echo "  [通過] $name"
  else
    echo "  [失敗] $name"
    sed 's/^/        /' /tmp/verify_out.$$ | head -40
    FAILED=1
  fi
  rm -f /tmp/verify_out.$$
}

#grep 反向檢查：命中即失敗
grep_absent() {
  ! grep -rnE "$1" core/ --include='*.py' > /dev/null 2>&1
}

#公開倉庫檢查：任何進版控的檔案都不得洩漏本機路徑，命中即失敗
no_local_paths() {
  local hits
  hits=$(git ls-files -z | xargs -0 grep -lIE '[A-Za-z]:\\Users|/Users/[A-Za-z]|/home/[a-z]' 2>/dev/null)
  if [ -n "$hits" ]; then
    echo "以下版控檔案含本機絕對路徑："
    echo "$hits"
    return 1
  fi
  return 0
}

echo "=== L1 靜態與結構檢查 ==="
#V01 core/ 不得碰網路模組
check "V01 core/ 無網路模組 import" grep_absent '^[[:space:]]*(import|from)[[:space:]]+(requests|urllib|http|socket|ssl|ftplib|telnetlib|asyncio)\b'
#V02 core/ 不得直接相依真實取數實作
check "V02 core/ 未 import roster_http" grep_absent 'roster_http'
#V03 core/ 不得寫檔或讀環境變數
check "V03 core/ 無 open( 與 os.environ" grep_absent '(\bopen\(|os\.environ|getenv)'
#V04 全部模組可匯入
check "V04 全模組可匯入" python tools/check_imports.py
#V05 階段定義與整體成敗判定
check "V05 僅 S8 fatal 且 server.py 依此判定" python tools/check_stages.py
#V20 倉庫要公開，版控檔案不得含本機絕對路徑或使用者目錄
check "V20 版控檔案無本機絕對路徑" no_local_paths

#B 計畫追加項（V01–V20 不動，只往下加）
#grep 反向檢查指定路徑：命中即失敗，路徑可為檔案或目錄
grep_absent_in() {
  local pattern="$1"; shift
  local target
  #目標不存在時 grep 回傳 2，反向後會變成假通過，所以先確認存在
  for target in "$@"; do
    case "$target" in -*) continue ;; esac
    [ -e "$target" ] || { echo "檢查目標不存在：$target"; return 1; }
  done
  ! grep -rnE "$pattern" "$@"
}
#V-B03 Pyodide 沒有可用的 socket，管線必須能在瀏覽器內 import
check "V-B03 web/pipeline.py 未 import http.server/socket/socketserver/threading" \
  grep_absent_in '^[[:space:]]*(import|from)[[:space:]]+(http\.server|http|socketserver|socket|threading)\b' web/pipeline.py
#V-B04 lxml 是 C 擴充，換成標準庫 html.parser 讓瀏覽器端的載入量與相依性降到最低
check "V-B04 全專案 .py 無 'lxml' 解析器字串" \
  grep_absent_in "[\"']lxml[\"']" --include='*.py' .

#靜態站自足檢查：docs/ 的網頁與腳本只准連 cdn.jsdelivr.net（Pyodide），其餘網域與本機位址一律違規
docs_offsite_absent() {
  local sources hits
  sources=$(ls docs/*.js docs/*.html 2>/dev/null)
  [ -n "$sources" ] || { echo "docs/ 下找不到任何 .js 或 .html"; return 1; }
  hits=$(
    grep -nE 'localhost|127\.0\.0\.1|0\.0\.0\.0' $sources
    #任何「協定://主機」都取出主機比對白名單
    grep -noE '[A-Za-z][A-Za-z0-9+.-]*://[^/"'"'"'`) ]*' $sources | grep -vE ':https://cdn\.jsdelivr\.net$'
    #沒寫協定的裸網域（例如 fonts.googleapis.com）也要抓
    grep -noE '\b[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.(com|net|org|io|dev|app|jp|tw|co|me|cloud|site)\b' $sources | grep -vE ':cdn\.jsdelivr\.net$'
  )
  if [ -n "$hits" ]; then
    echo "docs/ 出現白名單以外的位址："
    echo "$hits"
    return 1
  fi
  return 0
}
#V-B05 靜態站必須自足，唯一例外是 Pyodide 的 CDN
check "V-B05 docs/*.js、docs/*.html 只連 cdn.jsdelivr.net" docs_offsite_absent

if [ "$FAILED" -ne 0 ]; then
  echo "L1 未通過，停止後續層級"
  exit 1
fi

echo "=== L2 單元測試 ==="
python -m pytest -q -m "not l3"
if [ "$?" -ne 0 ]; then
  echo "L2 未通過，停止後續層級"
  exit 1
fi

if [ "$LAYERS" != "all" ]; then
  echo "完成：L1 與 L2 全數通過（L3 未執行）"
  exit 0
fi

echo "=== L3 端到端與覆蓋率 ==="
check "檔案完備" python tools/check_complete.py
if [ "$FAILED" -ne 0 ]; then
  echo "L3 檔案完備檢查未通過"
  exit 1
fi
python -m pytest -q -m l3
if [ "$?" -ne 0 ]; then
  echo "L3 端到端未通過"
  exit 1
fi
python -m pytest -q --cov=core --cov-report=term-missing --cov-fail-under=80
if [ "$?" -ne 0 ]; then
  echo "L3 覆蓋率未達 80%"
  exit 1
fi
echo "完成：L1、L2、L3 全數通過"
