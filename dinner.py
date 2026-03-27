import os, random
import google.generativeai as genai
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# --- 1. 飾りを捨てた、純粋な料理名リスト ---
MENU_LIST = {
    "献立": [
        "【主菜】肉じゃが 【副菜】ほうれん草お浸し・冷奴 【汁物】味噌汁",
        "【主菜】焼き鮭 【副菜】きんぴらごぼう・漬物 【汁物】豚汁",
        "【主菜】ハンバーグ 【副菜】ポテサラ・コーン 【汁物】コンソメスープ",
        "【主菜】唐揚げ 【副菜】千切りキャベツ・ポテト 【汁物】わかめスープ",
        "【主菜】鯖の味噌煮 【副菜】ひじき煮・だし巻き卵 【汁物】なめこ汁",
        "【主菜】豚生姜焼き 【副菜】マカロニサラダ・トマト 【汁物】あおさ汁",
        "【主菜】チキン南蛮 【副菜】タルタル・ブロッコリー 【汁物】卵スープ",
        "【主菜】回鍋肉 【副菜】春巻き・きゅうり 【汁物】中華スープ"
    ],
    "単品": [
        "炒飯", "オムライス", "ナポリタン", "カルボナーラ", "牛丼", "カツ丼", 
        "親子丼", "ソース焼きそば", "塩焼きそば", "カレーうどん", 
        "明太パスタ", "ミートソース", "豚丼", "ビビンバ", "天津飯", "麻婆丼"
    ],
    "手軽": [
        "卵かけご飯", "納豆キムチ飯", "サバ缶キャベツ", "明太バターうどん", 
        "チーズカレー", "サラダチキン丼", "カップ麺", "ツナマヨ丼", 
        "麻婆豆腐", "茶漬け", "トースト", "冷凍ピザ"
    ],
    "外食": [
        "お好み焼き", "ラーメン", "寿司", "サイゼリヤ", "吉野家", 
        "マクドナルド", "ココイチ", "びっくりドンキー", "町中華", 
        "ガスト", "天下一品", "焼肉", "丸亀製麺", "すき家"
    ]
}
@app.route("/", methods=['GET'])
def index():
    return "Ready for Dinner!", 200

line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))
genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text
    
    # --- 2. 特定のキーワードならリストからランダム ---
    if text in MENU_LIST:
        menu = random.choice(MENU_LIST[text])
        if text == "献立":
            reply = f"今日のバッチリ【{text}】はこれです！\n\n{menu}"
        else:
            reply = f"今日の【{text}】は【 {menu} 】で決まりですね！"
    
    # --- 3. 食材ならAIが考える ---
    else:
        try:
            model = genai.GenerativeModel('gemini-3-flash-preview')
            # AIにも、食材から「定食セット」を考えさせる命令に変更！
            prompt = f"食材「{text}」を使って、主菜、副菜2つ、汁物の献立セットを考えて。回答は料理名のみを1行で。"
            response = model.generate_content(prompt)
            reply = f"「{text}」でいうとこれですかね！\n{response.text.strip()}"
        except Exception as e:
            reply = f"デバッグ情報：{str(e)[:40]}"
    
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
