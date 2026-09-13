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

---

# EXPENSIVE-PLAN.md 執行期間的自主決策

## 5. Python 版本：沿用 `C:\Python36\python.exe`

EXPENSIVE-PLAN.md §7 預設值表指出「使用者慣用的 `c:\Python36\python.exe` 不適用於本專案」，前提是該路徑放的是 Python 3.6。
實際檢查結果：`C:\Python36\python.exe` 的版本是 **3.10.10**（目錄名沿用舊版而已），滿足 f-string 巢狀與 dict 保序的需求。
故直接沿用此直譯器，不另外安裝環境。

## 6. 新增 `core/parse_basic.py`

§4 只規定了 `parse_pitch` / `parse_mix` / `parse_vs` 三支解析器，但 `audit_totals` 需要「球團別官方合計」、
`cross_check` 需要「對左右別官方合計」，兩者都在 basic 分頁。把 basic 分頁的解析塞進其他三支都會讓職責混亂，
因此新增 `core/parse_basic.py`（`parse_split_totals`、`parse_team_totals`）。§4 指定的簽名全部原樣保留、未更動。

## 7. 新增 `tools/` 與 `web/report_template.html`

- `tools/check_imports.py`、`tools/check_stages.py`、`tools/check_complete.py`：`verify.sh` 的 L1 檢查腳本。
- `tools/run_fixtures.py`：以 fixture 跑完整管線並產出 `out/preview-report.md`（§6.3 要求的人工過目報告）。
- `web/report_template.html`：`render_html(data, template_text)` 是純函式、不得讀檔，範本因此必須是獨立檔案，由 `server.py` 讀入後傳進去。

## 8. 球團名正規化不讀設定檔

A5 規定 `core/` 不得讀檔，而 `aggregate_splits` 的簽名固定為三個參數，沒有位置可以傳入球團對照表。
因此在 `core/match.py` 以常數 `TEAM_NAMES` 鏡射 `config/team_meta.json` 的 12 個鍵，並以「最長前綴命中」把
`楽天Eagles` 還原成 `楽天`，取代既有腳本裡寫死的 `TEAM_ALIAS` 對照表。

## 9. 官方球團表缺列的球團照樣列入稽核差異

原站「チーム別の対戦成績」把 DeNA（標示為「横浜」）與阪神列為無資料，但逐投手表裡各有 2 個打數。
兩者名稱也對不起來（横浜 vs DeNA）。取較保守的做法：不靜默略過，一律列入 `audit_totals` 的差異清單（official 記為 0），
讓使用者自己判斷。V12 要求的軟銀 16 打數、羅德 1 打數不受影響。

## 10. 名冊快照 fixture 由 `hands_raw.txt` 轉出

`StubRosterSource` 需要「球團代碼 → 名冊」的資料。既有 fixture 只有 `hands_raw.txt`（82 筆，含球團與左右手），
故以它轉出 `tests/fixtures/roster/rst_{code}.json` 五份快照，**未捏造任何一筆左右手**，
並在檔案內記錄 `source` 欄位指回來源。§7 預設值表允許以既有產出當替代 fixture。

## 11. `config/settings.example.json` 的 `cache_ttl_days` 為 1

計畫 §7 的預設值是 7 天，但便宜批次已寫入 1。因為本批次不得修改 `config/`，
改為在 `web/server.py` 的 `DEFAULT_SETTINGS` 以 7 天為預設；若使用者把範例檔複製成 `settings.json`，
則以檔案內的值為準。此欄位只影響 `adapters/roster_http.py` 的真實取數，與驗收無關。

## 12. `tests/.gitkeep` 缺席不視為 T0 缺檔

CHEAP-PLAN.md 要求的骨架目錄中，`tests/` 底下沒有 `.gitkeep`，但 `tests/` 目錄本身存在且已有回歸 fixture，
骨架的目的已達成。依 §8「不得刪除或覆蓋既有檔案」與最保守原則，不補檔也不視為缺漏，僅記錄於此。

## 13. `out/report-<run>.html` 不進版控

每次執行會依 run id 產生一份 HTML，屬於即時產物。`.gitignore` 增加 `out/report-*.html`，
固定產物 `out/report.html`、`out/run.ndjson`、`out/preview-report.md` 仍進版控，方便交付後直接查看。

## 建議後續（不在本批次實作）

- `config/settings.example.json` 的 `cache_ttl_days` 建議改成 7，與計畫預設值一致。
- Short-Stop 的「横浜」與 `config/team_meta.json` 的 `DeNA` 鍵值不一致，建議在 `team_meta.json` 補一個別名欄位，
  讓稽核能把兩者對起來。
- 軟銀缺 16 打數的根因是存檔當下區塊未載入完成，建議在窗口頁面提示使用者「稽核差異偏大時請重新存檔該分頁」。
- ~~`adapters/roster_http.py` 的名冊解析尚未以真實頁面驗證過~~ 已於交付後補正：使用者手動執行時連續踩到兩個
  只有真實連線才會浮現的錯誤（User-Agent 含中文導致標頭無法以 latin-1 編碼、名冊表格結構與假設不符）。
  已抓一頁真實名冊存為 `tests/fixtures/npb/rst_e.html`，補上 `tests/test_roster_http.py` 六項離線測試。
  教訓：「唯一會連網的模組完全沒有測試」這個缺口，靠分層驗收全綠是看不出來的。

---

# 成品排版改版：以 tests/fixtures/lin-an-ko-2026-pitching.html 為準

使用者指定「排版與功能都複製」該份手作成品。`web/report_template.html` 的 CSS 與 body 結構逐字搬過來（CSS 與該檔完全相同），
差別只在資料來源改成管線的 `DATA`，以下三處為必要的一般化：頁首標題與副標由 `player`／`generated_at` 產生、
球種順序與配色改讀 `config/pitch_meta.json`（其值與該檔原本寫死的常數完全一致）、
交叉驗證結論由 `cross` 即時產生而非寫死句子。

## 1. 移除「資料校驗」專節

該份成品沒有這一節，資訊改放兩處：交叉驗證結論進「對左右投的打擊成績」的問號註記，一致性稽核差異進頁尾「資料的已知缺口」。
判斷：使用者指定的排版即為規格，且資訊沒有消失只是換位置，反而更靠近它要解釋的數字。
連帶調整 `tests/test_e2e.py::test_report_html` 移除該節標題的斷言，另加 `test_report_controls` 改驗互動元件是否齊全。

## 2. 新增顯示用的左右合計，但絕不自行計算

綜觀摘要條要顯示 OPS、上壘率、三振率，這三項不可相加（V13 明訂產出不得含自行加總的 OPS）。
作法是新增 `parse_basic.parse_split_display()`，把原站「対左右別の対戦成績」表的率值以**字串原樣**取出，
與既有 `parse_split_totals()` 並存：後者只取可加總欄位供稽核與交叉驗證，前者只供顯示。
兩者取自同一張表，以 `test_split_display_agrees_with_totals` 確保打數安打不會出現兩套數字。
微觀的左右成績卡仍然沒有 OPS，並在問號註記裡說明原因，與 V13 不衝突。

## 3. 球種列表改帶數值欄位

原 `parse_pitch` 產出的是 `'38.0%'`、`'146.4km/h'` 這類字串，無法排序也無法換算長條寬度。
新增 `render.to_number()` 與 `render.pitch_rows()` 產生數值版 `pitch_rows`，
原始字串仍原封不動留在 `data['pitch']`，避免既有使用者（與測試）受影響。

## 建議後續（不在本批次實作）

- 十二格球數階梯的空列（`沒有走到這個球數`）在目前 fixture 資料下不會出現，只在瀏覽器內以臨時抽掉球數的方式驗過，
  尚無自動化測試覆蓋。若之後有球數稀疏的真實樣本，應補一份 fixture 讓它進 L2。

---

# B 計畫便宜批次的自主決策

## 1. CB02 寫「13 個元素 id」但 §3.1 表格只列 12 個

CHEAP-PLAN-B.md 第 183 行的驗收項 CB02 稱「§3.1 表列的全部 13 個元素 id」，但 §3.1 的表格
（第 68–79 行）逐列數只有 12 列：`boot`、`boot-msg`、`picker`、`files`、`filelist`、`run`、
`progress`、`log`、`result`、`open-report`、`save-report`、`error`。判斷這是計畫文件本身的
筆誤，非隱藏的第 13 個需求（表格是「必須存在的元素 id」的完整定義來源，文字敘述的數字只是
複述）。`docs/index.html` 依表格逐一實作全部 12 個 id，不自行編造第 13 個。

## 2. `docs/.nojekyll` 同時要「非空」（CB01）又要「空檔案」（§3.4）

§1 產出清單與 CB01 都要求六個檔案「存在且非空」，但 §3.4 明訂 `.nojekyll` 就是空檔案，
這是 GitHub Pages 生態圈的標準用法（檔案本身存在即生效，內容從來不需要有東西）。
判斷維持業界慣例、保持真正空檔案，CB01 的「非空」對這一檔不適用——它的驗收精神是
「不要漏放檔案」，不是要求塞入無意義內容。

## 3. `docs/README.md`、`DEPLOY.md` 的字數上限採全字元計數（含標點與英數）

§3.5、§3.6 分別訂 400 字、1200 字上限，但沒說「字」是否含 Markdown 語法符號、英數字。
判斷採最嚴格解讀——整份檔案的全部字元數（含 `#`、`` ` ``、換行以外的標點）都算——
實際落點：`docs/README.md` 377 字、`DEPLOY.md` 1102 字，`README.md` 新增段落 238 字，
即使用最嚴格的算法仍在上限之內，不需要再壓縮。

## 4. `DEPLOY.md` 的 fixtures 大小改寫實測值

§3.6 原稿寫「約 11 MB」，實際 `du -sb tests/fixtures` 量測約 9.9 MB（四捨五入約 10 MB）。
§5 的「不得改動數值」只限定站台 1 GB、頻寬 100 GB、建置 10 次、逾時 10 分鐘這四個
GitHub 官方數字，不包含這個專案自身的資料量，因此改寫為實測的「約 10 MB」，避免文件
一開始就帶著不準確的數字。

## 建議後續（不在本批次實作）

- 本批次只做淺色模式；深色模式列為後續，需要時再補 `prefers-color-scheme` 對應的
  第二組變數值（沿用 §3.2 的變數名稱，數值待設計）。
- PWA 圖示（`manifest.webmanifest` 的 `icons`）目前留空陣列，需要使用者提供或指定
  設計方向後才能產生，不由代理人代為決定視覺風格。

