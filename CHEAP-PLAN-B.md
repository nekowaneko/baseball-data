# 配球資料處理窗口 B 計畫 — 便宜批次執行計畫

> 這份文件給協作代理人自主執行。
> 本批次為純產出工作，不含修正迴圈，可用較便宜的模型執行。
> 執行順序：本批次先跑，完成後才執行 EXPENSIVE-PLAN-B.md。
> 這是 B 計畫（改成手機瀏覽器內執行的純靜態站）。既有的 CHEAP-PLAN.md 與
> EXPENSIVE-PLAN.md 是第一版本機窗口的計畫，已執行完畢，**不得修改或刪除**。

## 0. 執行協定

- **全程不得向使用者提問。** 未明訂處依 §4 預設值表處理，並記錄在 DECISIONS.md
  的新章節「B 計畫便宜批次的自主決策」。
- 本批次的驗收都是結構性檢查（檔案存在、章節齊全、元素 id 齊全、格式正確、字數上限）。
  失敗時直接補齊缺漏即可，**不需要也不應該進入反覆修正的迴圈**。
- 若某項驗收補齊兩次仍不通過，停止該項並寫入 BLOCKERS.md，繼續處理其他項目。
- 每完成一個階段就 commit。本專案已是 git 倉庫且工作區乾淨，直接使用。
  **全程不設遠端、不執行 push、不建立 GitHub 倉庫**——公開發佈由使用者本人決定。
- 所有註解、文件、commit 訊息使用繁體中文（臺灣用法：品質、資料、程式）。
- 不執行任何測試套件，不修改任何 `.py` 檔。

## 1. 本批次範圍

| 動作 | 對象 |
|---|---|
| 建立 | `docs/index.html`、`docs/style.css`、`docs/manifest.webmanifest`、`docs/.nojekyll`、`docs/README.md`、`DEPLOY.md` |
| 填入內容 | 上述各檔的完整成品內容（規格見 §3） |
| 修改 | `README.md` 加一節「手機版（GitHub Pages）」 |
| 不動 | `core/`、`adapters/`、`web/`、`tests/`、`tools/`、`config/`、`cache/`、`out/`、既有兩份 PLAN、ACCEPTANCE.md、HANDOFF.md |

`docs/app.js`、`docs/sw.js`、`tools/build_web.py` **不在本批次**，屬於 EXPENSIVE-PLAN-B.md。
本批次只負責 `index.html` 的骨架與樣式，讓貴批次寫 JS 時有固定的 DOM 可以接。

## 2. 產出檔案清單（交接契約）

本批次完成後，以下檔案必須存在且非空。EXPENSIVE-PLAN-B.md 的 T0 會檢查這份清單：

- `docs/index.html` — 手機版窗口頁面骨架，必須含 §3.1 列出的全部元素 id
- `docs/style.css` — 窗口頁面樣式，行動裝置優先
- `docs/manifest.webmanifest` — PWA 資訊清單
- `docs/.nojekyll` — 空檔案，關閉 GitHub Pages 的 Jekyll 處理
- `docs/README.md` — 說明 `docs/` 是發佈來源、哪些檔案是產生的不要手改
- `DEPLOY.md` — 使用者自己開 GitHub 倉庫並啟用 Pages 的逐步說明

## 3. 各檔案的內容規格

### 3.1 `docs/index.html`

單頁，`lang="zh-Hant"`，含 `<meta name="viewport" content="width=device-width, initial-scale=1">`。
**必須**在 `<head>` 依序引入：`style.css`、`manifest.webmanifest`（`<link rel="manifest">`）。
**不得**在本批次引入 `app.js` 以外的任何腳本；`app.js` 以
`<script type="module" src="app.js"></script>` 放在 `</body>` 前（檔案此時尚不存在，這是預期的）。

必須存在的元素 id（貴批次的 `app.js` 會依賴這些，**名稱不得更動**）：

| id | 元素 | 用途 |
|---|---|---|
| `boot` | `<div>` | Pyodide 載入中的狀態區，預設可見 |
| `boot-msg` | `<p>` | 載入進度文字，初值「正在準備執行環境…」 |
| `picker` | `<div>` | 選檔區，預設以 `hidden` 隱藏 |
| `files` | `<input type="file" multiple>` | `accept=".mht,.mhtml"`，需有 `<label for="files">` |
| `filelist` | `<ul>` | 已選檔案清單 |
| `run` | `<button>` | 「開始處理」，預設 `disabled` |
| `progress` | `<ol>` | 八階段進度，預設以 `hidden` 隱藏 |
| `log` | `<pre>` | 即時 log 面板，預設以 `hidden` 隱藏 |
| `result` | `<div>` | 完成後的結果區，預設以 `hidden` 隱藏 |
| `open-report` | `<a>` | 開啟產出的對照表 |
| `save-report` | `<a download>` | 存成檔案 |
| `error` | `<div>` | 錯誤訊息區，預設以 `hidden` 隱藏 |

頁面文案（直接使用，不要自行改寫）：

- `<h1>`：`配球資料處理窗口`
- 副標：`在手機上處理 Short-Stop 的 MHT 快照，全程不離開這個瀏覽器。`
- 選檔區說明：`選擇 5 份 MHT 快照：基本成績、球種情報、狀況別、對戰成績、球團別配球。檔名不重要，會依內容判斷。`
- 隱私說明（必須有，放在頁尾）：`檔案只在你的手機裡處理，不會上傳到任何伺服器。`

字數上限：整個 `index.html` 不超過 6 KB（不含 CSS）。

### 3.2 `docs/style.css`

沿用 `web/report_template.html` 既有的配色變數，**數值必須一模一樣**：

```css
:root{
  --paper:#FFFFFF; --paper2:#EEF3F9; --rule:#C7D4E4;
  --ink:#0B2F62; --muted:#5B6E85; --navy:#0B2F62; --sky:#0090D4; --warn:#9B2C3B;
}
```

字型堆疊同樣沿用：`"Hiragino Kaku Gothic ProN","Noto Sans TC","Yu Gothic",system-ui,sans-serif`。

要求：行動裝置優先；主要操作按鈕的觸控目標不小於 44×44 CSS px；
`.wrap` 最大寬度 720px 置中；`[hidden]` 必須確實不顯示。
字數上限：8 KB。

### 3.3 `docs/manifest.webmanifest`

```json
{
  "name": "配球資料處理窗口",
  "short_name": "配球窗口",
  "start_url": "./",
  "scope": "./",
  "display": "standalone",
  "background_color": "#FFFFFF",
  "theme_color": "#0B2F62",
  "lang": "zh-Hant",
  "icons": []
}
```

`icons` 留空陣列。**不要自行產生圖示檔**——那需要使用者的設計判斷，列進 §7 的人工項目。

### 3.4 `docs/.nojekyll`

空檔案。理由：GitHub Pages 預設跑 Jekyll，會忽略底線開頭的檔案；這個專案的
payload 目錄未來可能出現這類檔名，先關掉比較保險。

### 3.5 `docs/README.md`

最多 400 字。必須說明：`docs/` 是 GitHub Pages 的發佈來源；
`docs/payload/` 由 `tools/build_web.py` 產生，**不要手動編輯**；
修改管線邏輯後必須重跑打包腳本，否則網站吃的還是舊的。

### 3.6 `DEPLOY.md`

給使用者本人照做的步驟文件，最多 1200 字。必須包含以下段落，且數值不得改動：

1. **前置決定**：GitHub Pages 免費方案只支援 **public 倉庫**（私有倉庫需付費的
   GitHub Pro）。公開倉庫會一併公開 `HANDOFF.md`、`DECISIONS.md` 與
   `tests/fixtures/` 裡約 11 MB 的 MHT 快照。要先確認這些都可以公開。
2. **建立倉庫並推送**：`git remote add origin`、`git push -u origin main` 的實際指令。
3. **啟用 Pages**：Settings → Pages → Source 選 `Deploy from a branch` →
   Branch 選 `main`、資料夾選 `/docs` → Save。
4. **網址**：`https://<帳號>.github.io/<倉庫名>/`，首次部署約需一兩分鐘。
5. **限制**（照抄，這些是查證過的官方數值）：站台上限 1 GB、
   每月頻寬軟上限 100 GB、每小時建置軟上限 10 次、部署逾時 10 分鐘。
   這個專案的靜態內容約數百 KB，全部遠低於上限。
6. **更新網站**：改完程式後跑 `python tools/build_web.py` 再 commit、push 即可。

### 3.7 `README.md` 的新增章節

在既有「用手機開」一節**之後**插入一節 `### 手機版（GitHub Pages）`，最多 300 字，
說明：B 計畫的靜態站放在 `docs/`，部署步驟見 `DEPLOY.md`，
與「用手機開」的差別是這個版本**不需要開電腦**。
**不得刪除或改寫既有的「用手機開」一節**——那是本機窗口的用法，兩者並存。

## 4. 預設值表（不要為這些提問）

| 問題 | 預設值 |
|---|---|
| 頁面語言 | `zh-Hant`，文案用繁體中文臺灣用法 |
| 深色模式 | 本批次不做，只做淺色；列進 DECISIONS.md 的建議後續 |
| PWA 圖示 | 不產生，`icons` 留空陣列，列進 §7 人工項目 |
| 是否引入任何 CSS 框架 | 否，手寫 CSS |
| `docs/` 以外要不要再建目錄 | 否 |
| 字數超出上限時 | 精簡內容，不得刪除必要章節或元素 id |
| 需要使用者本人判斷的內容 | 用 `[[待填：說明]]` 佔位，不自行編造 |
| 既有檔案與本計畫衝突時 | 保留既有檔案，另寫新檔並記錄在 DECISIONS.md |

## 5. 驗收清單

全部為結構性檢查，用 grep 或解析完成，不需要執行任何程式邏輯。

| # | 驗收項 | 判定方式 |
|---|---|---|
| CB01 | §2 清單中的 6 個檔案全部存在且非空 | 逐一檢查 |
| CB02 | `docs/index.html` 含 §3.1 表列的全部 13 個元素 id | 逐一 grep `id="..."` |
| CB03 | `docs/index.html` 有 viewport meta 且 `lang="zh-Hant"` | grep |
| CB04 | `docs/index.html` 以 `type="module"` 引入 `app.js` | grep |
| CB05 | `docs/style.css` 的 8 個顏色變數值與 `web/report_template.html` 完全相同 | 逐一比對字串 |
| CB06 | `docs/manifest.webmanifest` 是合法 JSON 且含 `name`/`start_url`/`display` | 解析 |
| CB07 | `index.html` ≤ 6 KB、`style.css` ≤ 8 KB、`DEPLOY.md` ≤ 1200 字 | 計算並斷言 |
| CB08 | `DEPLOY.md` 含「public」「1 GB」「100 GB」「/docs」四個關鍵字 | grep |
| CB09 | `README.md` 既有的「用手機開」一節仍存在 | grep |
| CB10 | 無 `[[待填` 殘留在應為實質內容的檔案（`index.html`、`style.css`、`DEPLOY.md`） | grep |
| CB11 | `docs/` 下沒有任何 `.py` 檔（本批次不碰程式） | find |
| CB12 | git 工作區乾淨、且 `git remote` 為空 | `git status --porcelain` 與 `git remote` 皆無輸出 |

**不得為了通過驗收而放寬標準、刪減章節、改寫元素 id、或修改驗收條件本身。**

## 6. 絕對禁止事項

- 不得向使用者提問。
- 不得建立 GitHub 倉庫、不得設遠端、不得 push。**公開發佈是使用者本人的決定。**
- 不得修改任何 `.py` 檔、不得修改 `web/report_template.html`。
- 不得刪除或覆蓋既有檔案；有衝突則將既有檔案改名保留。
- 不得執行 EXPENSIVE-PLAN-B.md 的任何內容，即使看起來很順手——
  特別是不得撰寫 `docs/app.js`、`docs/sw.js`、`tools/build_web.py`。
- 不得執行測試套件或 `verify.sh`。
- 不得從網路下載任何檔案（含 Pyodide、字型、圖示）。

## 7. 完成後的通知格式

輸出以下格式，不要輸出多餘內容：

    ✅ B 計畫便宜批次完成，請查核。

    驗收結果：CB01–CB12 全部通過（或：通過 n 項，m 項未通過，詳見 BLOCKERS.md）
    產出檔案：<n> 個
    Commit 數：<n>
    補齊次數：<n>

    需要你人工確認的部分：
    1. DEPLOY.md 的公開範圍說明是否符合你的意願（倉庫一旦 public，
       HANDOFF.md 與 tests/fixtures/ 的 MHT 都會公開）
    2. PWA 圖示尚未產生，manifest 的 icons 是空陣列
    3. 頁面文案的口吻

    自主決策列在 DECISIONS.md，共 <n> 項。

## 8. 故意不做的事

- 不寫任何 JavaScript 邏輯——那屬於 EXPENSIVE-PLAN-B.md。
- 不做深色模式、不做多語系、不做 PWA 圖示。
- 不碰 `web/server.py`：本機窗口要繼續能用，兩條路並存。
- 不自行擴充範圍；有建議寫進 DECISIONS.md 的「建議後續」段落，不要實作。
