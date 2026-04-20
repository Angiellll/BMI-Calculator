# 📊 BMI 健康管理工具（LINE Bot + 網頁顧問版）

這是一個結合 **Python Flask**、**Google Gemini AI**、**Google Sheets** 與 **純前端網頁**的完整健康管理系統。除了提供 LINE Bot 的 BMI 即時計算功能，還搭配一個功能豐富的互動式網頁，提供個人化健康報告與 30 天養成挑戰。

---

## 🌟 核心功能

### LINE Bot
- **BMI 自動計算**：輸入「身高 體重」即可獲得即時健康報告與理想體重建議。
- **AI 專家諮詢**：透過圖文選單（如：飲食建議、運動方案）觸發，由 Gemini AI 根據官方文獻提供個性化回覆。
- **動態資料庫**：建議內容同步自 Google Sheets，無需修改程式碼即可更新官方指引資訊。
- **視覺化報告**：使用 LINE Flex Message 提供美觀且易讀的健康報告單，並附上個人化網頁連結。

### 互動式網頁（index.html）
- **完整健康報告**：輸入身高體重，生成 BMI 狀態、理想體重、目標進度追蹤。
- **飲食菜單建議**：依體位狀態提供三種飲食方案可切換。
- **運動計畫**：戶外場點地圖導引 + 居家訓練計畫。
- **BMI 趨勢圖**：歷史量測紀錄以折線圖呈現，支援時間區間篩選。
- **30 天養成挑戰**：包含每日打卡日曆、Checklist 任務、體重變化曲線圖、里程碑解鎖與分享卡功能。
- **資料持久化**：所有紀錄儲存於瀏覽器 `localStorage`，重新整理不會消失。

---

## 🛠 技術棧 (Tech Stack)

| 層級 | 技術 |
| :--- | :--- |
| 程式語言 | Python 3.10+ |
| 後端框架 | Flask |
| AI 模型 | Google Gemini Flash-Lite（透過 Google AI SDK） |
| 通訊介面 | LINE Messaging API SDK |
| 資料處理 | Pandas（處理 CSV 格式的 Google Sheets） |
| 前端網頁 | 純 HTML / CSS / JavaScript（無框架依賴） |
| 圖表套件 | Chart.js + chartjs-plugin-annotation |
| 部署環境 | Render（PaaS，可延伸至其他雲端平台） |

---

## 📁 專案結構

```text
BMI-Calculator/
├── bmi_bot/
│   ├── app.py            # LINE Bot 主程式
│   └── requirements.txt  # Python 套件清單
├── index.html            # 互動式網頁健康顧問
└── README.md
```

---

## 📋 環境變數設定 (Environment Variables)

在部署至 Render 或本地執行時，請確保已設定以下變數：

| 變數名稱 | 說明 |
| :--- | :--- |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Developers 後台提供的 Access Token |
| `LINE_CHANNEL_SECRET` | LINE Developers 後台提供的 Channel Secret |
| `GEMINI_API_KEY` | Google AI Studio 申請的 API 金鑰 |
| `PORT` | 服務埠號（選填，預設為 `5000`） |

你也可以在 `bmi_bot/` 目錄下建立 `.env` 檔案：

```env
LINE_CHANNEL_ACCESS_TOKEN=你的_LINE_Channel_Access_Token
LINE_CHANNEL_SECRET=你的_LINE_Channel_Secret
GEMINI_API_KEY=你的_Gemini_API_Key
PORT=5000
```

> ⚠️ 請勿將 `.env` 檔案提交至版本控制，確保已將其加入 `.gitignore`。

---

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

### 3. 本地測試（需搭配 ngrok）

啟動 Flask 伺服器：

```bash
python app.py
```

啟動後預設監聽 `http://0.0.0.0:5000`。若要讓 LINE Webhook 連到本機，請另開終端機啟動 ngrok：

```bash
ngrok http 5000
```

將 ngrok 產生的 HTTPS 網址加上 `/callback`，填入 LINE Developers 後台的 Webhook URL 欄位。

---

## 💬 使用方式

### LINE Bot

#### 1) BMI 計算

直接傳訊息（身高與體重以空格分隔）：

```
175 70
```

機器人會回覆 Flex Message 包含：
- BMI 數值與體位狀態
- 理想體重與管理目標
- 飲食建議與運動方案
- 個人化網頁詳細報告連結

#### 2) AI 健康指引

傳送以下關鍵字之一：

```
飲食建議 / 運動方案 / 體位標準 / 常見迷思破解 / 身體活動指引
```

機器人會從 Google Sheets 抓取對應的國健署資料，透過 Gemini AI 生成個性化建議回覆。

### 網頁工具

直接開啟 `index.html`，或透過 LINE Bot 報告單底部的「瀏覽個人化詳細報告」按鈕進入，網頁會自動帶入身高、體重與目標體重參數。

---

## ⚙️ 固定設定說明

`app.py` 內有兩個固定常數，可視需求直接修改：

```python
SHEET_CSV_URL = "..."   # Google Sheets 公開 CSV 來源
MY_WEBSITE_URL = "..."  # Flex Message 按鈕連結的網頁網址
```

---

## 🚢 部署（Gunicorn）

`requirements.txt` 已包含 `gunicorn`，正式部署時建議使用：

```bash
gunicorn app:app --bind 0.0.0.0:5000
```

---

## ❓ 常見問題

| 問題 | 解法 |
| :--- | :--- |
| 出現「請輸入正確格式」 | 確認輸入格式為 `身高 體重`，例如 `168 60`，中間以半形空格分隔 |
| AI 回覆失敗 | 確認 `GEMINI_API_KEY` 是否正確，並檢查 Gemini API 用量是否已達上限 |
| LINE Webhook 回傳 400 | 確認 `LINE_CHANNEL_SECRET` 是否正確，Webhook URL 結尾需為 `/callback` |
| 圖文選單無回應 | 確認 Gemini API 金鑰有效且仍有可用額度，可至 Google AI Studio 查看用量 |
| 網頁資料消失 | 網頁資料儲存於瀏覽器 `localStorage`，清除瀏覽器快取或換裝置會導致資料遺失 |