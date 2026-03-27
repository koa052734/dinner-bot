import os, random
import google.generativeai as genai
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# --- 1. 爆盛り＆フルセットのリスト ---
MENU_LIST = {
    "献立": [
        "【主菜】肉じゃが 【副菜1】ほうれん草のお浸し 【副菜2】冷奴 【汁物】味噌汁",
        "【主菜】焼き魚（鮭） 【副菜1】きんぴらごぼう 【副菜2】漬物 【汁物】豚汁",
        "【主菜】ハンバーグ 【副菜1】ポテトサラダ 【副菜2】コーンスープ 【汁物】コンソメスープ",
        "【主菜】鶏の唐揚げ 【副菜1】キャベツの千切り 【副菜2】ポテトフライ 【汁物】わかめスープ",
        "【主菜】鯖の味噌煮 【副菜1】ひじきの煮物 【副菜2】だし巻き卵 【汁物】なめこの味噌汁",
        "【主菜】生姜焼き 【副菜1】マカロニサラダ 【副菜2】トマトスライス 【汁物】あおさ汁"
    ],
    "単品": ["オムライス", "炒飯", "カルボナーラパスタ", "カツ丼", "牛丼", "ソース焼きそば", "カレーうどん", "ミートソーススパゲティ", "親子丼"],
    "手軽": ["卵かけご飯", "納豆キムチご飯",  "冷凍うどん", "レトルトカレー＆チーズ", "サラダチキン丼", "カップヌードル背徳飯"],
    "外食": ["お好み焼き", "魚介系醤油ラーメン", "回転寿司", "サイゼリヤ", "吉野家", "マクドナルド", "近所の居酒屋", "焼肉屋", "ココイチ"]
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
