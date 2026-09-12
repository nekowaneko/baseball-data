# 中介資料格式規格

管線階段間傳遞的中介 JSON 格式。欄位取自既有產出（`vs_pitchers.json`、`splits.json`、HTML 內嵌 `DATA.teams`），不自創欄位。

## vs_pitchers.json

逐投手對戰成績，S2 輸出。頂層鍵為球團全名（含英文後綴，如 `楽天Eagles`），值為投手陣列：

| 欄位 | 說明 |
|---|---|
| `name` | 姓名 |
| `ops` | OPS 字串，無資料為 `—` |
| `avg` | 打擊率字串 |
| `ab` `h` `hr` `so` | 打數／安打／全壘打／三振（數字） |

## pitchmix.json

球團 × 左右投 × 球數 × 球種配球，S2 輸出。頂層鍵為球團名（不含英文後綴），值鍵為 `合計` / `対右投手` / `対左投手`（無資料可缺席），各為陣列：

| 欄位 | 說明 |
|---|---|
| `count` | 球數，如 `0-0`、`3-2` |
| `mix` | 球種 → 使用比例（%），只列有出現的球種 |

## splits.json

球團 × 左右手聚合，S6/S7 輸出。

- `stats`：球團名 → `{ R, L }`（缺一邊代表無資料）。每側含 `ab`、`h`、`hr`、`so`（可精確相加）、`pitchers`（涉及投手數）、`fallback`（S5 跨隊回退命中數）。
- `unmatched`：比對失敗投手陣列，每筆 `{ team, name, ab }`。

## run.ndjson

執行日誌，逐行一個事件：

| 欄位 | 說明 |
|---|---|
| `ts` | ISO 8601 時間戳 |
| `stage` | 對應 `stages.json` 的階段 id |
| `level` | `info` / `warn` / `error` |
| `msg` | 人類可讀訊息 |
| `detail` | 結構化補充資料，無則 `null` |
