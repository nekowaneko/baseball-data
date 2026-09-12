# 配球資料處理窗口

把手機存下的 Short-Stop MHT 快照，整理成球團 × 左右投配球與打擊成績可交叉閱讀的互動網頁。詳細背景與踩坑記錄見 [HANDOFF.md](HANDOFF.md)。

## 專案用途

日職打者的配球與打擊資料分散在 Short-Stop 的多個分頁，彼此無法直接對照。本專案接收使用者手動存下的 MHT 快照，自動解析、稽核、比對投手左右手、聚合統計，最終產出單一離線可開的 HTML 成品。

## 啟動方式

程式邏輯（`core/`、`adapters/`、`web/`）由 [EXPENSIVE-PLAN.md](EXPENSIVE-PLAN.md) 批次實作，目前僅有目錄骨架。實作完成後：

```bash
python -m web.server   # 啟動本機窗口，預設埠見 config/settings.example.json
./verify.sh            # 執行分層驗收（L1 靜態檢查／L2 單元測試／L3 端到端）
```

啟動後於瀏覽器開啟窗口頁面，上傳 5 份 MHT，即可看到進度條與 log 面板，完成後於 `out/` 取得成品 HTML。

## 資料流概述

```
MHT 上傳 → 拆封分類(S1) → 解析各分頁(S2) → 一致性稽核(S3)
→ 取得投手左右手(S4) → 姓名比對(S5) → 聚合統計(S6)
→ 交叉驗證(S7) → 產出 HTML(S8)
```

階段定義見 [config/stages.json](config/stages.json)；中介檔案格式見 [docs/DATA-SCHEMA.md](docs/DATA-SCHEMA.md)；已知資料缺口見 [docs/KNOWN-GAPS.md](docs/KNOWN-GAPS.md)。除 S8 外，任何階段失敗只降級記錄、不中止流程。
