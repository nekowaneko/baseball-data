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
