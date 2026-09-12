# 自主決策紀錄

CHEAP-PLAN.md 執行期間，未明訂處依 §4 預設值表處理，以下為需要額外說明的決策。

## 1. README.md 衝突處理

既有 `README.md`（初始化提交留下）內容過於簡略，不含「啟動方式」「資料流概述」，不符 CHEAP-PLAN.md §2 契約。依 §6「不得刪除或覆蓋既有檔案；有衝突則將既有檔案改名保留」，將原檔改名為 `README.original.md`，另寫符合契約的新版 `README.md`。

## 2. 空目錄骨架與 EXPENSIVE-PLAN.md 的落差

CHEAP-PLAN.md §2 列出的空目錄骨架為 `core/、adapters/、web/、tests/、fixtures/、cache/、out/`（七個，含頂層 `fixtures/`）。但 `EXPENSIVE-PLAN.md`（使用者本人於本次對話前已修改，尚未提交）已將目錄結構改為 `tests/fixtures/`（巢狀），且該路徑下已有實際回歸測試樣本（5 份 MHT、`vs_pitchers.json`、`splits.json`、成品 HTML）。

判斷：`EXPENSIVE-PLAN.md` 的異動是使用者本人較新的決定，優先於 CHEAP-PLAN.md 尚未同步更新的舊路徑。故不另建頂層 `fixtures/` 空資料夾，改以既有 `tests/fixtures/` 視為滿足「fixtures 骨架」要求；C09 驗收依此解讀為檢查 `core/、adapters/、web/、tests/、cache/、out/` 六個頂層資料夾，加上 `tests/fixtures/` 存在。

## 3. config/settings.example.json 內容

CHEAP-PLAN.md 未給出此檔的具體欄位，僅要求「不得含真實路徑以外的敏感資訊」。依 EXPENSIVE-PLAN.md §3–§4 揭露的模組介面（`web/server.py`、NPB 名冊介面、快取機制），推得以下欄位為必要且合理的預設：`upload_dir`、`cache_dir`、`output_dir`、`npb_roster_base_url`、`cache_ttl_days`、`min_ab_for_avg`（取自 HANDOFF.md §4 的門檻值 10）、`max_upload_size_mb`、`server_port`。皆為路徑或參數，不含憑證。

## 4. config/team_meta.json 的鍵值選擇

團隊鍵一律採用 Short-Stop／既有成品 HTML 使用的日文球團名（如 `楽天`、`日本ハム`），而非中文名或英文暱稱，以與 `vs_pitchers.json`、`splits.json`、`pitchmix.json` 既有資料的鍵值格式一致，避免下游比對時還要做名稱轉換。

## 建議後續（不在本批次實作）

- `config/settings.example.json` 的欄位待 EXPENSIVE-PLAN.md 實際寫出 `web/server.py` 後，應回頭核對欄位名稱與程式中讀取的設定鍵是否一致。
- 若使用者確認不再需要 `README.original.md`，可在下次維護時整併或刪除。
