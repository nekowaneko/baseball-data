# 執行進度與成本紀錄

依 EXPENSIVE-PLAN.md §0.5，逐階段記錄修正輪數、錯誤指紋與各驗收項失敗次數。

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
- 額外人工冒煙測試（不計入自動驗收）：在 127.0.0.1:8799 啟動伺服器，
  上傳五份 MHT → SSE 收到 50 筆事件 → 整體成功 → 下載產物 42,626 bytes 且含「綜觀」區塊。
