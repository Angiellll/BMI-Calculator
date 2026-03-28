import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, FlexSendMessage, TextSendMessage
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['x-line-signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    try:
        # 解析輸入：身高 體重 (例如 175 70)
        height, weight = map(float, msg.split())
        
        # 核心計算邏輯 (移植自你的 JS)
        height_m = height / 100
        bmi = round(weight / (height_m ** 2), 1)
        ideal_weight = round(22 * (height_m ** 2), 1)
        weight_diff = round(weight - ideal_weight, 1)

        # 建議數據庫
        if bmi < 18.5:
            status, color = "體重過輕", "#4a90e2"
            diet = "多攝取優質蛋白質（如雞腿肉、豆腐、豆漿），並適量增加總熱量攝取。"
            outdoor = "🏋️ 進行基礎重訓器材操作，如腿推機、拉背機，有助於增肌。"
            home = "🏠 伏地挺身、自重深蹲（每次 12 下，做 4 組），利用水瓶做側平舉。"
        elif bmi < 24:
            status, color = "正常範圍", "#2ecc71"
            diet = "恭喜維持！請繼續保持原型食物、多喝水，避免過多加工零食。"
            outdoor = "🏃 慢跑、騎自行車或快走 30 分鐘，維持優良心肺功能。"
            home = "🏠 瑜珈伸展、Tabata 高強度間歇運動或跳繩。"
        elif bmi < 27:
            status, color = "過重", "#f1c40f"
            diet = "減少含糖飲料與宵夜。嘗試 168 斷食法，將碳水化合物比例降低。"
            outdoor = "🚴 每週 3 次 40 分鐘的快走或輕快慢跑，增加熱量消耗。"
            home = "🏠 開合跳、波比跳 (Burpees) 每組 20 下，循環 5 組。"
        else:
            status, color = "肥胖", "#e74c3c"
            diet = "建議諮詢營養師。嚴格控制油脂與醣類，增加蔬菜纖維，提升飽足感。"
            outdoor = "🏊 游泳、水中行走或使用橢圓機，能燃脂並保護膝關節。"
            home = "🏠 超慢跑 (原地進行) 20 分鐘，或扶著椅子進行深蹲訓練。"

        goal_text = f"理想體重 {ideal_weight}kg。{'尚需減少 ' + str(weight_diff) + 'kg' if weight_diff > 0 else '目前非常苗條！'}"

        # 組合 LINE Flex Message (比照網頁 UI 設計)
        flex_message = {
            "type": "bubble",
            "header": {
                "type": "box", "layout": "vertical", "contents": [
                    {"type": "text", "text": "健康管理報告", "weight": "bold", "size": "xl", "color": "#333333"},
                    {"type": "text", "text": str(bmi), "weight": "bold", "size": "5xl", "color": color, "margin": "md"},
                    {"type": "text", "text": f"狀態：{status}", "size": "md", "color": color, "weight": "bold"}
                ], "alignItems": "center"
            },
            "body": {
                "type": "box", "layout": "vertical", "contents": [
                    {"type": "separator", "margin": "md"},
                    {"type": "text", "text": "🎯 管理目標", "weight": "bold", "margin": "lg"},
                    {"type": "text", "text": goal_text, "size": "sm", "color": "#666666", "wrap": True},
                    {"type": "text", "text": "🍎 飲食建議", "weight": "bold", "margin": "lg"},
                    {"type": "text", "text": diet, "size": "sm", "color": "#666666", "wrap": True},
                    {"type": "text", "text": "🌲 運動方案", "weight": "bold", "margin": "lg"},
                    {"type": "text", "text": f"{outdoor}\n{home}", "size": "sm", "color": "#666666", "wrap": True}
                ]
            }
        }
        
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="您的健康報告已生成", contents=flex_message))

    except Exception as e:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="💡 請輸入正確格式：身高 體重\n例如：175 70"))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)