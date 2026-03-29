# 📊 BMI 健康管理 LINE Bot (AI 顧問版)

這是一個結合 **Python Flask**、**Google Gemini AI** 與 **Google Sheets** 的智慧型 LINE Bot。除了提供基本的 BMI 計算功能，還能根據國健署官方資料，透過 AI 生成個性化健康建議。

## 🌟 核心功能

- **BMI 自動計算**：輸入「身高 體重」即可獲得即時健康報告與理想體重建議。
- **AI 專家諮詢**：透過圖文選單（如：飲食建議、運動方案）觸發，由 Gemini AI 根據官方文獻提供溫暖回覆。
- **動態資料庫**：建議內容同步自 Google Sheets，無需修改程式碼即可更新官方指引資訊。
- **視覺化報告**：使用 LINE Flex Message 提供美觀且易讀的健康報告單。

## 🛠 技術棧 (Tech Stack)

- **程式語言**：Python 3.10+
- **後端框架**：Flask
- **AI 模型**：Google Gemini Flash-Lite（透過 Google AI SDK）
- **通訊介面**：LINE Messaging API SDK
- **資料處理**：Pandas（處理 CSV 格式的 Google Sheets）
- **部署環境**：Render（PaaS，可延伸至其他雲端平台）

## 📁 專案結構

```text
bmi_bot/
├── app.py
├── requirements.txt
└── README.md
```

## 📋 環境變數設定 (Environment Variables)

在部署至 Render 或本地執行時，請確保已設定以下變數：

| 變數名稱 | 說明 |
| :--- | :--- |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Developers 後台提供的 Access Token |
| `LINE_CHANNEL_SECRET` | LINE Developers 後台提供的 Secret |
| `GEMINI_API_KEY` | Google AI Studio 申請的 API 金鑰 |
| `PORT` | 服務埠號（可省略，預設 `5000`） |

你也可以在專案根目錄建立 `.env`：

```env
LINE_CHANNEL_ACCESS_TOKEN=你的_LINE_Channel_Access_Token
LINE_CHANNEL_SECRET=你的_LINE_Channel_Secret
GEMINI_API_KEY=你的_Gemini_API_Key
PORT=5000 //可不用
```

## 🚀 快速開始

### 1. 複製專案

```bash
git clone https://github.com/Angiellll/BMI-Calculator.git
cd BMI-Calculator/bmi_bot
```

### 2. 安裝套件

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 本地測試（需搭配 ngrok） //可忽略

```bash
python app.py
```

啟動後預設監聽 `http://0.0.0.0:5000`。

若要讓 LINE Webhook 可連到本機服務，請啟動 ngrok：

```bash
ngrok http 5000
```

將 ngrok 產生的 HTTPS 網址，設定到 LINE Developers Webhook（尾端加上 `/callback`）。

## 💬 使用方式

### 1) BMI 計算

直接傳訊息：

```text
175 70
```

機器人會回覆：
- BMI 數值與體位狀態
- 理想體重與管理目標
- 飲食建議與運動方案
- 網站詳細內容連結

### 2) AI 指引

可傳送以下關鍵字之一：

- 飲食建議
- 運動方案
- 體位標準
- 常見迷思破解
- 身體活動指引

機器人會從 Google Sheets 抓取對應資料，並透過 Gemini 生成建議回覆。

## ⚙️ 目前程式中的固定設定

`app.py` 內有兩個固定常數：
- `SHEET_CSV_URL`：Google Sheets 公開 CSV 來源
- `MY_WEBSITE_URL`：Flex Message 按鈕連到的網站

如需更換資料來源或網站，直接修改這兩個常數即可。

## 🚢 部署（Gunicorn）

`requirements.txt` 已包含 `gunicorn`，可用以下方式啟動：

```bash
gunicorn app:app --bind 0.0.0.0:5000
```

## ❓ 常見問題

- 出現「請輸入正確格式」：請輸入 `身高 體重`，例如 `168 60`。
- AI 回覆失敗：先確認 `GEMINI_API_KEY` 是否正確，並檢查網路連線。
- LINE Webhook `400`：請確認 `LINE_CHANNEL_SECRET` 與 Webhook URL 的 `/callback` 路徑是否正確。
- 點圖文選單出不了結果大概是因為API用完了
