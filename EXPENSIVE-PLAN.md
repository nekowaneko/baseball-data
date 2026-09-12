# 配球資料處理窗口 — 貴批次執行計畫

> 這份文件給協作代理人自主執行。
> 前提：CHEAP-PLAN.md 已執行完成，其產出檔案全部存在。
> 本批次含修正迴圈，會產生較高的執行成本，成本控制條款見 §0 與 §6。

## 0. 執行協定（最高優先，違反即為失敗）

### 0.1 不提問
全程不得向使用者提問，包含確認、選擇、澄清。未明訂處依 §7 預設值表處理；§7 未涵蓋時選擇最保守的做法，並將決策與理由記錄在 DECISIONS.md。不得因為缺少憑證、外部服務、或內容素材而停下來詢問。

### 0.2 工作循環

    階段實作 → 執行 ./verify.sh → 全綠？
                                  ├─ 是 → 下一階段
                                  └─ 否 → 自動修正 → 重跑

### 0.3 錯誤指紋斷路器【條款 1】
每次修正前，取失敗訊息的前三行做正規化後雜湊，得到一枚「錯誤指紋」，記錄下來。若同一枚指紋第二次出現，**立刻停止該項目**，寫入 BLOCKERS.md（含指紋、完整錯誤、已嘗試的修法、你判斷的根因），然後繼續處理其他項目。輪數上限作為第二道防線，設為 3。**不得為了讓指紋不同而改寫錯誤訊息或包裝例外。**

### 0.4 分層驗收【條款 2】
verify.sh 分三層，依序執行，前一層失敗就不進入後一層：

- **L1（秒級）**：靜態檢查、匯入檢查、grep 類的結構與架構檢查
- **L2（十秒級）**：單元測試，不含覆蓋率統計
- **L3（分鐘級）**：覆蓋率、端到端流程、完整回歸

**各階段的驗收只跑 L1 與 L2。L3 只在最後一個階段跑一次。** 不得在 verify.sh 中吞掉任何一層的失敗回傳碼。

### 0.5 成本記錄【條款 6】
每階段結束時在 PROGRESS.md 記錄：該階段的修正輪數、出現過的錯誤指紋清單、每個驗收項各失敗過幾次。全案結束時匯總成一張表，放在最終報告開頭。

### 0.6 版本控制
開工前檢查有無 .git：沒有則 git init；有則直接使用，並先把既有未提交檔案 commit 保存，不要覆蓋或刪除。全程不設遠端、不執行 push。每階段完成且驗收通過後 commit 一次，訊息用繁體中文。

### 0.7 語言與風格
所有註解、文件、commit 訊息、錯誤訊息使用繁體中文，臺灣慣用用法（品質、資料、程式，不用質量、數據、程序）。

使用者的程式風格偏好，**務必遵守，否則他讀不懂產出的程式**：

Python — 註解緊貼在該行右側或上一行，用 `#` 後直接接中文不空格；函式短、單一職責、回傳純資料：

```python
#創建向量數據庫（使用FAISS）
def create_faiss_index(embeddings):
    d = embeddings.shape[1]  #嵌入向量的維度
    index = faiss.IndexFlatL2(d)  #使用L2距離
    index.add(embeddings)  #添加向量到數據庫
    return index
```

JavaScript — 一律 `const` 箭頭函式，**不使用分號**，常數集中定義在最上方，流程用小函式串接而非大函式：

```javascript
// 常數定義
const stages = { 'S1': { name: '接收與分類檔案', fatal: false } }

// 功能函數定義
const receiveFiles = (files) => {
  console.log(`收到檔案：${files.length} 個`)
  return { files, status: 'received', timestamp: Date.now() }
}
```

包裝器模式（記錄耗時與錯誤）是使用者慣用的寫法，階段管線一律套用：

```javascript
// 包裝器：把任一站包起來，記錄耗時與錯誤，方便之後維修與追蹤
const withTrace = (stageName, fn) => async (input) => {
  const startTime = Date.now()
  try {
    const output = await fn(input)
    console.log(`[${stageName}] 成功 耗時 ${Date.now() - startTime}ms`)
    return output
  } catch (error) {
    console.log(`[${stageName}] 失敗 耗時 ${Date.now() - startTime}ms 原因 ${error.message}`)
    throw error
  }
}
```

## 1. 本批次範圍

| 動作 | 對象 |
|---|---|
| 實作 | `core/` 解析與聚合、`adapters/` 取數、`web/` 伺服器與前端 |
| 修改 | 無既有程式 |
| 新增測試 | `tests/` 全部 |
| **不動** | `config/`、`docs/`（屬於便宜批次的產出，只讀不改） |

## 2. 不可協商的架構約束

| # | 約束 | 理由 |
|---|---|---|
| A1 | `core/` 底下不得 import `requests`、`urllib`、`http`、`socket` 或任何網路相關模組 | 讓驗收能在無網路下完成，這是整份計畫的地基 |
| A2 | 取外部資料一律經 `adapters/roster.py` 的 `RosterSource` 介面，並附 `StubRosterSource` 讀 `fixtures/`；驗收全程只用 Stub | 不消耗外部請求，結果可重現 |
| A3 | 階段失敗不得拋例外中止管線，一律回傳帶 `errors` 的結果物件；僅 S8 可判定整體失敗 | 資料本來就會缺，中止等於逼使用者重跑 |
| A4 | 姓名比對查不到時回傳 `None` 並列入 `unmatched`，不得以任何方式猜測左右手 | 猜錯會汙染整份統計且無法察覺 |
| A5 | `core/` 的函式不得寫檔、不得讀環境變數，輸入輸出皆為參數與回傳值 | 純函式才能低成本測試 |

每一條都有對應的驗收項（V01–V05）檢查它本身沒被違反。

## 3. 目錄結構

```
baseball-data/
├── core/
│   ├── mht.py            #MHT 拆封與分頁分類
│   ├── parse_pitch.py    #球種 × 左右投表格解析
│   ├── parse_mix.py      #球團 × 左右 × 球數 × 球種配球解析
│   ├── parse_vs.py       #逐投手對戰成績解析
│   ├── audit.py          #S3 一致性稽核
│   ├── match.py          #姓名正規化與左右手比對
│   ├── aggregate.py      #S6 聚合與 S7 交叉驗證
│   └── render.py         #S8 產出單一 HTML
├── adapters/
│   ├── roster.py         #RosterSource 介面與 Stub 實作
│   └── roster_http.py    #真實 NPB 取數，僅此檔可連網
├── web/
│   ├── server.py         #stdlib http.server，提供上傳與 SSE 進度
│   ├── index.html        #窗口頁面
│   └── app.js            #前端：上傳、進度條、log 面板
├── tests/
|    └── fixtures/        #MHT 樣本與 NPB 名冊快照
├── cache/                #名冊快取，帶抓取日期
├── out/                  #產出的 HTML
└── verify.sh
```

## 4. 模組介面規格

簽名固定，測試依賴它們：

```python
#core/mht.py
def unpack_mht(raw_bytes)          #回傳 {content_location: html_text}
def classify_page(html_text)       #回傳 'basic'|'pitch'|'mix'|'vs'|'situational'|None

#core/parse_mix.py
def parse_team_mix(html_text)      #回傳 {球團: {'合計'|'対右投手'|'対左投手': [{count, mix}]}}

#core/parse_vs.py
def parse_vs_pitchers(html_text)   #回傳 {球團: [{name, ops, avg, ab, h, hr, so}]}

#core/audit.py
def audit_totals(vs_data, team_totals)   #回傳 [{team, field, parsed, official, diff}]

#core/match.py
def norm_name(name)                      #NFKC 正規化後去空白
def build_hand_index(roster_rows)        #回傳 (by_team, by_name) 兩層對照
def lookup_hand(by_team, by_name, team, name)   #回傳 (hand, how)，how 為 exact|fallback|unmatched

#core/aggregate.py
def aggregate_splits(vs_data, by_team, by_name)  #回傳 (stats, unmatched)
def cross_check(stats, split_totals)             #回傳 {'L': {...}, 'R': {...}} 含 match 布林

#core/render.py
def render_html(data, template_text)     #回傳完整 HTML 字串
```

`adapters/roster.py` 的介面：

```python
class RosterSource:
    def fetch_team(self, npb_code)   #回傳 [{name, hand}]

class StubRosterSource(RosterSource):
    def __init__(self, fixtures_dir)
```

## 5. 實作階段

| 階段 | 內容 | 完成條件 |
|---|---|---|
| T0 | 確認 CHEAP-PLAN.md 的產出檔案全部存在且非空 | 清單齊全 |
| T1 | `core/mht.py` + `parse_*.py` 三支 + 測試 | 解析測試全綠（L1+L2） |
| T2 | `core/audit.py`、`match.py`、`aggregate.py` + 測試 | 聚合與交叉驗證測試全綠 |
| T3 | `adapters/roster.py` 介面與 Stub + 測試 | Stub 測試全綠，A2 驗收通過 |
| T4 | `core/render.py` + 測試 | 產出的 HTML 可解析且含必要區塊 |
| T5 | `web/server.py` 與前端三檔 + 測試 | 端到端以 Stub 跑完八階段 |
| T6 | 完整驗收（含 L3）並寫 ACCEPTANCE.md | 全部驗收項通過 |

T0 若發現缺檔，**停止並寫入 BLOCKERS.md，不要自行補寫**——那些內容屬於便宜批次，用貴的方式重做是純粹的浪費。

## 6. 驗收清單

### 6.1 自動驗收項【條款 5】

| # | 層 | 驗收項 | 判定方式 |
|---|---|---|---|
| V01 | L1 | A1：`core/` 無網路模組 import | grep |
| V02 | L1 | A2：`core/` 未直接 import `roster_http` | grep |
| V03 | L1 | A5：`core/` 無 `open(`寫檔與 `os.environ` | grep |
| V04 | L1 | 全部模組可被 import，無語法錯誤 | 匯入檢查回傳 0 |
| V05 | L1 | `stages.json` 僅 S8 fatal 為 true，且 `server.py` 依此判定整體成敗 | 解析 + grep |
| V06 | L2 | `norm_name` 對全半形空白與異體字寫法輸出一致 | 單元測試 |
| V07 | L2 | `lookup_hand` 查不到時回傳 `(None, 'unmatched')`，永不回傳猜測值 | 單元測試 |
| V08 | L2 | 跨隊回退可正確解析球團標錯的三位投手 | 以 fixture 斷言 |
| V09 | L2 | `parse_mix` 切分區塊時不被按鈕 title 誤導，對右 12 列、對左列數正確 | 以 fixture 斷言 |
| V10 | L2 | `parse_mix` 取得的色塊總數與 fixture 一致（675） | 斷言 |
| V11 | L2 | **黃金值回歸：對左合計為 52 打數 8 安打** | 以 fixture 斷言 |
| V12 | L2 | `audit_totals` 能偵測出軟銀缺 16 打數、羅德缺 1 打數 | 以 fixture 斷言 |
| V13 | L2 | `aggregate_splits` 只加總打數、安打、全壘打、三振，產出中不含 OPS 欄 | 斷言鍵集合 |
| V14 | L2 | 任一階段拋例外時管線不中止，`errors` 有記錄且後續階段仍執行 | 注入錯誤測試 |
| V15 | L2 | 打數低於 10 的格子，產出資料標記 `thin: true` | 斷言 |
| V16 | L2 | `run.ndjson` 每行皆為合法 JSON 且含 `ts`/`stage`/`level` | 解析 |
| V17 | L2 | 全部測試在無網路下通過，未發出真實請求 | 攔截連線嘗試 |
| V18 | L3 | 端到端：五份 fixture MHT 跑完八階段並產出 HTML | 執行並檢查產物 |
| V19 | L3 | `core/` 測試覆蓋率 ≥ 80% | 覆蓋率工具 |

### 6.2 耦合驗收項【條款 3】

| 項目 | 與之衝突 | 衝突時的優先順序 |
|---|---|---|
| V14 放寬錯誤處理，讓階段失敗不中止管線 | V05 要求 S8 失敗時整體必須判定為失敗 | **V05 優先**：只能對 S1–S7 加例外，不得讓 S8 也變成可降級 |
| V08 跨隊回退，放寬球團比對條件 | V07 查不到時不得猜測 | **V07 優先**：回退僅限「姓名在其他球團名冊中精確命中」，模糊比對一律視為未命中 |
| V15 薄樣本標記 thin 以隱藏打率 | V11 黃金值回歸需要完整加總 | **V11 優先**：thin 只影響顯示層，不得影響 `aggregate_splits` 的加總結果 |

### 6.3 移出自動層的項目【條款 4】

| 項目 | 為何無法自動判定 | 改為 |
|---|---|---|
| 產出網頁的視覺品質、配色可辨識度 | 需要人眼判斷 | 產出 `out/preview-report.md`，由使用者過目 |
| 真實 NPB 名冊的取數是否成功 | 依賴外部服務即時回應 | 手動執行 `adapters/roster_http.py` 後檢視 `cache/` |
| 進度條動畫的流暢度 | 依賴時間與並行順序 | 列入 CHECKLIST.md |

自動層對這些項目唯一允許的檢查是「報告檔有被產生出來」。

### 6.4 人工檢查清單
其餘檢查沿用便宜批次產出的 `CHECKLIST.md`，由使用者在交付後自己掃一遍。

## 7. 預設值表（不要為這些提問）

| 問題 | 預設值 |
|---|---|
| Python 版本 | 3.9 以上。使用者慣用的 `c:\Python36\python.exe` 不適用於本專案，因為需要 f-string 巢狀與 `dict` 保序行為；此決策寫入 DECISIONS.md |
| Web 框架 | 不用框架，使用標準庫 `http.server`，避免相依 |
| HTML 解析 | `beautifulsoup4` + `lxml`，與既有腳本一致 |
| 進度回報機制 | Server-Sent Events，單向即可，不用 WebSocket |
| 日誌格式 | NDJSON，每行一事件，寫入 `out/run.ndjson` |
| 前端框架 | 無，原生 JS，符合使用者風格偏好 |
| 打率顯示門檻 | 10 打數 |
| 名冊快取有效期 | 7 天，過期重抓；驗收永遠用 Stub 不受此影響 |
| 測試框架 | `pytest` |
| 覆蓋率門檻 | `core/` 80%，其餘不設門檻 |
| 某套件在此環境安裝失敗時 | 改用標準庫替代方案並記錄在 DECISIONS.md，不得降低安全性 |
| 兩種實作都合理時 | 選較保守、較容易測試的那個 |
| fixture 不足時 | 用既有產出的 `vs_pitchers.json` 等 JSON 當替代 fixture，不得自行捏造數字 |

## 8. 絕對禁止事項

- 不得向使用者提問。
- 不得連線真實外部服務、不得呼叫真實 API（驗收全程只用 Stub）。
- **不得猜測任何投手的左右手**，查不到就列入 unmatched。
- 不得為了讓交叉驗證通過而調整加總邏輯或黃金值。
- 不得建立含真實憑證的檔案，只建範例檔。
- 不得設遠端、不得 push。
- 不得刪除或覆蓋既有檔案；有衝突則將既有檔案改名保留。
- 不得安裝與本計畫無關的套件。
- 不得修改 `config/` 與 `docs/`（便宜批次的產出）。
- 不得執行 CHEAP-PLAN.md 的內容。

## 9. 完成後的通知格式

    ✅ 貴批次完成，請查核。

    驗收結果：V01–V19 全部通過（或：通過 n 項，m 項未通過，詳見 BLOCKERS.md）

    成本摘要：
    | 階段 | 修正輪數 | 觸發過的錯誤指紋 |
    |---|---|---|
    | T1 | <n> | <n> 種 |
    合計修正輪數：<n>

    Commit 數：<n>
    測試數：<n> 個，core/ 覆蓋率 <n>%

    需要你人工完成的事：
    1. 執行 adapters/roster_http.py 抓真實名冊並檢視 cache/
    2. 看 out/preview-report.md
    3. 掃 CHECKLIST.md

    自主決策列在 DECISIONS.md，共 <n> 項。

## 10. 故意不做的事

- 不做使用者帳號、權限、多人協作。
- 不做資料庫，全部以檔案為中介。
- 不做自動抓取 Short-Stop 頁面——那需要真人在瀏覽器存 MHT，見 HANDOFF.md §2 S1。
- 不做除了本打者以外的通用化，先讓單一案例跑通。
- 不擴充範圍；有建議寫進 DECISIONS.md 的「建議後續」段落，不要實作。
