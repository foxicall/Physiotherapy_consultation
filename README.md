# 生生優動板橋｜診間溝通工作台

可安裝於 iPhone、Android 與電腦的 PWA，整合 50 套物理治療症候群、台灣診間話術與診所自費價目。正式行動版採用 FastAPI + 原生 HTML/CSS/JavaScript；原有 Streamlit 介面保留，共用相同的 Gemini 提示詞與價格計算。

- [手機版／知識庫](https://foxicall.github.io/Physiotherapy_consultation/)
- [一鍵部署完整 AI 服務至 Render](https://render.com/deploy?repo=https://github.com/foxicall/Physiotherapy_consultation)
- [部署與管理說明](DEPLOYMENT.md)

GitHub Pages 版本提供可安裝、可離線使用的知識庫及價目表。**AI 生成需要另行部署 Python 服務並設定伺服器金鑰**；不會以固定示範文字冒充 AI 結果。完整服務部署後，同一網址同時提供 PWA 與 AI API，也可將服務網址填入 Pages 版的「診所服務連線設定」。

## 手機安裝

- **iPhone / iPad**：使用 Safari 開啟 → 分享 → 加入主畫面 → 新增。
- **Android**：使用 Chrome 開啟 → 安裝到手機，或瀏覽器選單 → 安裝應用程式／加入主畫面。
- 通訊軟體內建瀏覽器可能不支援安裝，請改用系統瀏覽器。正式網址需要 HTTPS；`localhost` 僅供開發。

首次連線下載成功後，即可離線重開知識庫、查閱六欄內容與價目。收藏只記錄症候群編號。AI 生成必須連線；主訴、生成結果、使用碼及授權 token 不會存入 localStorage、Service Worker 或資料庫。重新整理會清除本次主訴、結果及登入狀態。

## 使用流程

1. 依分類、中英文名稱、縮寫、俗稱或症狀搜尋，支援近似名稱及錯字，例如「網球軸」。
2. 查看症候群的六個面向，可收藏，或點選「帶入話術工作台」。
3. 補充實際主訴（選填），選擇對話對象、考量及目標。
4. 連接已部署的診所服務、輸入管理員提供的使用碼，生成四段話術；審閱後複製或匯出 Markdown。
5. 在「診所與價目」查閱官方聯絡資訊、單次與包套價格。

選擇疾病名稱只是溝通情境，不代表確診。知識庫原文完整保留且標示待查核；模型須依既有臨床規則省略無依據的機轉、必然惡化與根治保證，並以已提供的功能情境、適應症及共同決策表達。

## 開發與啟動

建議 Python 3.12、Node.js 22 以上。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-api.txt
cp .env.example .env
```

在 `.env` 設定 `GEMINI_API_KEY` 與足夠強的 `CLINIC_ACCESS_CODE`。正式執行環境也可直接注入環境變數；不要將真實值提交至 Git。

```bash
# 使用容器讀取 .env（已綁定 localhost，正式公開前需 HTTPS 反向代理）
docker compose up --build -d
```

若直接執行 Python，先在 shell 設定上述環境變數，再啟動：

```bash
uvicorn server:api --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

開啟 `http://localhost:8000`。未設定生成金鑰／使用碼時，知識庫可用，AI 生成保持停用。

原有介面仍可用：

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 知識庫維護

`pt-50-syndromes-database.md` 為唯一的原始來源，完整保留使用者提供的 50 套資料。Python 解析器要求編號 1–50 及每筆六個欄位。正式 API 直接讀取原文；離線版由它產生 `docs/catalog.json`。

修改知識庫、診所資料、提示詞常數或前端後，執行：

```bash
python scripts/build_pwa.py
```

此步更新離線資料及依資產內容雜湊命名的快取版本。新版下載後會顯示更新按鈕，由使用者確認更新，避免丟失尚未匯出的話術。生成的 `catalog.json`、`sw.js` 必須一併提交。

## 診所與價目

生生優動板橋診所：新北市板橋區文化路一段142號，電話 [02-8252-1611](tel:+886282521611)。官方資料來源及查核日期保存在 `clinic_info.json`；服務時段不等同逐日醫師門診，預約名額以院所確認為準。

| 服務 | 規格 | 費用 |
| --- | --- | --- |
| 首次評估與治療 | 40 分鐘；初診／首次體驗資格依確認 | NT$999 |
| 專案徒手 | 60 分鐘，單次 | NT$2,200 |
| 儀器整合 | 60 分鐘，單次 | NT$3,200 |
| 專案徒手療程組 | 60 分鐘 × 10 堂 | NT$20,900；折算 NT$2,090／堂 |
| 整合儀器療程組 | 60 分鐘 × 10 堂 | NT$30,400；折算 NT$3,040／堂 |

10 堂是商品規格，不是固定醫療處方；包套均價不是單堂售價。首次 40 分鐘不與其他 60 分鐘服務直接比較價差，未假定首次費用可折抵包套。效期、退費、轉讓、付款及詳細預約條件需向診所確認。自費價目不代表院所其他服務的健保適用情形。

## 驗證

```bash
pip install -r requirements.txt -r requirements-api.txt
python -m unittest discover -s tests -v
npm ci
npm test
npx playwright install --with-deps chromium
npm run test:e2e
```

測試涵蓋資料完整性、檢索、共用提示詞、API 授權、限流、錯誤遮蔽、Streamlit 回歸、手機／桌面操作、安裝資產、離線重開及生成錯誤。自動化測試使用模擬 Gemini 回應，不消耗 API 配額。GitHub Actions 會檢查離線資產是否同步。

## 專案結構

| 檔案 | 用途 |
| --- | --- |
| `server.py` | 正式 API、診所使用碼授權、限流及 PWA 靜態服務 |
| `consultation.py` | 共用 Gemini 生成、提示詞、診所價目與台灣口吻 |
| `app.py` | 原有 Streamlit 介面 |
| `syndrome_kb.py` | 原始 Markdown 解析與 Python 檢索 |
| `catalog.py` | 共用公開資料輸出 |
| `docs/` | 可部署到根目錄或子路徑的 PWA、圖示與離線資產 |
| `scripts/` | 重建離線資料、快取版本及圖示 |
| `tests/` | Python、JavaScript 與瀏覽器測試 |
| `Dockerfile`、`compose.yaml`、`render.yaml` | 正式部署設定 |

本工具提供供治療師審閱的溝通草稿，不代替臨床評估。請勿輸入患者個資。
