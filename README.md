# 🌿 BMI 健康管理工具（LINE Bot + 網頁 AI 顧問版）

結合 **Python Flask**、**Google Gemini AI**、**Google Sheets** 與 **純前端網頁**的完整健康管理系統。透過 LINE Bot 提供 BMI 即時計算，並搭配功能豐富的互動式網頁，提供個人化健康報告、30 天養成挑戰與 AI 即時對話。

---

## 🌟 目前功能一覽

### LINE Bot（`bmi_bot/app.py`）

| 功能 | 說明 |
| :--- | :--- |
| **BMI 即時計算** | 傳送 `身高 體重`（例：`175 70`），回傳 BMI 數值、體位狀態、理想體重與飲食運動建議 |
| **Flex Message 報告** | 以視覺化卡片呈現健康報告，附帶個人化網頁連結按鈕 |
| **AI 健康建議** | 傳送關鍵字（飲食建議、運動方案、體位標準、常見迷思破解、身體活動指引），從 Google Sheets 抓取國健署資料，透過 Gemini 生成親切建議 |

### 互動式網頁（`index.html`）

| 功能 | 說明 |
| :--- | :--- |
| **完整 BMI 報告** | 輸入身高體重，顯示 BMI、體位狀態、理想體重，依台灣衛福部標準判斷 |
| **目標進度追蹤** | 設定目標體重後，顯示進度條與距離目標的差距 |
| **BMI 趨勢圖表** | 歷史量測紀錄以折線圖呈現，支援近 10 次 / 一個月 / 一年篩選 |
| **新手引導橫幅** | 依體位狀態顯示個人化的「第一步建議」 |
| **飲食菜單建議** | 依體位提供三種飲食方案（A / B / C）可切換，附國健署參考連結 |
| **戶外運動場點** | 依體位推薦場所類型，點擊直接開啟 Google Maps 搜尋 |
| **居家運動計畫** | 依體位提供對應的居家訓練動作與組數建議 |
| **30 天養成挑戰** | 依 BMI 狀態自動顯示「增肌挑戰」或「燃脂挑戰」，包含每日打卡日曆、Checklist 任務、里程碑解鎖與 confetti 慶祝特效 |
| **體重變化記錄** | 挑戰期間可每日記錄體重，以折線圖追蹤 30 天變化 |
| **分享卡** | 達成 7 / 14 / 21 / 30 天里程碑後解鎖，可複製文字分享給朋友 |
| **AI 即時對話框** | 右下角懸浮按鈕，點開後可直接詢問 AI 健康問題，AI 會根據你的 BMI 狀態給出個人化回覆 |
| **資料持久化** | BMI 歷史、挑戰進度、體重記錄皆存於瀏覽器 `localStorage` |

---

## 🛠 技術棧

| 層級 | 技術 |
| :--- | :--- |
| 程式語言 | Python 3.10+、JavaScript |
| 後端框架 | Flask + Flask-CORS |
| AI 模型 | Google Gemini Flash-Lite |
| 通訊介面 | LINE Messaging API SDK |
| 資料來源 | Google Sheets（公開 CSV）+ Pandas |
| 前端 | 純 HTML / CSS / JavaScript（無框架） |
| 圖表 | Chart.js + chartjs-plugin-annotation |
| 特效 | canvas-confetti |
| 部署 | Render（後端）+ GitHub Pages（前端） |

---

## 📁 專案結構

```text
BMI-Calculator/
├── bmi_bot/
│   ├── app.py            # Flask 後端：LINE Bot + /chat AI 端點
│   └── requirements.txt
├── index.html            # 互動式網頁（含 AI 對話框）
└── README.md
```

---

## 📋 環境變數設定

在 `bmi_bot/` 建立 `.env` 檔案：

```env
LINE_CHANNEL_ACCESS_TOKEN=你的_LINE_Channel_Access_Token
LINE_CHANNEL_SECRET=你的_LINE_Channel_Secret
GEMINI_API_KEY=你的_Gemini_API_Key
PORT=5000
```

> ⚠️ 請將 `.env` 加入 `.gitignore`，避免金鑰外洩。

Render 部署時，在 Dashboard → Environment 分頁設定相同的三個變數。

---

## 🚀 快速開始

```bash
# 1. 安裝套件
cd bmi_bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. 啟動後端
python app.py

# 3. 本機測試需搭配 ngrok（LINE Webhook 用）
ngrok http 5000
```

將 ngrok 產生的 HTTPS 網址加上 `/callback`，填入 LINE Developers 後台的 Webhook URL。

---

## 💬 使用方式

### LINE Bot

```
175 70              → 回傳 BMI 報告（Flex Message）
飲食建議            → AI 依國健署資料生成飲食建議
運動方案            → AI 依國健署資料生成運動建議
體位標準            → AI 說明台灣 BMI 判斷標準
常見迷思破解        → AI 破解常見健康迷思
身體活動指引        → AI 說明每週建議運動量
```

### 網頁版

直接開啟 `index.html`，或透過 LINE Bot 報告卡片底部的「瀏覽個人化詳細報告」按鈕進入（網址會自動帶入身高、體重、目標體重參數）。

**AI 對話框使用方式：**
1. 輸入身高體重，生成報告
2. 點右下角 💬 按鈕開啟對話
3. 直接輸入問題，或點選快速回覆按鈕
4. AI 會根據你的 BMI 狀態給出個人化回覆

---

## ⚙️ 部署說明

### 後端（Render）

```bash
# 使用 gunicorn 啟動
gunicorn app:app --bind 0.0.0.0:5000
```

### 前端（GitHub Pages）

`index.html` 部署後，需將 AI 對話框的後端網址更新：

```javascript
// index.html 第一行 JS 設定
const FLASK_CHAT_URL = 'https://你的app.onrender.com/chat';
```

---

## ❓ 常見問題

| 問題 | 解法 |
| :--- | :--- |
| 「請輸入正確格式」 | 格式為 `身高 體重`，例如 `168 60`，中間半形空格 |
| AI 回覆失敗 | 確認 `GEMINI_API_KEY` 正確且有可用額度 |
| LINE Webhook 400 | 確認 `LINE_CHANNEL_SECRET` 正確，Webhook URL 結尾為 `/callback` |
| AI 對話框連線失敗 | 確認 `FLASK_CHAT_URL` 為 Render 正式網址，且 `flask-cors` 已安裝 |
| 網頁資料消失 | 資料存於瀏覽器 `localStorage`，清除快取或換裝置會遺失 |
