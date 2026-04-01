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

# ==========================================
# 1. 配置金鑰
# ==========================================
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'), timeout=60)
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# 設定 Gemini AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(model_name='models/gemini-flash-lite-latest')

# ★ 你的設定
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
    """從試算表抓取官方資料並透過 Gemini 轉化成親切建議"""
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
        根據以下資料：{official_text}
        針對「{category}」寫一段約 80 字的溫暖建議。
        最後加上：「想了解更多細節，歡迎參考國健署全文：{ref_link}」
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"AI Error: {e}")
        return "服務稍忙，請稍後再試！"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_msg = event.message.text.strip()

    # 圖文選單關鍵字
    menu_keywords = ["飲食建議", "運動方案", "體位標準", "常見迷思破解", "身體活動指引"]
    if user_msg in menu_keywords:
        ai_reply = get_ai_advice(user_msg)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ai_reply))
        return

    # BMI 計算與解析邏輯
    try:
        # 解析輸入，支援全形或半形空格
        parts = user_msg.replace('　', ' ').split()
        if len(parts) < 2:
            raise ValueError("參數不足")

        height = float(parts[0])
        weight = float(parts[1])

        # 基本數值檢查
        if height <= 0 or weight <= 0:
            raise ValueError("數值無效")

        # 計算數值
        height_m = height / 100
        bmi = round(weight / (height_m ** 2), 1)
        ideal_weight = round(22 * (height_m ** 2), 1)
        weight_diff = round(weight - ideal_weight, 1)

        # 判定狀態與顏色內容
        if bmi < 18.5:
            status, color = "體重過輕", "#4a90e2"
            diet, outdoor, home = "多攝取優質蛋白質。", "🏋️ 基礎重訓增肌。", "🏠 伏地挺身、深蹲。"
        elif bmi < 24:
            status, color = "正常範圍", "#2ecc71"
            diet, outdoor, home = "維持均衡飲食。", "🏃 慢跑或快走。", "🏠 瑜珈伸展。"
        elif bmi < 27:
            status, color = "過重", "#f1c40f"
            diet, outdoor, home = "減少精緻澱粉。", "🚴 每週 3 次快走。", "🏠 開合跳、波比跳。"
        else:
            status, color = "肥胖", "#e74c3c"
            diet, outdoor, home = "諮詢營養師建議。", "🏊 游泳保護關節。", "🏠 超慢跑訓練。"

        goal_text = f"理想體重 {ideal_weight}kg。{'尚需減少 ' + str(weight_diff) + 'kg' if weight_diff > 0 else '繼續保持！'}"
        # 原本的寫法（只有身高體重）
        # personalized_url = f"{MY_WEBSITE_URL}?h={height}&w={weight}"
        # 修改後的寫法：自動把計算出來的「理想體重」當作預設目標 t 傳過去
        personalized_url = f"{MY_WEBSITE_URL}?h={height}&w={weight}&t={ideal_weight}"

        # 建立 Flex Message 結構
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box", "layout": "vertical", "contents": [
                    {"type": "text", "text": "健康報告單", "weight": "bold", "size": "xl", "color": "#333333"},
                    {"type": "text", "text": str(bmi), "weight": "bold", "size": "5xl", "color": color, "margin": "md"},
                    {"type": "text", "text": f"狀態：{status}", "size": "md", "color": color, "weight": "bold"}
                ], "alignItems": "center", "paddingTop": "20px"
            },
            "body": {
                "type": "box", "layout": "vertical", "contents": [
                    {"type": "separator", "margin": "md"},
                    {"type": "text", "text": "🎯 管理目標", "weight": "bold", "margin": "lg", "size": "md"},
                    {"type": "text", "text": goal_text, "size": "sm", "color": "#666666", "wrap": True, "margin": "sm"},
                    {"type": "text", "text": "🍎 飲食建議", "weight": "bold", "margin": "lg", "size": "md"},
                    {"type": "text", "text": diet, "size": "sm", "color": "#666666", "wrap": True, "margin": "sm"},
                    {"type": "text", "text": "🌲 運動方案", "weight": "bold", "margin": "lg", "size": "md"},
                    {"type": "box", "layout": "vertical", "margin": "sm", "contents": [
                        {"type": "text", "text": f"戶外：{outdoor}", "size": "sm", "color": "#666666", "wrap": True},
                        {"type": "text", "text": f"室內：{home}", "size": "sm", "color": "#666666", "wrap": True, "margin": "xs"}
                    ]}
                ]
            },
            "footer": {
                "type": "box", "layout": "vertical", "contents": [
                    {
                        "type": "button", "style": "primary", "color": "#4a90e2",
                        "action": {
                            "type": "uri", 
                            "label": "🌐 瀏覽個人化詳細報告", 
                            "uri": personalized_url
                        }
                    }
                ], "paddingAll": "20px"
            }
        }

        # 範例判斷與發送
        if height == 175.0 and weight == 70.0:
            line_bot_api.reply_message(event.reply_token, [
                TextSendMessage(text="📊 這是計算範例說明：\n請依照「身高 體重」格式輸入即可！"),
                FlexSendMessage(alt_text="您的健康報告", contents=flex_content)
            ])
        else:
            line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="您的健康報告", contents=flex_content))

    except Exception as e:
        print(f"Error: {e}")
        line_bot_api.reply_message(
            event.reply_token, 
            TextSendMessage(text="💡 請輸入正確格式：身高 體重\n例如：175 70\n（注意中間要有空格喔！）")
        )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))