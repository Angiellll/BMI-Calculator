import os
import pandas as pd
import google.generativeai as genai
from flask import Flask, request, abort, jsonify
from flask_cors import CORS                          # ← 新增：允許網頁跨域呼叫
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, FlexSendMessage, TextSendMessage
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/chat": {"origins": "*"}})   # ← 只開放 /chat 端點的跨域

# ==========================================
# 1. 配置金鑰
# ==========================================
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'), timeout=60)
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(model_name='models/gemini-flash-lite-latest')

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR3WLMM8SN9OmkMBf6y0zqMxBmq9LO7AUKToJn-UoRmYL4dStUpE6KPnzV2-ZDwD9B98sC4ymomsKH6/pub?gid=0&single=true&output=csv"
MY_WEBSITE_URL = "https://angiellll.github.io/BMI-Calculator/"


# ==========================================
# 2. LINE Webhook
# ==========================================
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['x-line-signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


# ==========================================
# 3. 【新增】網頁 AI 對話框端點
# ==========================================
@app.route("/chat", methods=['POST'])
def chat():
    """
    接收網頁傳來的對話請求，帶入使用者 BMI 狀態後呼叫 Gemini，回傳 AI 回覆。

    Request JSON:
    {
        "messages": [{"role": "user", "content": "..."}, ...],
        "bmi_context": {          ← 可選，由網頁 calculateBMI() 後自動帶入
            "status": "過重",
            "bmi": "26.3",
            "idealWeight": "63.8"
        }
    }

    Response JSON:
    { "reply": "AI 回覆文字" }
    """
    data = request.get_json(silent=True)
    if not data or 'messages' not in data:
        return jsonify({"error": "缺少 messages 欄位"}), 400

    messages = data.get('messages', [])
    bmi_ctx  = data.get('bmi_context')   # 可能為 None（用戶尚未計算 BMI）

    # ── 組合系統提示 ──
    if bmi_ctx:
        system_prompt = f"""你是一位專業、親切、鼓勵性十足的健身新手顧問。

使用者目前資訊：
- BMI：{bmi_ctx.get('bmi', '未知')}
- 體位狀態：{bmi_ctx.get('status', '未知')}
- 理想體重：{bmi_ctx.get('idealWeight', '未知')} kg

回覆規則：
1. 針對使用者的體位狀態給出個人化建議，不要給通用答案。
2. 語氣溫暖、口語化，像朋友而非教科書。
3. 每次回覆控制在 150 字以內，新手不需要太多資訊。
4. 如果問題與健康無關，禮貌引導回健康話題。
5. 不要加 Markdown 格式符號（**、##），純文字即可。"""
    else:
        system_prompt = """你是一位專業、親切、鼓勵性十足的健身新手顧問。

回覆規則：
1. 語氣溫暖、口語化，像朋友而非教科書。
2. 每次回覆控制在 150 字以內，簡潔明瞭。
3. 如果問題與健康無關，禮貌引導回健康話題。
4. 不要加 Markdown 格式符號（**、##），純文字即可。

提示：鼓勵使用者先輸入身高體重，這樣你就能給更個人化的建議。"""

    # ── 把對話歷史轉成 Gemini 格式 ──
    # Gemini 的 role 只有 'user' 和 'model'（不是 'assistant'）
    try:
        gemini_history = []
        for msg in messages[:-1]:   # 最後一則由 send_message 傳
            role = 'model' if msg['role'] == 'assistant' else 'user'
            gemini_history.append({'role': role, 'parts': [msg['content']]})

        last_user_msg = messages[-1]['content'] if messages else ""

        # 建立含歷史的對話
        chat_session = model.start_chat(history=gemini_history)
        full_prompt = f"{system_prompt}\n\n用戶問題：{last_user_msg}"
        response = chat_session.send_message(full_prompt)
        reply_text = response.text.strip()

        return jsonify({"reply": reply_text})

    except Exception as e:
        print(f"Chat API Error: {e}")
        return jsonify({"reply": "服務稍忙，請稍後再試！"}), 500


# ==========================================
# 4. LINE Bot 訊息處理
# ==========================================
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

    # ── 關鍵字觸發 AI 建議 ──
    menu_keywords = ["飲食建議", "運動方案", "體位標準", "常見迷思破解", "身體活動指引"]
    if user_msg in menu_keywords:
        ai_reply = get_ai_advice(user_msg)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ai_reply))
        return

    # ── BMI 計算 ──
    try:
        parts = user_msg.replace('　', ' ').split()
        if len(parts) < 2:
            raise ValueError("參數不足")

        height = float(parts[0])
        weight = float(parts[1])

        if height <= 0 or weight <= 0:
            raise ValueError("數值無效")

        height_m = height / 100
        bmi = round(weight / (height_m ** 2), 1)
        ideal_weight = round(22 * (height_m ** 2), 1)
        weight_diff = round(weight - ideal_weight, 1)

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
        personalized_url = f"{MY_WEBSITE_URL}?h={height}&w={weight}&t={ideal_weight}"

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

        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="您的健康報告", contents=flex_content))

    except Exception as e:
        print(f"Error: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="💡 請輸入正確格式：身高 體重\n例如：175 70")
        )


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))