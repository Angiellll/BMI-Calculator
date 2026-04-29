import os  # 匯入作業系統模組（讀取環境變數）
import pandas as pd  # 匯入 pandas（讀取 CSV）
import google.generativeai as genai  # 匯入 Gemini AI
from flask import Flask, request, abort  # Flask API
from linebot import LineBotApi, WebhookHandler  # LINE Bot SDK
from linebot.exceptions import InvalidSignatureError  # LINE 驗證錯誤
from linebot.models import MessageEvent, TextMessage, FlexSendMessage, TextSendMessage  # LINE 訊息類型
from dotenv import load_dotenv  # 讀取 .env

load_dotenv()  # 載入環境變數

app = Flask(__name__)  # 建立 Flask app

# ==========================================
# ⭐【新增】遊戲化資料（暫存用）
# ==========================================
users = {}  # 用 dictionary 存使用者狀態 {user_id: {level, exp, pet}}

# ==========================================
# 1. 配置金鑰
# ==========================================
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'), timeout=60)  # LINE API
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))  # Webhook handler

# 設定 Gemini AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))  # 設定 API key
model = genai.GenerativeModel(model_name='models/gemini-flash-lite-latest')  # 使用模型

# ★ 你的設定
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR3WLMM8SN9OmkMBf6y0zqMxBmq9LO7AUKToJn-UoRmYL4dStUpE6KPnzV2-ZDwD9B98sC4ymomsKH6/pub?gid=0&single=true&output=csv"
MY_WEBSITE_URL = "https://angiellll.github.io/BMI-Calculator/"

@app.route("/callback", methods=['POST'])  # LINE webhook 路徑
def callback():
    signature = request.headers['x-line-signature']  # 取得簽名
    body = request.get_data(as_text=True)  # 取得內容
    try:
        handler.handle(body, signature)  # 驗證並處理
    except InvalidSignatureError:
        abort(400)  # 驗證失敗
    return 'OK'

# ==========================================
# ⭐【新增】初始化使用者
# ==========================================
def init_user(user_id):  # 初始化函式
    if user_id not in users:  # 如果不存在
        users[user_id] = {  # 建立資料
            "level": 1,  # 等級
            "exp": 0,  # 經驗值
            "pet": "🌱 種子"  # 初始精靈
        }

# ==========================================
# ⭐【新增】加經驗 & 進化
# ==========================================
def add_exp(user_id, exp):  # 增加經驗
    users[user_id]["exp"] += exp  # 累加 EXP

    # 升級判斷
    while users[user_id]["exp"] >= 100:  # 每100升級
        users[user_id]["exp"] -= 100  # 扣掉
        users[user_id]["level"] += 1  # 等級+1

        # 進化系統（皮克敏風）
        if users[user_id]["level"] == 3:
            users[user_id]["pet"] = "🌿 嫩芽"
        elif users[user_id]["level"] == 5:
            users[user_id]["pet"] = "🧚 小精靈"
        elif users[user_id]["level"] == 8:
            users[user_id]["pet"] = "🌸 開花精靈"

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

def build_pet_flex_message(user):
    pet_name = user["pet"]
    pet_icon = pet_name.split()[0] if pet_name else "🌱"

    flex_content = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "我的小精靈", "weight": "bold", "size": "xl", "align": "center"},
                {"type": "text", "text": pet_icon, "size": "5xl", "align": "center", "margin": "md"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": f"等級：{user['level']}", "size": "md", "weight": "bold"},
                {"type": "text", "text": f"EXP：{user['exp']}/100", "size": "md", "margin": "sm"},
                {"type": "text", "text": f"夥伴：{pet_name}", "size": "md", "margin": "sm"}
            ]
        }
    }

    return FlexSendMessage(alt_text="我的小精靈", contents=flex_content)

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_msg = event.message.text.strip()  # 取得使用者訊息
    user_id = event.source.user_id  # ⭐ 取得 LINE 使用者ID

    init_user(user_id)  # ⭐ 初始化使用者

    # ==========================================
    # ⭐【新增】遊戲指令區
    # ==========================================

    # 查詢狀態
    if user_msg == "我的精靈":
        user = users[user_id]
        line_bot_api.reply_message(event.reply_token, build_pet_flex_message(user))
        return

    # 運動指令（例：運動 30）
    if user_msg.startswith("運動"):
        try:
            minutes = int(user_msg.split()[1])  # 取得分鐘
            gained = minutes * 10  # 每分鐘10 EXP
            add_exp(user_id, gained)  # 加經驗

            user = users[user_id]
            reply = f"🔥 運動 {minutes} 分鐘！\n+{gained} EXP\n目前等級：{user['level']}（{user['pet']}）"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
            return
        except:
            pass

    # 每日簽到
    if user_msg == "簽到":
        add_exp(user_id, 20)  # 給20 EXP
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 簽到成功！+20 EXP"))
        return

    # ==========================================
    # 原本功能（完全保留）
    # ==========================================

    menu_keywords = ["飲食建議", "運動方案", "體位標準", "常見迷思破解", "身體活動指引"]
    if user_msg in menu_keywords:
        ai_reply = get_ai_advice(user_msg)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ai_reply))
        return

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

        # ⭐【新增】BMI成功 → 給 EXP
        add_exp(user_id, 10)  # 計算一次給10 EXP

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
                    {"type": "text", "text": goal_text, "size": "sm", "color": "#666666", "wrap": True, "margin": "sm"}
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