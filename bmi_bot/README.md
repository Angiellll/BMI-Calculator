# 📊 BMI 健康管理工具（LINE Bot + 網頁顧問版）

這個專案結合 **Python Flask**、**Google Gemini AI**、**Google Sheets** 與 **純前端網頁**，做出一個可在 LINE 內互動、也可在網頁上使用的 BMI 健康管理系統。

---

## 🌟 核心功能

### LINE Bot（`bmi_bot/app.py`）
- **BMI 自動計算**：輸入 `身高 體重` 就能回傳 BMI、體位狀態、理想體重與健康建議。
- **AI 健康建議**：傳送 `飲食建議`、`運動方案`、`體位標準`、`常見迷思破解`、`身體活動指引`，會從 Google Sheets 抓資料，再交給 Gemini 生成回覆。
- **小精靈互動**：輸入 `我的精靈` 會顯示等級、EXP 與小精靈圖示；`運動 XX` 和 `簽到` 會累積 EXP。
- **個人化報告連結**：BMI Flex Message 會附上個人化網頁網址，把身高、體重、目標體重一起帶入。

### 互動式網頁（`index.html`）
- **完整 BMI 報告**：可直接輸入身高、體重與目標體重，產生 BMI 狀態、理想體重與目標進度。
- **飲食、運動、挑戰整合**：提供飲食菜單、戶外場點、居家運動與 30 天挑戰內容。
- **歷史紀錄與圖表**：支援 BMI 歷史明細、趨勢圖、時間篩選與目標線。
- **網頁小精靈**：30 天挑戰模組內會顯示寵物/小精靈，並依完成狀況升級。
- **資料儲存**：多數紀錄存在瀏覽器 `localStorage`，重新整理後仍會保留。

---

## 🛠 技術棧 (Tech Stack)

| 層級 | 技術 |
| :--- | :--- |
| 程式語言 | Python 3.10+、JavaScript |
| 後端框架 | Flask |
| AI 模型 | Google Gemini Flash-Lite（透過 Google AI SDK） |
| 通訊介面 | LINE Messaging API SDK |
| 資料處理 | Pandas（讀取 Google Sheets CSV） |
| 前端網頁 | HTML / CSS / JavaScript |
| 圖表套件 | Chart.js、chartjs-plugin-annotation |
| 特效套件 | canvas-confetti |
| 部署環境 | Render 或其他支援 Python 的平台 |

---

## 📁 專案結構

```text
BMI-Calculator/
├── bmi_bot/
│   ├── app.py
│   ├── requirements.txt
│   └── README.md
├── index.html
└── README.md
```

---

## 📋 環境變數設定

請在 `bmi_bot/` 內建立 `.env` 檔案，並設定：

| 變數名稱 | 說明 |
| :--- | :--- |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Developers 的 Access Token |
| `LINE_CHANNEL_SECRET` | LINE Developers 的 Channel Secret |
| `GEMINI_API_KEY` | Google AI Studio 的 API 金鑰 |
| `PORT` | 服務埠號，未設定時預設為 `5000` |

範例：

```env
LINE_CHANNEL_ACCESS_TOKEN=你的_LINE_Channel_Access_Token
LINE_CHANNEL_SECRET=你的_LINE_Channel_Secret
GEMINI_API_KEY=你的_Gemini_API_Key
PORT=5000
```

> 建議把 `.env` 加入 `.gitignore`，避免把金鑰提交到 GitHub。

---

## 🚀 快速開始

### 1. 安裝套件

```bash
cd /Users/angie/Desktop/bmi_bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 啟動 LINE Bot

```bash
python app.py
```

預設會在 `http://0.0.0.0:5000` 啟動。

如果要讓 LINE Webhook 連到本機，請另外啟動 ngrok：

```bash
ngrok http 5000
```

把 ngrok 產生的網址加上 `/callback` 後，填到 LINE Developers 的 Webhook URL。

### 3. 開啟網頁版

直接用瀏覽器打開 `index.html`，或把它部署到 GitHub Pages / 其他靜態網站平台。

---

## 💬 使用方式

### LINE Bot

#### BMI 計算

直接傳送：

```text
175 70
```

會回覆：
- BMI 數值與狀態
- 理想體重與管理目標
- 飲食建議、戶外方案、居家運動
- 個人化網頁報告按鈕

#### AI 健康建議

直接傳送：

```text
飲食建議
運動方案
體位標準
常見迷思破解
身體活動指引
```

機器人會先從 Google Sheets 讀取內容，再交給 Gemini 生成自然語氣的建議。

#### 小精靈 / 遊戲化

```text
我的精靈
運動 30
簽到
```

- `我的精靈`：顯示目前等級、EXP 與小精靈。
- `運動 XX`：每分鐘加 EXP。
- `簽到`：固定加 EXP。

> 注意：LINE Bot 的小精靈目前是存在 `app.py` 的記憶體中，伺服器重啟後可能會重置。

### 網頁版

打開 `index.html` 後，可直接輸入身高、體重與目標體重，網頁會顯示：
- BMI 狀態與理想體重
- 目標進度條
- 歷史紀錄圖表
- 飲食菜單、戶外場點、居家運動
- 30 天挑戰、體重記錄與分享卡

若網址帶有參數，例如：

```text
index.html?h=175&w=70&t=65
```

會自動帶入身高、體重與目標體重。

---

## ⚙️ 程式中的固定設定

`bmi_bot/app.py` 裡有兩個固定常數：

```python
SHEET_CSV_URL = "..."   # Google Sheets 公開 CSV 來源
MY_WEBSITE_URL = "..."  # LINE Flex Message 的個人化網頁網址
```

如果你更換 Google Sheets 或網站網址，只要修改這兩個值就可以。

---

## 🚢 部署（Gunicorn）

`requirements.txt` 已包含 `gunicorn`，部署時可使用：

```bash
gunicorn app:app --bind 0.0.0.0:5000
```

---

## ❓ 常見問題

| 問題 | 解法 |
| :--- | :--- |
| 出現「請輸入正確格式」 | 請確認格式是 `身高 體重`，例如 `168 60`，中間要有半形空格 |
| AI 回覆失敗 | 確認 `GEMINI_API_KEY` 正確，且 Google AI Studio 還有可用額度 |
| LINE Webhook 回傳 400 | 確認 `LINE_CHANNEL_SECRET` 正確，Webhook URL 結尾要是 `/callback` |
| `我的精靈` 沒反應 | 確認 LINE Bot 已啟動，且 `LINE_CHANNEL_ACCESS_TOKEN` 有設定 |
| 網頁資料消失 | 網頁資料存放在瀏覽器 `localStorage`，清除快取或換裝置會消失 |
