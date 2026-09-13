# 配球資料處理窗口 B 計畫 — 貴批次執行計畫

> 這份文件給協作代理人自主執行。
> 前提：CHEAP-PLAN-B.md 已執行完成，其產出檔案全部存在。
> 本批次含修正迴圈，會產生較高的執行成本，成本控制條款見 §0 與 §6。
> 目標：讓整條管線在**手機瀏覽器內**以 Pyodide 執行，產出純靜態站放上 GitHub Pages，
> 全程不需要開電腦。既有的本機窗口（`python -m web.server`）必須繼續可用。

## 0. 執行協定（最高優先，違反即為失敗）

### 0.1 不提問
全程不得向使用者提問，包含確認、選擇、澄清。
未明訂處依 §7 預設值表處理；§7 未涵蓋時選擇最保守的做法，
並將決策與理由記錄在 DECISIONS.md 的新章節「B 計畫貴批次的自主決策」。
不得因為缺少網路、憑證、或無法開瀏覽器而停下來詢問。

### 0.2 工作循環
    階段實作 → 執行 ./verify.sh → 全綠？
                                  ├─ 是 → 下一階段
                                  └─ 否 → 自動修正 → 重跑

### 0.3 錯誤指紋斷路器【條款 1】
每次修正前，取失敗訊息的前三行做正規化後雜湊，得到一枚「錯誤指紋」，記錄下來。
若同一枚指紋第二次出現，**立刻停止該項目**，寫入 BLOCKERS.md
（含指紋、完整錯誤、已嘗試的修法、你判斷的根因），然後繼續處理其他項目。
輪數上限作為第二道防線，設為 3。
**不得為了讓指紋不同而改寫錯誤訊息或包裝例外。**

理由：燒錢的失敗模式不是試了很多不同方法，而是同一個錯誤被撞很多次。
單純的輪數上限擋不住重複。

### 0.4 分層驗收【條款 2】
沿用既有的 `verify.sh` 三層架構，本批次在既有層級中**追加**檢查項，不得改寫既有項：

- **L1（秒級）**：靜態檢查、匯入檢查、grep 類的結構與架構檢查
- **L2（十秒級）**：單元測試，不含覆蓋率統計
- **L3（分鐘級）**：覆蓋率、端到端流程、完整回歸

**各階段的驗收只跑 `./verify.sh`（L1+L2）。`./verify.sh all`（含 L3）只在 T6 跑一次。**
不得在 `verify.sh` 中吞掉任何一層的失敗回傳碼。

### 0.5 成本記錄【條款 6】
每階段結束時在 PROGRESS.md 記錄：該階段的修正輪數、出現過的錯誤指紋清單、
每個驗收項各失敗過幾次。全案結束時匯總成一張表，放在最終報告開頭。

### 0.6 版本控制
本專案已是 git 倉庫。開工前先確認工作區乾淨；不乾淨就先 commit 保存既有檔案。
**全程不設遠端、不執行 push、不建立 GitHub 倉庫**——公開發佈是使用者本人的決定。
每階段完成且驗收通過後 commit 一次，訊息用繁體中文。

### 0.7 語言與風格
所有註解、文件、commit 訊息、錯誤訊息使用繁體中文（臺灣用法：品質、資料、程式）。

本專案的既有風格必須延續，**不合就是白做**：

- 註解用 `#` 緊接文字、不空格，寫在被註解的定義**上方**一行，說明「為什麼」不是「做什麼」
- 函式以單行註解開頭，簡短直述
- 純函式優先，資料進資料出
- 不寫防禦性的 try/except 包裝，例外讓它往上拋，由管線層決定降級

範例（取自 `core/render.py`，照這個樣子寫）：

```python
#把原站的字串數字轉成浮點數：去掉 % 與 km/h，破折號回 None
#為什麼要轉：畫面要依用球比例排序、依比例畫長條，字串做不到，但原字串仍保留不動
def to_number(text):
    if text is None:
        return None
```

JavaScript 沿用 `web/report_template.html` 的風格：`const` 箭頭函式、無分號結尾、
註解同樣用 `//` 緊接文字說明為什麼。

## 1. 本批次範圍

| 動作 | 對象 |
|---|---|
| 新增 | `web/pipeline.py`、`adapters/roster_cache.py`、`tools/build_web.py`、`docs/app.js`、`docs/sw.js` |
| 修改 | `web/server.py`（改為引用 `web/pipeline.py`）、`core/parse_*.py`（換解析器）、`verify.sh`（追加 L1 檢查）、`tests/test_pipeline.py`（修正 monkeypatch 目標） |
| 新增測試 | `tests/test_pipeline_module.py`、`tests/test_roster_cache.py`、`tests/test_build_web.py` |
| **不動** | `core/render.py` 的既有函式簽名、`web/report_template.html`、`config/`、`cache/` 內容、既有兩份 PLAN、`out/` |

### 1.1 既有驗收不得退化
既有的 V01–V19 與全部 97 項測試必須仍然通過，任何退化即視為失敗。
依條款 2，這項完整回歸屬於 L3，**只在 T6 跑一次**，不要每階段都重跑整套。

## 2. 不可協商的架構約束

| # | 約束 | 理由 |
|---|---|---|
| A1 | `core/` 不得 import 網路模組（既有 V01） | 既有地基，不得因本批次退化 |
| A2 | `core/` 不得出現 `open(`、`os.environ`（既有 V03） | 同上 |
| A3 | `web/pipeline.py` 不得 import `http.server`、`socketserver`、`socket`、`threading` | Pyodide 沒有可用的 socket；管線必須能在瀏覽器內 import |
| A4 | 全專案 `.py` 不得再以 `'lxml'` 作為 BeautifulSoup 的解析器 | lxml 是 C 擴充，換成標準庫 `html.parser` 可讓載入量與相依性降到最低 |
| A5 | `docs/` 下除了 Pyodide 的 CDN 位址外，不得出現任何外部網域或 `localhost` | 靜態站必須自足；唯一例外見 §7 |
| A6 | `tools/build_web.py` 產生的 zip 不得含 `tests/`、`out/`、`uploads/`、`__pycache__`、`.pyc` | 避免把 11 MB 樣本與產物打包進網站 |

**每一條架構約束都有一個對應的驗收項（V-B01…V-B06）檢查它本身沒被違反。**

## 3. 目錄結構

```
web/
  pipeline.py          # 從 server.py 抽出的八階段編排，純邏輯，無 HTTP
  server.py            # 本機窗口，改為 from web.pipeline import ...
adapters/
  roster_cache.py      # 從 cache/*.json 讀名冊的 RosterSource 實作（瀏覽器用）
tools/
  build_web.py         # 打包 docs/payload/pipeline.zip
docs/
  index.html           # 便宜批次已產出，本批次不得改動其元素 id
  style.css            # 便宜批次已產出
  app.js               # 本批次：Pyodide 啟動、讀檔、跑管線、顯示結果
  sw.js                # 本批次：service worker，離線快取
  payload/
    pipeline.zip       # 由 build_web.py 產生，不進 git 以外的手動編輯
tests/
  test_pipeline_module.py
  test_roster_cache.py
  test_build_web.py
```

## 4. 模組介面規格

**不得修改既有函式的簽名**，否則既有 97 項測試會連鎖失效。

### 4.1 `web/pipeline.py`

從 `web/server.py` **原樣搬移**以下物件，內容不得趁機改寫：

```python
DEFAULT_SETTINGS, CONFIG_FILES, LOG_PATH, REPORT_TEMPLATE, ROOT
def load_config(root=ROOT)
class RunLog
def s1_classify(ctx) ... def s8_render(ctx)
STAGE_FUNCS
def new_context(files, roster_source, config, log, output_path, player='')
def run_pipeline(files, roster_source, config, log=None, output_path=None, player='')
```

`web/server.py` 改為 `from web.pipeline import (...)` 後重新匯出，讓
`server.run_pipeline`、`server.load_config`、`server.RunLog` 這些既有引用全部仍然有效。

**已知耦合**：`tests/test_pipeline.py::test_stage_failure_does_not_abort` 目前
`monkeypatch.setattr(server, 'render_html', boom)`。搬移後 `run_pipeline` 在
`web.pipeline` 的命名空間解析 `render_html`，patch 到 `server` 會失效。
**修法固定為**：把該測試改成 patch `web.pipeline` 的 `render_html`。
**不得**為了讓舊 patch 生效而在 `server.py` 裡重寫一份管線。

### 4.2 `adapters/roster_cache.py`

```python
#從預先打包的 cache/*.json 讀名冊，不連網，給瀏覽器版用
class CachedRosterSource:
    def __init__(self, cache_dir='cache'): ...
```

必須與 `adapters/roster.py` 的 `RosterSource` 介面相容——先讀該檔確認方法名稱與
回傳形狀，**照既有的來**，不要自創。快取檔格式為
`{npb_code, fetched_at, source, players}`，共 12 隊。
**不檢查 TTL**：瀏覽器版沒有重抓的能力，過期也只能用，過期與否交給頁面顯示 `fetched_at`。
取不到某隊時回傳空清單並讓 S4 照既有方式記 warn，不得拋例外中止。

### 4.3 `tools/build_web.py`

```python
#把管線與資料打包成單一 zip，給瀏覽器端的 Pyodide 解開
def build(root=ROOT, out_path=None) -> str   #回傳產出的 zip 路徑
```

zip 內容固定為：`core/`、`adapters/`（**排除 `roster_http.py`**，它是唯一會連網的模組）、
`web/pipeline.py`、`web/__init__.py`、`config/*.json`、`cache/*.json`、
`web/report_template.html`。
排除規則見 A6。產出路徑預設 `docs/payload/pipeline.zip`。
可直接以腳本執行（`python tools/build_web.py`）。

### 4.4 `docs/app.js`

流程固定為：

1. 從 CDN 載入 Pyodide（版本鎖 `v314.0.6`，見 §7），更新 `#boot-msg`
2. `pyodide.loadPackage('beautifulsoup4')`——**不要用 micropip 連 PyPI**，
   beautifulsoup4 4.14.3 已內建於 Pyodide
3. `fetch('payload/pipeline.zip')` → `pyodide.unpackArchive(buffer, 'zip')`
4. 隱藏 `#boot`、顯示 `#picker`
5. 使用者選檔後列進 `#filelist`，滿一個檔以上就解除 `#run` 的 `disabled`
6. 按下 `#run`：把每個檔讀成 `Uint8Array`，組成 `[(檔名, bytes), ...]` 傳進
   `web.pipeline.run_pipeline`，`roster_source` 用 `CachedRosterSource()`
7. `RunLog` 的 `sink` 接一個 JS 回呼，即時把事件寫進 `#log`、更新 `#progress`
8. 完成後從虛擬檔案系統讀回產出的 HTML，建成 Blob URL：
   `#open-report` 指向它、`#save-report` 加 `download` 屬性
9. 任何例外寫進 `#error` 並保留 `#log` 內容，不得靜默失敗

**不得**把 MHT 內容送到任何網路位址。

### 4.5 `docs/sw.js`

快取 `index.html`、`style.css`、`app.js`、`manifest.webmanifest`、`payload/pipeline.zip`。
策略固定為 cache-first、快取名稱含版本字串，啟用時清掉舊版本快取。
**Pyodide 的 CDN 資源不主動快取**（跨網域、量大，交給瀏覽器自己的 HTTP 快取）。

## 5. 實作階段

| 階段 | 內容 | 完成條件 |
|---|---|---|
| T0 | 確認 CHEAP-PLAN-B.md §2 的 6 個檔案全部存在且非空 | 清單齊全 |
| T1 | 抽出 `web/pipeline.py`，`server.py` 改為引用；修正 `test_pipeline.py` 的 patch 目標；新增 `test_pipeline_module.py` | `./verify.sh` 全綠 |
| T2 | 全專案解析器換成 `html.parser`；新增 A4 的 grep 驗收 | `./verify.sh` 全綠，**既有測試的斷言值一個都不准改** |
| T3 | `adapters/roster_cache.py` + `test_roster_cache.py` | `./verify.sh` 全綠 |
| T4 | `tools/build_web.py` + `test_build_web.py`，產出 `docs/payload/pipeline.zip` | `./verify.sh` 全綠，zip 內容符合 §4.3 |
| T5 | `docs/app.js`、`docs/sw.js`；`verify.sh` 追加 A5 的 grep | `./verify.sh` 全綠 |
| T6 | 完整驗收 `./verify.sh all`，寫 `ACCEPTANCE-B.md`、`CHECKLIST-B.md`、`out/preview-web.md` | 全部驗收項通過 |

T0 若發現缺檔，**停止並寫入 BLOCKERS.md，不要自行補寫**——
那些內容屬於便宜批次，用貴的方式重做是純粹的浪費。

## 6. 驗收清單

### 6.1 自動驗收項【條款 5】

| # | 層 | 驗收項 | 判定方式 |
|---|---|---|---|
| V-B01 | L1 | A1：`core/` 無網路模組 import（既有 V01 沿用） | grep |
| V-B02 | L1 | A2：`core/` 無 `open(`、`os.environ`（既有 V03 沿用） | grep |
| V-B03 | L1 | A3：`web/pipeline.py` 未 import `http.server`/`socket`/`socketserver`/`threading` | grep |
| V-B04 | L1 | A4：全專案 `.py` 無 `'lxml'` 字串 | grep |
| V-B05 | L1 | A5：`docs/*.js`、`docs/*.html` 無 `localhost`、無 `127.0.0.1`、無 CDN 白名單以外的網域 | grep |
| V-B06 | L2 | A6：產出的 zip 不含 `tests/`、`out/`、`uploads/`、`.pyc`、`roster_http.py` | 解 zip 列表並斷言 |
| V-B07 | L1 | 全模組可匯入（既有 V04 沿用，需涵蓋新模組） | `tools/check_imports.py` |
| V-B08 | L2 | `web.pipeline` 可在未 import `web.server` 的情況下獨立匯入並跑完管線 | 子行程中只 import pipeline |
| V-B09 | L2 | `server.run_pipeline`、`server.load_config`、`server.RunLog` 仍可用 | 匯入並斷言為可呼叫 |
| V-B10 | L2 | `CachedRosterSource` 讀得到 12 隊、格式含 `players` | 斷言 |
| V-B11 | L2 | 缺某隊快取時 `CachedRosterSource` 回空清單不拋例外 | 指向空目錄並斷言 |
| V-B12 | L2 | zip 內含 `core/render.py`、`web/pipeline.py`、`config/pitch_meta.json`、`cache/rst_e.json`、`web/report_template.html` | 解 zip 列表並斷言 |
| V-B13 | L2 | zip 大小小於 1 MB | 斷言 |
| V-B14 | L2 | `docs/app.js` 鎖定的 Pyodide 版本字串與 §7 一致 | grep |
| V-B15 | L2 | `docs/index.html` 的 13 個元素 id 全部被 `app.js` 引用到 | 交叉 grep |
| V-B16 | L2 | 全部測試在無網路下通過，未發出真實請求（既有 V17 沿用） | `conftest.py` 的 `block_network` |
| V-B17 | L3 | 既有 97 項測試全數通過，無退化 | `pytest` |
| V-B18 | L3 | 黃金值回歸：對左合計 52 打數 8 安打（既有 V11 沿用） | `pytest` |
| V-B19 | L3 | `core/` 覆蓋率 ≥ 80%（既有 V19 沿用） | `pytest --cov` |

**禁止為了通過驗收而做的事**：修改驗收標準、skip 測試、放寬斷言、改弱 grep 條件、
在 `verify.sh` 中吞掉失敗回傳碼、包裝例外以改變錯誤指紋。
確實無法通過的項目走 §0.3 的斷路器流程。

### 6.2 耦合驗收項【條款 3】

| 項目 | 與之衝突 | 衝突時的優先順序 |
|---|---|---|
| V-B03 `web/pipeline.py` 不得 import `http.server` | 本機窗口 `python -m web.server` 仍須能啟動（V-B09） | **兩者並存，方向固定**：`server.py` import `pipeline.py`，絕不反向。若出現循環相依，把共用常數留在 `pipeline.py` |
| V-B04 解析器換成 `html.parser` | V-B18 黃金值與既有 97 項測試的斷言值不得改變 | **V-B18 優先**：若某個解析結果因換解析器而改變，修的是解析程式碼，**不是測試斷言**。修不好就走斷路器，保留 lxml 並記錄在 BLOCKERS.md |
| V-B06/A6 zip 排除 `roster_http.py` | 本機的 `python adapters/roster_http.py` 仍須能執行 | **兩者並存**：只排除出 zip，不得刪除或改動該檔 |
| V-B05 `docs/` 不得出現外部網域 | Pyodide 必須從 CDN 載入 | **明訂白名單**：只允許 `cdn.jsdelivr.net`，其餘一律視為違規 |
| V-B13 zip < 1 MB | 名冊與設定必須完整打包 | **完整性優先**：12 隊名冊約 33 KB，程式約 64 KB，遠低於上限；若真的超過，先查是不是誤打包了 `tests/` |

### 6.3 移出自動層的項目【條款 4】

| 項目 | 為何無法自動判定 | 改為 |
|---|---|---|
| Pyodide 在真實手機瀏覽器能否啟動、耗時多久 | 需要真實裝置與網路，非決定性 | 使用者依 `CHECKLIST-B.md` 實機驗 |
| 上傳 5 份 MHT 後的實際產出是否正確 | 需要人眼比對報表 | 同上 |
| 離線（飛航模式）二次開啟能否運作 | 依賴瀏覽器快取狀態 | 同上 |
| 版面在各尺寸手機的觀感 | 需要人的審美判斷 | 同上 |

自動層對這些項目唯一允許的檢查是「`out/preview-web.md` 報告檔有被產生出來」。

### 6.4 人工檢查清單
其餘檢查寫進 `CHECKLIST-B.md`，由使用者在交付後自己掃一遍，至少包含：
實機開啟、選 5 份 MHT、跑完八階段、產出可開可存、飛航模式重開、加到主畫面。

## 7. 預設值表（不要為這些提問）

| 問題 | 預設值 |
|---|---|
| Python 版本 | 3.10（本機）；瀏覽器端由 Pyodide 決定，程式不得用 3.11+ 語法 |
| Pyodide 版本 | 鎖定 `v314.0.6`，來源 `https://cdn.jsdelivr.net/pyodide/v314.0.6/full/pyodide.js` |
| bs4 取得方式 | `pyodide.loadPackage('beautifulsoup4')`，**不用 micropip 連 PyPI** |
| BeautifulSoup 解析器 | `'html.parser'`（已實測 90 項測試全通過） |
| 若 `html.parser` 造成任一既有斷言失敗 | 走斷路器，保留 `'lxml'` 並改用 `pyodide.loadPackage('lxml')`，記錄在 DECISIONS.md |
| 名冊來源 | 預先打包的 `cache/*.json`，不檢查 TTL，不在瀏覽器內連 npb.jp（無 CORS） |
| 產出顯示方式 | Blob URL，`#open-report` 開新分頁、`#save-report` 下載 |
| 產出檔名 | `report-<YYYYMMDD-HHMM>.html` |
| 虛擬檔案系統的輸出路徑 | `/out/report.html` |
| 上傳檔數不足 5 份 | 照跑，缺的分頁由既有 S2 降級邏輯記 warn |
| 單檔大小上限 | 沿用 `config/settings.example.json` 的 `max_upload_size_mb`（20） |
| 覆蓋率門檻 | 維持 80%，不得調低 |
| 某套件在此環境安裝失敗時 | 改用標準庫替代方案並記錄在 DECISIONS.md，不得降低安全性 |
| 兩種實作都合理時 | 選較保守、較容易測試的那個 |
| 要不要改用 PyScript 之類的封裝 | 否，直接用 Pyodide，少一層相依 |
| 要不要做深色模式、多語系、圖示 | 否，列進 DECISIONS.md 的建議後續 |

## 8. 絕對禁止事項

- 不得向使用者提問。
- 不得連線真實外部服務、不得在測試中呼叫真實 API（驗收全程離線）。
- **不得建立 GitHub 倉庫、不得設遠端、不得 push。** 公開發佈是使用者本人的決定。
- 不得把 MHT 內容或產出送到任何網路位址。
- 不得刪除或覆蓋既有檔案；有衝突則將既有檔案改名保留。
- 不得修改既有函式簽名、不得修改 `web/report_template.html`。
- 不得改動 `docs/index.html` 的元素 id。
- 不得為了讓測試通過而修改既有測試的斷言值（V-B18 的耦合規則）。
- 不得安裝與本計畫無關的套件。
- 不得執行 CHEAP-PLAN-B.md 的內容。
- 不得修改既有的 CHEAP-PLAN.md、EXPENSIVE-PLAN.md、ACCEPTANCE.md。

## 9. 完成後的通知格式

    ✅ B 計畫貴批次完成，請查核。

    驗收結果：V-B01–V-B19 全部通過（或：通過 n 項，m 項未通過，詳見 BLOCKERS.md）
    既有 97 項測試無退化

    成本摘要：
    | 階段 | 修正輪數 | 觸發過的錯誤指紋 |
    |---|---|---|
    | T1 | <n> | <n> 種 |
    合計修正輪數：<n>

    Commit 數：<n>
    測試數：<n> 個，core/ 覆蓋率 <n>%
    docs/payload/pipeline.zip：<n> KB

    需要你人工完成的事：
    1. 依 DEPLOY.md 建立 public 倉庫並啟用 GitHub Pages（我不會做這步）
    2. 依 CHECKLIST-B.md 用手機實機驗一輪
    3. 看 out/preview-web.md

    自主決策列在 DECISIONS.md，共 <n> 項。

## 10. 故意不做的事

- 不做名冊的線上更新（npb.jp 無 CORS，瀏覽器抓不到）；名冊靠使用者偶爾在電腦上跑
  `python adapters/roster_http.py` 後重新打包，一季一兩次。
- 不做 serverless 代理、不做任何後端。
- 不做多球員管理、不做歷史紀錄保存。
- 不移除本機窗口，兩條路並存。
- 不擴充範圍；有建議寫進 DECISIONS.md 的「建議後續」段落，不要實作。
