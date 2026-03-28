import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, FlexSendMessage, TextSendMessage
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# 從環境變數取得金鑰
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
    user_msg = event.message.text.strip()

    # ==========================================
    # 區塊 C：飲食指南 (根據國健署官方手冊內容)
    # ==========================================
    if user_msg == "飲食建議":
        diet_info = (
            "🥗 【國健署：每日飲食指南精華】\n\n"
            "掌握「我的餐盤」聰明吃：\n"
            "1. 每天早晚一棵奶 (補鈣)\n"
            "2. 每餐水果拳頭大\n"
            "3. 菜比水果多一點\n"
            "4. 飯跟蔬菜一樣多\n"
            "5. 豆魚蛋肉一掌心\n"
            "6. 堅果種子一茶匙\n\n"
            "💡 建議優先選擇全穀雜糧，並以白肉取代紅肉喔！"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=diet_info))
        return

    # ==========================================
    # 區塊 D：開發者資訊 (聯絡我)
    # ==========================================
    elif user_msg == "開發者資訊":
        dev_info = (
            "👨‍💻 【關於開發者】\n\n"
            "這是一款結合資管專業與健康科技的 AI 顧問。\n"
            "開發者：Angie (資管系)\n"
            "專案名稱：BMI-Calculator Project\n\n"
            "目標是透過科技縮短資訊落差，讓健康管理更簡單！"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=dev_info))
        return

    # ==========================================
    # 區塊 A & 一般輸入：BMI 計算邏輯
    # ==========================================
    else:
        try:
            # 如果是點擊 A 區塊的範例 "175 70"
            is_example = (user_msg == "175 70")
            
            # 解析輸入：身高 體重
            height, weight = map(float, user_msg.split())
            
            # 計算邏輯
            height_m = height / 100
            bmi = round(weight / (height_m ** 2), 1)
            ideal_weight = round(22 * (height_m ** 2), 1)
            weight_diff = round(weight - ideal_weight, 1)

            # 根據 BMI 分類建議
            if bmi < 18.5:
                status, color = "體重過輕", "#4a90e2"
                diet = "多攝取優質蛋白質（如雞胸肉、豆漿），增加總熱量攝取。"
                outdoor = "🏋️ 進行基礎重訓，如腿推機、拉背機，有助於增肌。"
                home = "🏠 伏地挺身、自重深蹲（每次 12 下，做 4 組）。"
            elif bmi < 24:
                status, color = "正常範圍", "#2ecc71"
                diet = "恭喜維持！請繼續保持原型食物、多喝水，避免過多加工品。"
                outdoor = "🏃 慢跑、騎自行車或快走 30 分鐘，維持心肺功能。"
                home = "🏠 瑜珈伸展、Tabata 高強度間歇運動。"
            elif bmi < 27:
                status, color = "過重", "#f1c40f"
                diet = "減少含糖飲料與宵夜。嘗試 168 斷食法，降低碳水比例。"
                outdoor = "🚴 每週 3 次 40 分鐘快走，增加熱量消耗。"
                home = "🏠 開合跳、波比跳 (Burpees) 每組 20 下，循環 5 組。"
            else:
                status, color = "肥胖", "#e74c3c"
                diet = "建議諮詢營養師。嚴格控制油脂與醣類，增加蔬菜纖維。"
                outdoor = "🏊 游泳、水中行走或使用橢圓機，保護膝關節。"
                home = "🏠 超慢跑 20 分鐘，或扶著椅子進行深蹲訓練。"

            goal_text = f"理想體重 {ideal_weight}kg。{'尚需減少 ' + str(weight_diff) + 'kg' if weight_diff > 0 else '目前非常苗條！'}"

            # 建立 Flex Message
            flex_content = {
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

            # 如果是點擊範例按鈕，多噴一段文字提示
            if is_example:
                line_bot_api.reply_message(event.reply_token, [
                    TextSendMessage(text="📊 這是計算範例說明：\n請依照「身高 體重」格式輸入即可！"),
                    FlexSendMessage(alt_text="您的健康報告已生成", contents=flex_content)
                ])
            else:
                line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="您的健康報告已生成", contents=flex_content))

        except Exception:
            # 使用者亂打字時的提示
            line_bot_api.reply_message(
                event.reply_token, 
                TextSendMessage(text="💡 請輸入正確格式：身高 體重\n例如：175 70\n或點擊選單查看範例！")
            )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)