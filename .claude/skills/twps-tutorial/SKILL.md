---
name: twps-tutorial
description: 整理一篇改筆教學並上架到 TWPS 改筆百科。使用者貼 FB 貼文連結、教學文字或照片，說「整理這篇」「幫我上 HackMD」「上傳到網站」時使用。先在 HackMD 建草稿給使用者確認，確認後才加進總目錄並同步到網站。
---

# TWPS 改筆教學整理

完整流程與規則在 `docs/教學整理流程.md`，格式規格在 `SPEC.md`。開始前先讀這兩份。

## 兩個階段，中間一定要等使用者確認

**階段一：整理並建立 HackMD 草稿**
1. 收集內容（FB 連結用使用者的 Chrome 讀；或使用者直接貼的文字與照片）。
2. 依 `docs/教學整理流程.md` 的對應表整理，步驟依作者編號排序。
3. 照片上傳到 HackMD 圖床，不外連。
4. 「作者的話」直接複製作者原文，不改寫、不改人稱、不修標點。
5. 依 SPEC.md 排版：cm／g、不寫「約」、數量用數字、全形標點、`#### 步驟一　小標`、每步先說明後照片。
6. 在 HackMD 團隊 TWPSmodification 建新筆記，並在「筆記設定」設定標題。
7. **不要加進總目錄。** 把筆記連結給使用者，列出你做的判斷（例如重排了哪些步驟、哪些留言沒收），然後停下來等確認。

**階段二：使用者說「上傳」後才做**
1. 在總目錄（`SlgLCaoxRb6avBEJNptVlQ`）對應分類最後加 `[筆名](/筆記ID)`，更新「最後更新日期」。
2. 到 GitHub annvi23/twps-modding-wiki 的 Actions → Sync from HackMD → Run workflow。
3. 等部署完成後打開 https://twps-modding-wiki.pages.dev 確認新教學出現在「最近更新」。

## 注意
- 使用者說過瀏覽器操作不必逐一確認，但上架（加進總目錄）一定要等他說「上傳」。
- HackMD API token、密碼等密鑰不能由 Claude 填進網頁欄位。
- 只建立在 TWPSmodification 團隊，不要建在個人空間。
