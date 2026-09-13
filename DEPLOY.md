# 部署到 GitHub Pages

這份文件給使用者本人照做，把 `docs/` 發佈成手機可直接開啟的網址。全程不由代理人自動執行。

## 1. 前置決定：先確認可以公開

GitHub Pages 的免費方案只支援 **public 倉庫**（私有倉庫要跑 Pages 需要付費的 GitHub Pro）。
一旦把整個倉庫設成 public，以下內容會一併公開：

- `HANDOFF.md`、`DECISIONS.md`
- `tests/fixtures/` 裡約 10 MB 的 MHT 快照原始檔

請先確認這些都可以公開，再進行下一步。若不行，這個方案就不適用，
維持 `python -m web.server --host 0.0.0.0` 的區網用法即可。

## 2. 建立倉庫並推送

在 GitHub 網站建立一個新的 **public** 倉庫（不要勾選自動產生 README，本地已經有內容），
接著在專案目錄執行：

```bash
git remote add origin https://github.com/<帳號>/<倉庫名>.git
git push -u origin main
```

`<帳號>` 與 `<倉庫名>` 換成實際值。

## 3. 啟用 Pages

到倉庫的 **Settings → Pages**：

- Source 選 `Deploy from a branch`
- Branch 選 `main`，資料夾選 `/docs`
- 按 **Save**

## 4. 網址

儲存後 GitHub 會顯示發佈網址，格式是：

```
https://<帳號>.github.io/<倉庫名>/
```

首次部署通常需要一兩分鐘才會生效，之後每次 push 到 `main` 都會自動重新部署。

## 5. 限制（GitHub 官方數值）

- 站台總容量上限 **1 GB**
- 每月頻寬軟上限 **100 GB**
- 每小時建置軟上限 **10 次**
- 單次部署逾時 **10 分鐘**

這個專案的靜態內容只有數百 KB，遠低於以上所有上限，正常使用不會踩到。

## 6. 之後要更新網站

改完程式邏輯後，先在本機重新打包，再照常 commit、push：

```bash
python tools/build_web.py
git add docs
git commit -m "更新網站內容"
git push
```

push 完後等一兩分鐘，GitHub Pages 會自動套用新版本。
