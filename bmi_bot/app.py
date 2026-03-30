import os
import pandas as pd
import google.generativeai as genai
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, FlexSendMessage, TextSendMessage
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# 配置 LINE Bot
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'), timeout=60)
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# 設定 Gemini AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(model_name='models/gemini-1.5-flash')

# 設定與路徑
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR3WLMM8SN9OmkMBf6y0zqMxBmq9LO7AUKToJn-UoRmYL4dStUpE6KPnzV2-ZDwD9B98sC4ymomsKH6/pub?gid=0&single=true&output=csv"
MY_WEBSITE_URL = "https://angiellll.github.io/BMI-Calculator/"

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
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        df['Category'] = df['Category'].str.strip()
        row = df[df['Category'] == category]
        if row.empty: return f"找不到「{category}」相關指引。"
        
        official_text = row['Content'].values[0]
        ref_link = row['Reference_Link'].values[0]
        prompt = f"你是一位親切的健康顧問，根據資料：{official_text}，針對「{category}」提供約 80 字溫馨建議，並附上連結：{ref_link}"
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return "服務稍忙，請稍後再試！"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_msg = event.message.text.strip()
    menu_keywords = ["飲食建議", "運動方案", "體位標準", "常見迷思破解", "身體活動指引"]
    
    if user_msg in menu_keywords:
        ai_reply = get_ai_advice(user_msg)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ai_reply))
        return

    # 解析 身高 體重
    try:
        parts = user_msg.split()
        if len(parts) < 2: raise ValueError()
        
        h, w = float(parts[0]), float(parts[1])
        bmi = round(w / ((h / 100) ** 2), 1)
        ideal_w = round(22 * ((h / 100) ** 2), 1)

        # 判定
        if bmi < 18.5: status, color = "體重過輕", "#4a90e2"
        elif bmi < 24: status, color = "正常範圍", "#2ecc71"
        elif bmi < 27: status, color = "過重", "#f1c40f"
        else: status, color = "肥胖", "#e74c3c"

        # 關鍵：帶參數網址
        personalized_url = f"{MY_WEBSITE_URL}?h={h}&w={w}"

        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box", "layout": "vertical", "contents": [
                    {"type": "text", "text": "健康報告單", "weight": "bold", "size": "xl"},
                    {"type": "text", "text": str(bmi), "weight": "bold", "size": "5xl", "color": color, "margin": "md"},
                    {"type": "text", "text": f"狀態：{status}", "size": "md", "color": color, "weight": "bold"}
                ], "alignItems": "center"
            },
            "body": {
                "type": "box", "layout": "vertical", "contents": [
                    {"type": "separator", "margin": "md"},
                    {"type": "text", "text": "🎯 管理目標", "weight": "bold", "margin": "lg"},
                    {"type": "text", "text": f"理想體重為 {ideal_w}kg", "size": "sm", "color": "#666666"}
                ]
            },
            "footer": {
                "type": "box", "layout": "vertical", "contents": [
                    {
                        "type": "button", "style": "primary", "color": "#4a90e2",
                        "action": {"type": "uri", "label": "🌐 瀏覽趨勢與詳細報告", "uri": personalized_url}
                    }
                ]
            }
        }
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="BMI報告", contents=flex_content))

    except:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="💡 請輸入正確格式：身高 體重\n例如：175 70"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))