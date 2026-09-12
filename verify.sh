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
