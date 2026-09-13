> 本文含代碼化的本機資訊，`<代碼>` 的實際值見 LOCAL-CODEBOOK.md（未進版控，僅存在本機）。

# 執行進度與成本紀錄

依 EXPENSIVE-PLAN.md §0.5，逐階段記錄修正輪數、錯誤指紋與各驗收項失敗次數。

## 成本摘要

| 階段 | 修正輪數 | 觸發過的錯誤指紋 |
|---|---|---|
| T0 前置檢查 | 0 | 0 種 |
| T1 解析器 | 0 | 0 種 |
| T2 稽核與聚合 | 0 | 0 種 |
| T3 名冊介面 | 0 | 0 種 |
| T4 HTML 產出 | 2 | 2 種 |
| T5 伺服器與前端 | 1 | 1 種 |
| T6 完整驗收 | 0 | 0 種 |
| **合計** | **3** | **3 種** |

沒有任何一枚錯誤指紋重複出現，斷路器未觸發，BLOCKERS.md 未產生。

## T0 前置檢查

CHEAP-PLAN.md §2 交接清單全部存在且非空（README.md、config/ 四檔、docs/ 兩檔、CHECKLIST.md、骨架目錄）。
`tests/.gitkeep` 不存在，但 `tests/` 目錄本身存在且已有 fixture，視為骨架要求已滿足（見 DECISIONS.md）。

- 修正輪數：0
- 錯誤指紋：無

## T1 MHT 拆封與三支解析器

- 修正輪數：0（`verify.sh` L1+L2 首次執行即全綠）
- 錯誤指紋：無
- 各驗收項失敗次數：V01–V05 各 0、V09 0、V10 0
- 備註：`core/parse_vs.py` 的解析結果與既有黃金產出 `tests/fixtures/vs_pitchers.json` 完全相同。

## T2 稽核、姓名比對與聚合

- 修正輪數：0（首次執行即全綠）
- 錯誤指紋：無
- 各驗收項失敗次數：V06–V08、V11–V13 各 0
- 備註：`aggregate_splits` 的輸出與既有黃金產出 `tests/fixtures/splits.json` 完全相同，
  對左合計 52 打數 8 安打，跨隊回退命中 3 人（阪神 2、DeNA 1）。

## T3 名冊取數介面與 Stub

- 修正輪數：0（首次執行即全綠）
- 錯誤指紋：無
- 各驗收項失敗次數：V02 0、V17 0
- 備註：由既有 `tests/fixtures/hands_raw.txt` 轉出五份名冊快照 JSON 當 Stub 資料，
  未捏造任何一筆左右手；以 Stub 建出的對照表可完整還原黃金值。

## T4 HTML 產出

- 修正輪數：2
- 錯誤指紋：
  - `a1f0-render-placeholder`：`JSONDecodeError: Extra data`——範本佔位只換掉註解、未換掉後面的預設 `{}`，
    產出 `const DATA = {...}{}` 的壞語法。修法：佔位字串改為 `/*__DATA__*/{}`，連同預設值一起取代。
  - `b7c3-thin-threshold`：`assert False is True`——測試把薄樣本門檻寫成「10 打數以下」，
    但規格是「低於 10 打數」。修法：更正測試斷言，不動實作（門檻值來自 HANDOFF.md）。
- 各驗收項失敗次數：V15 1、內嵌 JSON 合法性 1，其餘 0
- 追加修正：測試中 `'<\/'` 造成 DeprecationWarning，改為原始字串（不計入修正輪數，非驗收失敗）

## T5 伺服器、前端與端到端

- 修正輪數：1
- 錯誤指紋：
  - `c92b-bytes-nonascii`：`SyntaxError: bytes can only contain ASCII literal characters`
    ——測試裡的 bytes 字面值寫了中文。修法：改以 `str.encode('utf-8')` 產生位元組。
- 各驗收項失敗次數：V05 0、V14 0、V16 0、V18 0
- 追加修正：`core/render.py` 的 `'<\/'` 造成 DeprecationWarning，改為原始字串（非驗收失敗）
- 額外人工冒煙測試（不計入自動驗收）：在 `<LOCAL_TEST_ADDR>` 啟動伺服器，
  上傳五份 MHT → SSE 收到 50 筆事件 → 整體成功 → 下載產物 42,626 bytes 且含「綜觀」區塊。

## T6 完整驗收

- 修正輪數：0
- 錯誤指紋：無
- `./verify.sh all` 一次通過：L1 五項、L2 79 個測試、L3 端到端 5 個測試與覆蓋率 96.55%
- 產出 `ACCEPTANCE.md`、`out/report.html`、`out/run.ndjson`、`out/preview-report.md`

## 交付後修正（不屬於 T1–T6）

使用者手動執行 `adapters/roster_http.py` 時連續失敗三次，全部集中在唯一沒有測試覆蓋的連網模組：

| # | 症狀 | 根因 | 修法 |
|---|---|---|---|
| 1 | `ModuleNotFoundError: No module named 'adapters'` | 以腳本方式執行時 `sys.path` 只含 `adapters/` | 匯入前把專案根目錄加進 `sys.path` |
| 2 | `'latin-1' codec can't encode characters` | `USER_AGENT` 寫了中文，HTTP 標頭只能是 latin-1 | 改為純 ASCII，並依回應宣告的 charset 解碼 |
| 3 | 12 隊全部解析出 0 人 | 假設表頭是「選手名」，實際 NPB 是一張大表中間插入分段標題列，姓名欄的標題即守備位置 | 改為逐列辨識標題列、只收「投手」分段；抓真實頁面存為 fixture 並補六項測試 |

三者都是「驗收全程不連網」造成的盲區：`roster_http.py` 先前完全沒有測試。現已有 `tests/test_roster_http.py`
以真實頁面快照離線驗證，解析結果與既有 82 筆左右手對照表在樂天這一隊完全一致（17/17 相符）。

---

# B 計畫貴批次（EXPENSIVE-PLAN-B.md）

依 EXPENSIVE-PLAN-B.md §0.5，逐階段記錄修正輪數、錯誤指紋與各驗收項失敗次數。
開工前基準：`./verify.sh` L1 六項全過、L2 93 個測試通過（全套共收集 99 個，6 個為 L3）。

## T0 前置檢查

CHEAP-PLAN-B.md §2 的 6 個交接檔案全部存在：`docs/index.html` 1586 B、`docs/style.css` 2619 B、
`docs/manifest.webmanifest` 235 B、`docs/README.md` 633 B、`DEPLOY.md` 1916 B、`docs/.nojekyll` 0 B。
`.nojekyll` 依便宜批次 §3.4 本來就是空檔案，視為滿足（見 DECISIONS.md）。

- 修正輪數：0
- 錯誤指紋：無

## T1 抽出 web/pipeline.py

- 修正輪數：0
- 錯誤指紋：無
- `./verify.sh` 一次通過：L1 七項、L2 96 個測試
- 各驗收項失敗次數：V-B03 0、V-B08 0、V-B09 0、V05 0

## T2 解析器換成 html.parser

- 修正輪數：0
- 錯誤指紋：無
- 7 個 `.py` 共 10 處 `'lxml'` 改為 `'html.parser'`；測試只改了解析器參數，斷言值一個都沒動
- `./verify.sh` 一次通過：L1 八項、L2 96 個測試（含黃金值 `test_golden_values` 52 打數 8 安打）
- 各驗收項失敗次數：V-B04 0
