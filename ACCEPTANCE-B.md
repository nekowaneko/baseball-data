# B 計畫驗收結果

## 成本摘要

| 階段 | 修正輪數 | 觸發過的錯誤指紋 |
|---|---|---|
| T0 前置檢查 | 0 | 0 種 |
| T1 抽出 web/pipeline.py | 0 | 0 種 |
| T2 解析器換成 html.parser | 0 | 0 種 |
| T3 名冊快取來源 | 0 | 0 種 |
| T4 打包腳本 | 0 | 0 種 |
| T5 前端與 service worker | 1 | 1 種（`a9987f88`） |
| T6 完整驗收 | 0 | 0 種 |
| **合計** | **1** | **1 種** |

沒有任何一枚錯誤指紋重複出現，斷路器未觸發，BLOCKERS.md 未產生。各階段明細見 PROGRESS.md。

---

執行日期：2026-09-13　執行環境：Windows 10、Python 3.10.10、Git Bash

重跑方式：

```bash
./verify.sh all
```

最後一次完整執行（T6，只跑這一次）：**L1、L2、L3 全數通過**。
L1 九項檢查；測試 118 個（L2 112、L3 6），其中既有 99 個全數通過、本批次新增 19 個；`core/` 覆蓋率 **96.68%**。
`docs/payload/pipeline.zip`：37,793 bytes（約 37 KB），32 個檔案。

## 自動驗收項（EXPENSIVE-PLAN-B.md §6.1）

| # | 層 | 驗收項 | 結果 | 證據 |
|---|---|---|---|---|
| V-B01 | L1 | A1：`core/` 無網路模組 import | 通過 | `verify.sh` 既有 V01 |
| V-B02 | L1 | A2：`core/` 無 `open(`、`os.environ` | 通過 | `verify.sh` 既有 V03 |
| V-B03 | L1 | A3：`web/pipeline.py` 未 import `http.server`/`socket`/`socketserver`/`threading` | 通過 | `verify.sh` V-B03（grep 反向，已確認對 `server.py` 會命中） |
| V-B04 | L1 | A4：全專案 `.py` 無 `'lxml'` | 通過 | `verify.sh` V-B04（單雙引號皆抓，已確認對改動前的程式會命中） |
| V-B05 | L1 | A5：`docs/*.js`、`docs/*.html` 無 `localhost`、`127.0.0.1`、白名單外網域 | 通過 | `verify.sh` V-B05（另以違規樣本反向測試） |
| V-B06 | L2 | A6：zip 不含 `tests/`、`out/`、`uploads/`、`.pyc`、`roster_http.py` | 通過 | `tests/test_build_web.py::test_excludes`、`test_excluded_rule` |
| V-B07 | L1 | 全模組可匯入，涵蓋新模組 | 通過 | `tools/check_imports.py` 追加 `web.pipeline`、`adapters.roster_cache`、`tools.build_web` |
| V-B08 | L2 | `web.pipeline` 不經 `web.server` 獨立匯入並跑完管線 | 通過 | `tests/test_pipeline_module.py::test_pipeline_runs_without_server`（子行程，確認 `web.server`、`http.server` 皆未載入） |
| V-B09 | L2 | `server.run_pipeline`、`server.load_config`、`server.RunLog` 仍可用 | 通過 | `tests/test_pipeline_module.py::test_server_reexports`；另以隨機埠啟動本機窗口，`/` 與 `/api/stages` 正常回應 |
| V-B10 | L2 | `CachedRosterSource` 讀得到 12 隊、格式含 `players` | 通過 | `tests/test_roster_cache.py::test_reads_all_twelve_teams` |
| V-B11 | L2 | 缺某隊快取時回空清單不拋例外 | 通過 | `tests/test_roster_cache.py::test_missing_team_returns_empty` |
| V-B12 | L2 | zip 含 `core/render.py`、`web/pipeline.py`、`config/pitch_meta.json`、`cache/rst_e.json`、`web/report_template.html` | 通過 | `tests/test_build_web.py::test_required_members` |
| V-B13 | L2 | zip 小於 1 MB | 通過 | `tests/test_build_web.py::test_size_under_one_mb`（37,793 bytes） |
| V-B14 | L2 | `docs/app.js` 鎖定的 Pyodide 版本與 §7 一致 | 通過 | `tests/test_build_web.py::test_pyodide_version_pinned`（`v314.0.6`、jsDelivr、不用 micropip） |
| V-B15 | L2 | `docs/index.html` 的元素 id 全部被 `app.js` 引用 | 通過 | `tests/test_build_web.py::test_index_ids_used_by_app`（12 個，見 DECISIONS.md 決策 3） |
| V-B16 | L2 | 全部測試在無網路下通過 | 通過 | `tests/conftest.py` 的 `block_network`（autouse）；兩個子行程測試只用 Stub 與本機快取，不連網 |
| V-B17 | L3 | 既有測試全數通過，無退化 | 通過 | 既有 99 個全過（計畫寫 97，見 DECISIONS.md 決策 2） |
| V-B18 | L3 | 黃金值回歸：對左合計 52 打數 8 安打 | 通過 | `tests/test_aggregate.py::test_golden_left_total`、`tests/test_pipeline.py::test_golden_values`、`tests/test_e2e.py` |
| V-B19 | L3 | `core/` 覆蓋率 ≥ 80% | 通過 | 96.68% |

本批次額外加的自動檢查（不在 §6.1，但與交付品質直接相關）：

| 檢查 | 證據 |
|---|---|
| 網站上的 zip 與目前程式一致，改了管線忘了重新打包會失敗 | `tests/test_build_web.py::test_published_payload_is_current` |
| zip 解到空目錄後只靠 zip 內容跑完八階段（模擬 Pyodide） | `tests/test_build_web.py::test_unpacked_payload_runs_pipeline` |
| 重新打包的位元組可重現 | `tests/test_build_web.py::test_deterministic` |
| app.js 接到 `web.pipeline`、`CachedRosterSource`、`/out/report.html`，且沒有任何 POST 上傳 | `tests/test_build_web.py::test_app_wires_pipeline` |
| sw.js 快取五個網站檔、快取名稱含版本、清舊版、不碰 CDN | `tests/test_build_web.py::test_service_worker` |
| 快照很舊也照讀（不檢查 TTL） | `tests/test_roster_cache.py::test_ignores_ttl` |
| `pipeline.py` 不反向引用 `server` | `tests/test_pipeline_module.py::test_pipeline_does_not_import_server` |

## 耦合驗收項（§6.2）

| 衝突 | 採用的優先順序 | 落實方式 |
|---|---|---|
| V-B03 vs 本機窗口仍須能啟動 | 兩者並存，`server.py` → `pipeline.py` 單向 | `server.py` 從 `web.pipeline` 重新匯出；反向引用有測試擋；本機窗口啟動冒煙通過 |
| V-B04 vs V-B18 黃金值與既有斷言 | V-B18 優先 | 換成 `html.parser` 後既有斷言零修改即通過；`out/report.html` 與改動前逐字相同（只差時間戳），未觸發 lxml 退路 |
| A6 排除 `roster_http.py` vs 本機仍須能執行 | 兩者並存 | 只從 zip 排除；檔案保留，僅依 A4 換了解析器字串（DECISIONS.md 決策 7），`test_roster_http.py` 照過 |
| V-B05 不得有外部網域 vs Pyodide 走 CDN | 白名單只允許 `cdn.jsdelivr.net` | V-B05 grep 以協定網址與裸網域兩種方式比對白名單 |
| V-B13 zip < 1 MB vs 完整打包 | 完整性優先 | 12 隊名冊與程式全數打包，僅 37 KB |

## 移出自動層的項目（§6.3）

以下無法自動判定，改由使用者依 `CHECKLIST-B.md` 實機驗證；自動層只確認 `out/preview-web.md` 已產生。

- Pyodide 在真實手機瀏覽器能否啟動、耗時多久
- 上傳 5 份 MHT 後的實際產出是否正確
- 離線（飛航模式）二次開啟能否運作
- 版面在各尺寸手機的觀感

`out/preview-web.md` 已產生。注意它不是在真實瀏覽器跑的：驗收不得連外部服務，無法載入 Pyodide，
因此以 CPython 執行 app.js 內嵌的同一段 Python 膠水程式代替（DECISIONS.md 決策 17）。

## 請你特別留意

1. **手機版的 S7 對左結果與本機窗口不同**：12 隊真實名冊下為 54 打數 9 安打（不符官方 52/8），
   來源是 DeNA 左投「東 克樹」2 打數在 Stub 名冊下未命中、在快取名冊下被計入。詳見 `out/preview-web.md`。
2. **處理期間畫面不會即時更新**：管線在主執行緒同步執行，log 與進度在跑完後一次出現（DECISIONS.md 決策 12）。
3. **更新網站要做兩件事**：重跑 `python tools/build_web.py`，並把 `docs/sw.js` 的 `VERSION` 加一。
4. **乾淨 clone 需要先有 `cache/`**：`cache/*` 在 .gitignore，V-B10 與 V-B12 依賴本機快取（DECISIONS.md 決策 9）。
