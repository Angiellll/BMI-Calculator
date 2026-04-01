import os
import pandas as pd
import google.generativeai as genai
import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, FlexSendMessage, TextSendMessage
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ==========================================
# 1. 配置與檔案處理
# ==========================================
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'), timeout=60)
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# 設定 Gemini AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(model_name='gemini-flash-lite-latest')

# 設定與路徑
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR3WLMM8SN9OmkMBf6y0zqMxBmq9LO7AUKToJn-UoRmYL4dStUpE6KPnzV2-ZDwD9B98sC4ymomsKH6/pub?gid=0&single=true&output=csv"
MY_WEBSITE_URL = "https://angiellll.github.io/BMI-Calculator/"
PROGRESS_FILE = 'user_progress.json'

# --- 讀取/儲存進度功能 (防止 Render 重啟歸零) ---
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_progress(data):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f)

# 初始化進度資料
user_progress = load_progress()

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['x-line-signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

def get_ai_advice(category):
    """從試算表抓取資料並透過 Gemini 轉化建議"""
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        df['Category'] = df['Category'].str.strip()
        row = df[df['Category'] == category]

        if row.empty:
            return f"抱歉，目前找不到「{category}」的相關指引。"

        official_text = row['Content'].values[0]
        ref_link = row['Reference_Link'].values[0]

        prompt = f"""
        你是一位專業且親切的健康顧問。
        根據以下官方指引：{official_text}
        請針對「{category}」這個主題，寫一段約 80-100 字的口語化建議，口吻要溫馨鼓勵。
        最後請換行並加上：「詳細資訊可參考國健署指引：{ref_link}」
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"AI Advice Error: {e}")
        return "健康顧問目前正在翻閱資料中，請稍後再試！"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global user_progress
    user_id = event.source.user_id
    user_msg = event.message.text.strip()

    # 1. 處理「查詢進度」
    if user_msg == "查詢進度":
        user_progress = load_progress() # 重新讀取確保資料最新
        current_day = user_progress.get(user_id, 0)
        if current_day == 0:
            reply = "你還沒有開始 30 天挑戰喔！\n快完成一次 BMI 計算來獲取挑戰方案吧！"
        else:
            reply = f"📊 您的個人化挑戰進度：\n目前已持續實踐：{current_day} 天\n距離 30 天目標還剩：{30 - current_day} 天\n\n加油，你是最棒的！💪"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    # 2. 處理「我已完成實踐」
    if user_msg == "我已完成實踐":
        user_progress[user_id] = user_progress.get(user_id, 0) + 1
        save_progress(user_progress)
        day = user_progress[user_id]
        line_bot_api.reply_message(
            event.reply_token, 
            TextSendMessage(text=f"✅ 紀錄成功！恭喜您完成第 {day} 天的實踐。明天也要繼續堅持喔！✨")
        )
        return

    # 3. 處理圖文選單關鍵字
    menu_keywords = ["飲食建議", "運動方案", "體位標準", "常見迷思破解", "身體活動指引"]
    if user_msg in menu_keywords:
        ai_reply = get_ai_advice(user_msg)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ai_reply))
        return

    # 4. 處理 BMI 計算邏輯
    try:
        clean_msg = user_msg.replace('　', ' ').replace('\n', ' ')
        parts = [p for p in clean_msg.split(' ') if p] 
        
        if len(parts) < 2:
            return 

        height = float(parts[0])
        weight = float(parts[1])

        if not (50 <= height <= 250 and 10 <= weight <= 300):
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="💡 偵測到數值可能不正確，請重新輸入（身高 體重）"))
            return

        # 計算數值
        height_m = height / 100
        bmi = round(weight / (height_m ** 2), 1)
        ideal_weight = round(22 * (height_m ** 2), 1)
        weight_diff = round(weight - ideal_weight, 1)

        # 判定狀態與內容
        if bmi < 18.5:
            status, color = "體重過輕", "#4a90e2"
            diet, outdoor, home = "加強蛋白質與熱量攝取。", "🏋️ 重訓增肌優於有氧。", "🏠 居家徒手訓練：深蹲。"
        elif bmi < 24:
            status, color = "正常範圍", "#2ecc71"
            diet, outdoor, home = "維持原型食物與均衡營養。", "🏃 維持規律有氧運動。", "🏠 每日拉筋伸展。"
        elif bmi < 27:
            status, color = "過重", "#f1c40f"
            diet, outdoor, home = "控制精緻澱粉，增加蔬菜量。", "🚴 中強度有氧（快走）。", "🏠 高強度間歇運動（HIIT）。"
        else:
            status, color = "肥胖", "#e74c3c"
            diet, outdoor, home = "尋求營養師制定減脂餐單。", "🏊 水中運動減輕關節負擔。", "🏠 超慢跑訓練。"

        if weight_diff > 0:
            goal_text = f"理想體重為 {ideal_weight}kg，距離目標還需努力 {weight_diff}kg。"
        elif weight_diff < 0:
            goal_text = f"理想體重為 {ideal_weight}kg，目前狀態相當精實！"
        else:
            goal_text = "恭喜！您正處於完美的理想體重。"

        # --- 重要：保留並修正網址拼接邏輯 ---
        # 確保格式正確，例如：.../index.html?h=175&w=70
        sep = "&" if "?" in MY_WEBSITE_URL else "?"
        personalized_url = f"{MY_WEBSITE_URL}{sep}h={height}&w={weight}"

        # 5. 建立 Flex Message 報告
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box", "layout": "vertical", "contents": [
                    {"type": "text", "text": "📊 健康報告摘要", "weight": "bold", "size": "md", "color": "#aaaaaa"},
                    {"type": "text", "text": str(bmi), "weight": "bold", "size": "5xl", "color": color, "margin": "md"},
                    {"type": "text", "text": f"狀態：{status}", "size": "lg", "color": color, "weight": "bold"}
                ], "alignItems": "center", "paddingTop": "20px"
            },
            "body": {
                "type": "box", "layout": "vertical", "contents": [
                    {"type": "separator", "margin": "md"},
                    {"type": "text", "text": "🎯 管理目標", "weight": "bold", "margin": "lg", "size": "md", "color": "#333333"},
                    {"type": "text", "text": goal_text, "size": "sm", "color": "#666666", "wrap": True, "margin": "sm"},
                    {"type": "text", "text": "🍎 飲食重點", "weight": "bold", "margin": "lg", "size": "md", "color": "#333333"},
                    {"type": "text", "text": diet, "size": "sm", "color": "#666666", "wrap": True, "margin": "sm"},
                    {"type": "text", "text": "🌲 運動建議", "weight": "bold", "margin": "lg", "size": "md", "color": "#333333"},
                    {"type": "box", "layout": "vertical", "margin": "sm", "contents": [
                        {"type": "text", "text": f"📍 戶外：{outdoor}", "size": "sm", "color": "#666666", "wrap": True},
                        {"type": "text", "text": f"🏠 室內：{home}", "size": "sm", "color": "#666666", "wrap": True, "margin": "xs"}
                    ]}
                ]
            },
            "footer": {
                "type": "box", "layout": "vertical", "spacing": "sm", "contents": [
                    {
                        "type": "button", "style": "primary", "color": color,
                        "action": {
                            "type": "uri", 
                            "label": "🌐 瀏覽個人化詳細報告", 
                            "uri": personalized_url
                        }
                    },
                    {
                        "type": "button", "style": "secondary", "margin": "md",
                        "action": {
                            "type": "message", 
                            "label": "📈 查詢計畫進度", 
                            "text": "查詢進度"
                        }
                    }
                ], "paddingAll": "20px"
            }
        }

        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="您的健康報告已送達", contents=flex_content))

    except Exception as e:
        print(f"Main Error: {e}")
        line_bot_api.reply_message(
            event.reply_token, 
            TextSendMessage(text="💡 想要計算 BMI 嗎？\n請直接輸入「身高 體重」\n例如：175 70")
        )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)