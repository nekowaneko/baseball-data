# 配球資料處理窗口

把手機存下的 Short-Stop MHT 快照，整理成球團 × 左右投配球與打擊成績可交叉閱讀的互動網頁。詳細背景與踩坑記錄見 [HANDOFF.md](HANDOFF.md)。

## 專案用途

日職打者的配球與打擊資料分散在 Short-Stop 的多個分頁，彼此無法直接對照。本專案接收使用者手動存下的 MHT 快照，自動解析、稽核、比對投手左右手、聚合統計，最終產出單一離線可開的 HTML 成品。

## 啟動方式

程式邏輯（`core/`、`adapters/`、`web/`）已由 [EXPENSIVE-PLAN.md](EXPENSIVE-PLAN.md) 批次實作完成，驗收結果見 [ACCEPTANCE.md](ACCEPTANCE.md)。

```bash
python -m web.server            # 啟動本機窗口，預設埠見 config/settings.example.json
python -m web.server --host 0.0.0.0   # 同時開放同一 Wi-Fi 的手機連入（見下方「用手機開」）
./verify.sh                     # 分層驗收：只跑 L1 靜態檢查與 L2 單元測試
./verify.sh all                 # 三層全跑，含端到端與 core/ 覆蓋率門檻
python tools/run_fixtures.py    # 不開瀏覽器，直接以測試樣本跑完整條管線
python adapters/roster_http.py  # 手動抓取真實 NPB 名冊到 cache/（唯一會連網的程式）
```

啟動後於瀏覽器開啟窗口頁面，上傳 5 份 MHT，即可看到進度條與 log 面板，完成後於 `out/` 取得成品 HTML。

### 用手機開

MHT 快照本來就存在手機上，直接用手機上傳最省事：

1. 手機與電腦連同一個 Wi-Fi（不要用手機自己的行動網路）。
2. 電腦上執行 `python -m web.server --host 0.0.0.0`，終端機會印出手機要開的網址。
3. 第一次啟動時 Windows 若跳出防火牆詢問，選「允許」；若沒跳出而手機連不上，以管理員身分執行：
   `netsh advfirewall firewall add rule name="配球窗口 8787" dir=in action=allow protocol=TCP localport=8787 profile=private`
4. 手機瀏覽器開終端機印出的 `http://<電腦IP>:8787`。

注意事項：

- 這是 HTTP 明文、且沒有任何身分驗證，只適合家裡或個人熱點這種可信網路；用完就把伺服器關掉。
- 電腦的區域網路 IP 可能在重開機或換網路後改變，每次以終端機印出的為準。
- 只想在手機上「看成品」而不重跑流程：`out/report.html` 是單檔離線 HTML，用任何方式傳到手機（雲端硬碟、通訊軟體）開起來就能看，不必啟動伺服器。

## 資料流概述

```
MHT 上傳 → 拆封分類(S1) → 解析各分頁(S2) → 一致性稽核(S3)
→ 取得投手左右手(S4) → 姓名比對(S5) → 聚合統計(S6)
→ 交叉驗證(S7) → 產出 HTML(S8)
```

階段定義見 [config/stages.json](config/stages.json)；中介檔案格式見 [docs/DATA-SCHEMA.md](docs/DATA-SCHEMA.md)；已知資料缺口見 [docs/KNOWN-GAPS.md](docs/KNOWN-GAPS.md)。除 S8 外，任何階段失敗只降級記錄、不中止流程。
