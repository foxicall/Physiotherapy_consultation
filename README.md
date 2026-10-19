# 物理治療業務話術產生器

使用 Python、Streamlit 與 Google GenAI SDK，透過 `gemini-2.5-flash` 產生繁體中文顧問式溝通指南。

## 安裝與啟動

在專案根目錄執行（建議 Python 3.10 以上）：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

設定 Google Gemini API 金鑰（請使用自己的有效金鑰，勿提交到 Git）：

```bash
export GEMINI_API_KEY="你的 API 金鑰"
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
```

開啟 `http://localhost:8501`；遠端環境請使用該環境提供的 8501 連接埠預覽或轉送網址。

## 使用方式

1. 在側邊欄選擇症狀、溝通目標、抗拒點與患者特質。自訂症狀填寫後優先使用。
2. 點選主畫面的「🚀 生成話術指南」。
3. 閱讀五個章節的 Markdown 預覽，在「複製完整話術」分頁使用程式碼區塊右上角的複製圖示。

結果保留於目前 Streamlit 工作階段；修改欄位不會清除上次成功結果，重新整理或中斷工作階段後可能消失。畫面會標明結果對應的情境。

請求逾時設定為 60 秒，停用自動重試；遇到錯誤可手動重新生成。系統會提示缺少金鑰、權限問題、配額限制、網路與逾時等錯誤，不顯示原始 API 錯誤以避免暴露敏感資訊。

輸入會傳送至 Google Gemini，請勿提供患者個資。輸出是溝通草稿，需由治療師依臨床評估確認，不可作為診斷或療效保證。

## 檔案

- `app.py`：介面、提示詞、API 呼叫與錯誤處理。
- `requirements.txt`：相依套件。
- `README.md`：安裝與使用說明。
