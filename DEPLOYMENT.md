# 正式部署與管理

## 建議：同一網址提供 PWA 與 AI

1. 開啟 [Render 一鍵部署](https://render.com/deploy?repo=https://github.com/foxicall/Physiotherapy_consultation)，登入自己的 Render 帳號並連接本 GitHub 專案。
2. 在 Render 的秘密環境變數輸入 `GEMINI_API_KEY`。使用可存取 `gemini-3.8-flash` 的金鑰，不需要更換為其他模型。
3. Blueprint 會自動產生 `CLINIC_ACCESS_CODE`。部署後由管理員在 Render 環境設定取得此使用碼，僅提供給授權診所人員。
4. 等待服務部署成功，使用 Render 實際回傳的 HTTPS 網址。此網址可直接安裝 PWA，無須再設定前後端連線。
5. 開啟話術工作台，輸入診所使用碼後，以無個資的範例生成一次確認。已設定金鑰不保證模型權限或配額正常；`/api/health` 僅回報服務設定狀態。

`render.yaml` 預設免費方案；平台可能有休眠、冷啟動及使用限制，實際條件以平台為準。需要持續在線時由帳號管理員自行選擇適合方案。此程式沒有自動開通付費資源。

雲端開發環境的金鑰不會自動移轉到 Render。請在正式平台的秘密設定中完成配置，不要將金鑰貼進 GitHub、前端設定或公開檔案。

## 選用：GitHub Pages 安裝入口

Render 網址已提供完整 PWA，不必另開 Pages。若需要獨立的靜態入口，由儲存庫管理員至 [Settings → Pages](https://github.com/foxicall/Physiotherapy_consultation/settings/pages)，選擇 **Deploy from a branch → main → /docs → Save**。GitHub 整合可能沒有 Pages 管理權限，必須由管理員完成此設定。

等待 Pages 部署成功後，才可使用 `https://foxicall.github.io/Physiotherapy_consultation/`。此入口提供 PWA 介面、50 套症候群、收藏及離線價目，但不能執行 Python。

正式 AI 服務部署後，可採以下任一方式：

- **個別裝置連線**：在話術工作台展開「診所服務連線設定」，填入完整 HTTPS 服務網址。
- **全診所預設網址**：更新 `docs/config.json` 的 `apiBaseUrl` 為服務 HTTPS 網址，執行 `python scripts/build_pwa.py`，提交並推送。

後端 `ALLOWED_ORIGINS` 填入前端的精確 origin，例如 `https://foxicall.github.io`，不是含專案路徑的完整網址；多個 origin 使用逗號分隔。使用同源部署時可留空，不需 CORS。

## 自行部署容器

```bash
cp .env.example .env
# 以安全方式填入 GEMINI_API_KEY、CLINIC_ACCESS_CODE
# 產生使用碼可使用 python -c 'import secrets; print(secrets.token_urlsafe(32))'
docker compose up --build -d
```

Compose 僅綁定 `127.0.0.1:8000`。在對外的 HTTPS 反向代理後提供服務，設定足以涵蓋 60 秒模型請求的代理逾時，例如 90 秒。不要直接以 HTTP 公開傳送使用碼或對話。

容器使用非 root 使用者、唯讀檔案系統，預設一個 worker。不要掛載原始 Git 儲存庫、`.env` 或整個工作目錄到靜態資產資料夾。

## 授權與資料

- 伺服器僅在 `GEMINI_API_KEY` 與 `CLINIC_ACCESS_CODE` 都存在時啟用生成。
- 使用碼換取最長 12 小時的簽名授權；手機僅在記憶體中持有，重新整理後需重新輸入。旋轉使用碼也會讓既有授權失效。
- 服務不儲存主訴或結果；前端不將這些資料或使用碼放進離線快取。請勿另開記錄請求內容的代理日誌。
- 登入每來源每分鐘最多 5 次，生成每次授權每分鐘最多 8 次，單程序同時最多 2 次生成。
- 限流狀態僅在程序記憶體內，重啟會清除。多副本／多 worker 部署前應改用共享限流服務，不能把目前限制視為跨主機限制。
- 瀏覽器只收到公開知識庫、價目與本次生成結果；伺服器 Gemini 金鑰永不傳回前端。價格由共用常數輸出。

## 更新與復原

1. 更新來源後執行 `python scripts/build_pwa.py`。
2. 執行 README 所列測試，確認 `catalog.json` 與 `sw.js` 一併提交。
3. GitHub Pages 隨 `main` 更新；Render Blueprint 設定於檢查通過後自動部署。
4. 已安裝 PWA 會下載新版並顯示更新按鈕；使用者應先匯出本次結果再更新。
5. 回退時重新部署上一個已驗證 commit，不刪除使用者的來源知識庫。

## API

| 端點 | 用途 |
| --- | --- |
| `GET /api/health` | 服務、版本、模型、50 套數量與設定就緒狀態 |
| `GET /api/catalog` | 公開症候群、院所資料、價格與選單 |
| `POST /api/session` | 使用 `{"code":"診所使用碼"}` 取得短期 token |
| `POST /api/generate` | Bearer 授權；傳入症候群編號、主訴、目標、考量及對象 |

API 回應使用 `Cache-Control: no-store`。錯誤訊息不包含上游原始錯誤、金鑰或患者輸入。
