# TWPS 改筆百科

臺灣轉筆論壇改筆百科的網站。內容在 HackMD 團隊 [TWPSmodification](https://hackmd.io/team/TWPSmodification) 編輯，這個 repo 每天自動抓下來產生網站。

## 運作方式

1. 在 HackMD 寫教學（格式見 [SPEC.md](SPEC.md)，範本見 [TEMPLATE.md](TEMPLATE.md)），並把連結加進「總目錄」對應的分類底下。
2. GitHub Actions 每天台灣時間 03:00 執行 `scripts/fetch.py` 抓筆記、`scripts/build.py` 產生網站到 `dist/`，有變動就自動 commit。
3. Cloudflare Pages 看到新的 commit 就重新發布 `dist/`。

想馬上更新：到 GitHub 的 **Actions → Sync from HackMD → Run workflow**。

## 檔案

| 路徑 | 用途 |
|---|---|
| `site/template.html` | 網站版面（樣式與互動都在這一個檔案） |
| `site/assets/default.jpg` | 沒有封面時使用的預設圖（放上去就會自動套用） |
| `scripts/fetch.py` | 從 HackMD 下載筆記與建立時間 |
| `scripts/parse_notes.py` | 把筆記解析成資料 |
| `scripts/build.py` | 產生 `dist/`；加 `--preview` 產生單檔預覽 |
| `scripts/normalize.py` | 把舊格式筆記轉成 SPEC.md 規格 |
| `content/` | 自動抓下來的筆記（不要手動改） |
| `dist/` | 產生出來的網站（不要手動改） |

## 本機預覽

```bash
python -I scripts/fetch.py
python -I scripts/build.py
python -m http.server 8000 -d dist
```

## 設定

GitHub repo 的 **Settings → Secrets and variables → Actions** 需要一個 `HACKMD_TOKEN`（HackMD 設定頁的 API token）。沒有也能運作，只是「最近更新」會改用目錄順序。

## 網站

- 名稱：紡 TSUMUGI（非官方整理，部分內容整理自 TWPS 改筆百科 HackMD 團隊筆記）
- 網址：https://tsumugi-works.pages.dev（Cloudflare Pages 專案 `tsumugi-works`，輸出 `dist/`）
- 舊網址 twps-modding-wiki.pages.dev：Cloudflare 專案改為輸出 `legacy/`，整站 301 轉到新網址
- 網址路徑：`/mods/`、`/mods/dual|g3|vp-mx/`、`/mods/<代稱>/`、`/materials/`、`/tips/`、`/search/?q=`、`/wish/`；代稱記在 `content/slugs.json`，中文標題的代稱在 `site/slugs.json` 指定
