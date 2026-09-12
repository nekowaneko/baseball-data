# 驗收結果

執行日期：2026-09-12　執行環境：Windows 10、Python 3.10.10（`C:\Python36\python.exe`，目錄名沿用舊版但實際版本為 3.10）

重跑方式：

```bash
./verify.sh all
```

最後一次完整執行：**L1、L2、L3 全數通過**，測試 84 個（L2 79、L3 5），`core/` 覆蓋率 **96.55%**。

## 自動驗收項（EXPENSIVE-PLAN.md §6.1）

| # | 層 | 驗收項 | 結果 | 證據 |
|---|---|---|---|---|
| V01 | L1 | `core/` 無網路模組 import | 通過 | `verify.sh` grep 反向檢查 |
| V02 | L1 | `core/` 未直接 import `roster_http` | 通過 | `verify.sh` grep 反向檢查 |
| V03 | L1 | `core/` 無 `open(` 寫檔與 `os.environ` | 通過 | `verify.sh` grep 反向檢查 |
| V04 | L1 | 全部模組可被 import，無語法錯誤 | 通過 | `tools/check_imports.py`、`tools/check_complete.py` |
| V05 | L1 | 僅 S8 fatal，且 `server.py` 依此判定整體成敗 | 通過 | `tools/check_stages.py`、`tests/test_pipeline.py::test_fatal_stage_fails_whole_run` |
| V06 | L2 | `norm_name` 對全半形空白與寫法差異輸出一致 | 通過 | `tests/test_match.py::test_norm_name_same_key` |
| V07 | L2 | `lookup_hand` 查不到回傳 `(None, 'unmatched')` | 通過 | `tests/test_match.py::test_lookup_unmatched` |
| V08 | L2 | 跨隊回退正確解析球團標錯的三位投手 | 通過 | `tests/test_aggregate.py::test_cross_team_fallback`（阪神 2、DeNA 1） |
| V09 | L2 | `parse_mix` 不被按鈕 title 誤導，對右／對左各 12 列 | 通過 | `tests/test_parse_mix.py::test_section_rows` |
| V10 | L2 | 色塊總數與 fixture 一致（675） | 通過 | `tests/test_parse_mix.py::test_total_blocks` |
| V11 | L2 | 黃金值回歸：對左合計 52 打數 8 安打 | 通過 | `tests/test_aggregate.py::test_golden_left_total` |
| V12 | L2 | `audit_totals` 偵測軟銀缺 16 打數、羅德缺 1 打數 | 通過 | `tests/test_audit.py::test_detects_known_gaps` |
| V13 | L2 | 只加總四個欄位，產出不含 OPS | 通過 | `tests/test_aggregate.py::test_only_summable_fields` |
| V14 | L2 | 階段拋例外時管線不中止，`errors` 有記錄且後續階段仍執行 | 通過 | `tests/test_pipeline.py::test_stage_failure_does_not_abort` |
| V15 | L2 | 打數低於 10 的格子標記 `thin: true` | 通過 | `tests/test_render.py::test_mark_thin` |
| V16 | L2 | `run.ndjson` 每行皆為合法 JSON 且含 `ts`/`stage`/`level` | 通過 | `tests/test_pipeline.py::test_ndjson_format` |
| V17 | L2 | 全部測試在無網路下通過，未發出真實請求 | 通過 | `tests/conftest.py` 的 `block_network`（autouse，攔截 `socket.connect`） |
| V18 | L3 | 端到端：五份 fixture MHT 跑完八階段並產出 HTML | 通過 | `tests/test_e2e.py`（`out/report.html`，42KB） |
| V19 | L3 | `core/` 測試覆蓋率 ≥ 80% | 通過 | 96.55% |

## 耦合驗收項（§6.2）

| 衝突 | 採用的優先順序 | 落實方式 |
|---|---|---|
| V14 放寬錯誤處理 vs V05 S8 失敗即整體失敗 | **V05 優先** | `run_pipeline` 只對非 fatal 階段降級；S8 失敗時 `ok=False`（`test_fatal_stage_fails_whole_run`） |
| V08 跨隊回退 vs V07 不得猜測 | **V07 優先** | 回退僅限「姓名 NFKC 正規化後精確命中」，無任何模糊比對（`test_lookup_unmatched` 涵蓋部分相符與順序不同） |
| V15 薄樣本標記 vs V11 黃金值完整加總 | **V11 優先** | `thin` 標記只在 `core/render.py` 的顯示層產生，`aggregate_splits` 的加總不受影響（`test_mark_thin_keeps_totals`） |

## 移出自動層的項目（§6.3）

| 項目 | 處理方式 | 狀態 |
|---|---|---|
| 產出網頁的視覺品質與配色 | `out/preview-report.md` | 已產生，待使用者過目 |
| 真實 NPB 名冊取數是否成功 | 手動執行 `python adapters/roster_http.py` 後檢視 `cache/` | 待使用者執行（驗收全程只用 Stub） |
| 進度條動畫流暢度 | 列入 `CHECKLIST.md` | 待使用者確認 |

## 這次執行的實際數據

- 八階段全部成功，整體判定成功。
- 交叉驗證：對左 52 打數 8 安打，與原站**完全相符**；對右 141/38 對官方 157/41，差額 16 打數 3 安打，與 S3 稽核抓到的軟銀缺口一致，兩個異常互相印證。
- 一致性稽核差異 7 筆：軟銀（打數 16、安打 3、全壘打 1）、羅德（打數 1）、以及官方球團表未列資料的 DeNA 與阪神（合計 4 筆）。
- 左右手未命中 4 人：DeNA 東 克樹、DeNA 中川 颯、養樂多 小川 泰弘、養樂多 星 知弥；全部留空不猜。
