# `docs/` 說明

本目錄是 GitHub Pages 發佈來源（Source 設為 `main` 分支的 `/docs`），對外即手機版配球資料處理窗口。

- `index.html`、`style.css`、`manifest.webmanifest`、`app.js`、`sw.js`、`.nojekyll` 為網站本體。
- `payload/` 由 `tools/build_web.py` 產生，**不要手動編輯**；改動管線邏輯後須重跑該腳本，否則網站吃到舊資料。
- `DATA-SCHEMA.md`、`KNOWN-GAPS.md` 是專案技術文件，不是網站內容，只是恰好同放此目錄，
  會被 GitHub Pages 一併當靜態檔服務，屬預期行為。

部署步驟見 [../DEPLOY.md](../DEPLOY.md)。
