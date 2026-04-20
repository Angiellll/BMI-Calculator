import os
import json
import gspread
import pandas as pd
import google.generativeai as genai
from datetime import datetime
from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, FlexSendMessage, TextSendMessage
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'), timeout=60)
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(model_name='models/gemini-flash-lite-latest')

SHEET_CSV_URL = os.getenv('SHEET_CSV_URL')  # 原本的試算表 CSV 網址放進 .env
MY_WEBSITE_URL = "https://angiellll.github.io/BMI-Calculator/"

# ── Google Sheets 寫入設定 ────────────────────────────────────────────────────
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_challenge_sheet():
    creds = Credentials.from_service_account_file('service_account.json', scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(os.getenv('SPREADSHEET_ID'))
    return sh.worksheet('challenge_progress')

# ── 週任務內容（與網頁一致）─────────────────────────────────────────────────
WEEK_TASKS = {
    'gain': [
        ["早餐增加一份蛋白質（如雞蛋、豆漿）", "訓練：做 3 組深蹲，每組 12 下", "睡前喝一杯溫牛奶補充熱量"],
        ["每餐加入手掌大小的蛋白質來源", "訓練：伏地挺身 + 弓箭步各 4 組", "記錄今日的訓練負重數字"],
        ["進行力竭訓練，每組做到撐不住為止", "增加一餐高碳水的點心（如香蕉、地瓜）", "睡前做 5 分鐘靜態伸展放鬆"],
        ["用最重的重量完成一次完整訓練", "測量體重並與第一天比較", "今天好好犒賞自己，充足休息"],
    ],
    'lose': [
        ["今天喝 2000ml 以上的水", "戒除一杯含糖飲料，改喝無糖飲品", "餐前 10 分鐘先喝一杯水再吃飯"],
        ["今天做 20 分鐘有氧運動（快走/跳繩）", "晚餐吃五分飽，減少精緻澱粉", "記錄今日吃了哪些讓你後悔的食物"],
        ["完成一次 HIIT 訓練（20 分鐘）", "晚餐不吃白飯，改為地瓜或糙米", "睡覺前不吃任何東西"],
        ["測量體重並與第一天比較", "制定下個月的維持計畫", "今天好好犒賞自己（健康的方式）"],
    ]
}

# ── /sync_challenge：接收網頁打卡資料 ────────────────────────────────────────
@app.route("/sync_challenge", methods=['POST', 'OPTIONS'])
def sync_challenge():
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    if request.method == 'OPTIONS':
        return ('', 204, headers)

    data = request.get_json()
    user_id = data.get('userId')
    challenge_data = data.get('challengeData')

    if not user_id or not challenge_data:
        return jsonify({'error': 'missing data'}), 400, headers

    try:
        ws = get_challenge_sheet()
        row_data = [
            user_id,
            challenge_data.get('type', ''),
            json.dumps(challenge_data.get('completedDays', []), ensure_ascii=False),
            json.dumps(challenge_data.get('taskChecks', {}), ensure_ascii=False),
            challenge_data.get('startDate', ''),
            datetime.now().isoformat()
        ]
        try:
            cell = ws.find(user_id)
            ws.update(f'A{cell.row}:F{cell.row}', [row_data])
        except Exception:
            ws.append_row(row_data)

        return jsonify({'status': 'ok'}), 200, headers
    except Exception as e:
        print(f"Sync error: {e}")
        return jsonify({'error': str(e)}), 500, headers

# ── 查詢挑戰進度 ──────────────────────────────────────────────────────────────
def get_challenge_progress(user_id):
    try:
        ws = get_challenge_sheet()
        cell = ws.find(user_id)
        if not cell:
            return None
        row = ws.row_values(cell.row)
        return {
            'type':         row[1],
            'completedDays': json.loads(row[2]) if row[2] else [],
            'taskChecks':   json.loads(row[3]) if row[3] else {},
            'startDate':    row[4]
        }
    except Exception as e:
        print(f"Get progress error: {e}")
        return None

# ── 建立進度 Flex Message ─────────────────────────────────────────────────────
def build_progress_flex(progress):
    challenge_type  = progress['type']
    completed_days  = progress['completedDays']
    task_checks     = progress['taskChecks']
    today           = datetime.now().strftime('%Y-%m-%d')

    plan_name  = "💪 30天增肌增重挑戰" if challenge_type == 'gain' else "🔥 30天燃脂瘦身挑戰"
    plan_color = "#e67e22"             if challenge_type == 'gain' else "#e74c3c"

    total_done  = len(completed_days)
    week_index  = min(total_done // 7, 3)
    done_today  = today in completed_days

    # 連續打卡天數
    streak = 0
    check  = datetime.now()
    for _ in range(31):
        dk = check.strftime('%Y-%m-%d')
        if dk in completed_days:
            streak += 1
            check  = check.replace(day=check.day - 1)
        else:
            break

    # 今日任務狀態
    tasks        = WEEK_TASKS[challenge_type][week_index]
    today_checks = task_checks.get(today, [])

    if done_today:
        status_text  = "✅ 今日已打卡完成！"
        status_color = "#27ae60"
    elif today_checks:
        done_count   = sum(1 for c in today_checks if c)
        status_text  = f"📋 今日進度：{done_count}/{len(tasks)} 項完成"
        status_color = "#f39c12"
    else:
        status_text  = "📋 今日尚未開始任務"
        status_color = "#aaaaaa"

    # 任務列表
    task_rows = []
    for i, task in enumerate(tasks):
        checked = done_today or (i < len(today_checks) and today_checks[i])
        task_rows.append({
            "type": "box", "layout": "horizontal",
            "contents": [
                {"type": "text", "text": "✅" if checked else "⬜",
                 "flex": 0, "size": "sm"},
                {"type": "text", "text": task, "size": "sm", "wrap": True,
                 "color": "#27ae60" if checked else "#999999",
                 "margin": "sm", "flex": 1}
            ], "margin": "sm"
        })

    week_labels = {
        'gain': ["第一週：基礎適應","第二週：肌力建構","第三週：負荷強化","第四週：成果驗收"],
        'lose': ["第一週：代謝喚醒","第二週：主動燃脂","第三週：體能突破","第四週：體質鞏固"]
    }

    return {
        "type": "bubble", "size": "mega",
        "header": {
            "type": "box", "layout": "vertical",
            "backgroundColor": plan_color, "paddingAll": "20px",
            "contents": [
                {"type": "text", "text": plan_name,
                 "weight": "bold", "size": "lg", "color": "#ffffff"},
                {"type": "text",
                 "text": week_labels[challenge_type][week_index],
                 "size": "sm", "color": "rgba(255,255,255,0.75)", "margin": "sm"}
            ]
        },
        "body": {
            "type": "box", "layout": "vertical", "paddingAll": "20px",
            "contents": [
                {
                    "type": "box", "layout": "horizontal",
                    "paddingBottom": "16px",
                    "contents": [
                        {"type": "box", "layout": "vertical", "flex": 1, "contents": [
                            {"type": "text", "text": str(total_done),
                             "weight": "bold", "size": "3xl",
                             "color": plan_color, "align": "center"},
                            {"type": "text", "text": "已完成天",
                             "size": "xs", "color": "#999999", "align": "center"}
                        ]},
                        {"type": "separator"},
                        {"type": "box", "layout": "vertical", "flex": 1, "contents": [
                            {"type": "text", "text": str(streak),
                             "weight": "bold", "size": "3xl",
                             "color": "#f1c40f", "align": "center"},
                            {"type": "text", "text": "連續打卡",
                             "size": "xs", "color": "#999999", "align": "center"}
                        ]},
                        {"type": "separator"},
                        {"type": "box", "layout": "vertical", "flex": 1, "contents": [
                            {"type": "text", "text": str(30 - total_done),
                             "weight": "bold", "size": "3xl",
                             "color": "#95a5a6", "align": "center"},
                            {"type": "text", "text": "剩餘天數",
                             "size": "xs", "color": "#999999", "align": "center"}
                        ]}
                    ]
                },
                {"type": "separator"},
                {"type": "text", "text": "今日任務",
                 "weight": "bold", "size": "md", "margin": "lg"},
                {"type": "text", "text": status_text,
                 "size": "sm", "color": status_color, "margin": "sm"},
                *task_rows
            ]
        },
        "footer": {
            "type": "box", "layout": "vertical", "paddingAll": "16px",
            "contents": [{
                "type": "button", "style": "primary", "color": plan_color,
                "action": {
                    "type": "uri",
                    "label": "前往網頁打卡",
                    "uri": MY_WEBSITE_URL
                }
            }]
        }
    }

# ── LINE Webhook ──────────────────────────────────────────────────────────────
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
        if row.empty:
            return f"抱歉，目前找不到「{category}」的相關指引。"
        official_text = row['Content'].values[0]
        ref_link      = row['Reference_Link'].values[0]
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
    user_id  = event.source.user_id

    # 查詢挑戰進度
    if user_msg in ["查詢進度", "我的挑戰", "挑戰進度", "進度查詢"]:
        progress = get_challenge_progress(user_id)
        if not progress:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"目前尚無挑戰記錄！\n請先到網頁開始你的30天挑戰 👉 {MY_WEBSITE_URL}"
                )
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                FlexSendMessage(
                    alt_text="您的挑戰進度",
                    contents=build_progress_flex(progress)
                )
            )
        return

    # 圖文選單關鍵字
    menu_keywords = ["飲食建議", "運動方案", "體位標準", "常見迷思破解", "身體活動指引"]
    if user_msg in menu_keywords:
        ai_reply = get_ai_advice(user_msg)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ai_reply))
        return

    # BMI 計算
    try:
        parts  = user_msg.replace('　', ' ').split()
        if len(parts) < 2:
            raise ValueError("參數不足")
        height = float(parts[0])
        weight = float(parts[1])
        if height <= 0 or weight <= 0:
            raise ValueError("數值無效")

        height_m     = height / 100
        bmi          = round(weight / (height_m ** 2), 1)
        ideal_weight = round(22 * (height_m ** 2), 1)
        weight_diff  = round(weight - ideal_weight, 1)

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

        goal_text        = f"理想體重 {ideal_weight}kg。{'尚需減少 ' + str(weight_diff) + 'kg' if weight_diff > 0 else '繼續保持！'}"
        personalized_url = f"{MY_WEBSITE_URL}?h={height}&w={weight}&t={ideal_weight}"

        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "健康報告單",
                     "weight": "bold", "size": "xl", "color": "#333333"},
                    {"type": "text", "text": str(bmi),
                     "weight": "bold", "size": "5xl", "color": color, "margin": "md"},
                    {"type": "text", "text": f"狀態：{status}",
                     "size": "md", "color": color, "weight": "bold"}
                ],
                "alignItems": "center", "paddingTop": "20px"
            },
            "body": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {"type": "separator", "margin": "md"},
                    {"type": "text", "text": "🎯 管理目標",
                     "weight": "bold", "margin": "lg", "size": "md"},
                    {"type": "text", "text": goal_text,
                     "size": "sm", "color": "#666666", "wrap": True, "margin": "sm"},
                    {"type": "text", "text": "🍎 飲食建議",
                     "weight": "bold", "margin": "lg", "size": "md"},
                    {"type": "text", "text": diet,
                     "size": "sm", "color": "#666666", "wrap": True, "margin": "sm"},
                    {"type": "text", "text": "🌲 運動方案",
                     "weight": "bold", "margin": "lg", "size": "md"},
                    {"type": "box", "layout": "vertical", "margin": "sm",
                     "contents": [
                         {"type": "text", "text": f"戶外：{outdoor}",
                          "size": "sm", "color": "#666666", "wrap": True},
                         {"type": "text", "text": f"室內：{home}",
                          "size": "sm", "color": "#666666", "wrap": True, "margin": "xs"}
                     ]}
                ]
            },
            "footer": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {
                        "type": "button", "style": "primary", "color": "#4a90e2",
                        "action": {
                            "type": "uri",
                            "label": "瀏覽個人化詳細報告",
                            "uri": personalized_url
                        }
                    },
                    # ★ 新增：查詢挑戰進度的小按鈕
                    {
                        "type": "button", "style": "secondary",
                        "margin": "sm",
                        "action": {
                            "type": "message",
                            "label": "📊 查詢挑戰進度",
                            "text": "查詢進度"
                        }
                    }
                ],
                "paddingAll": "20px"
            }
        }

        if height == 175.0 and weight == 70.0:
            line_bot_api.reply_message(event.reply_token, [
                TextSendMessage(text="📊 這是計算範例說明：\n請依照「身高 體重」格式輸入即可！"),
                FlexSendMessage(alt_text="您的健康報告", contents=flex_content)
            ])
        else:
            line_bot_api.reply_message(
                event.reply_token,
                FlexSendMessage(alt_text="您的健康報告", contents=flex_content)
            )

    except Exception as e:
        print(f"Error: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="💡 請輸入正確格式：身高 體重\n例如：175 70\n（注意中間要有空格喔！）")
        )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))