import os, random
import google.generativeai as genai
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# --- 1. カテゴリ別のランダムリスト ---
MENU_LIST = {
    "献立": ["カレーライス", "肉じゃが", "ハンバーグ", "親子丼", "生姜焼き", "麻婆豆腐"],
    "単品": ["チャーハン", "オムライス", "パスタ", "うどん", "焼きそば", "丼もの"],
    "手軽": ["卵かけご飯", "納豆パスタ", "冷凍うどん", "サバ缶の和え物", "レトルトカレー"],
    "外食": ["お好み焼き（広島風！）", "ラーメン", "回転寿司", "ファミレス", "コンビニ弁当"]
}

@app.route("/", methods=['GET'])
def index():
    return "Ready!", 200

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
    reply = ""

    # --- 2. 特定のキーワード（献立・単品・手軽・外食）ならランダムに返す ---
    if text in MENU_LIST:
        menu = random.choice(MENU_LIST[text])
        reply = f"【{text}】やな！それなら【 {menu} 】はどう？"
    
    # --- 3. それ以外（食材など）ならAI（Gemini）が考える ---
    else:
        try:
            model = genai.GenerativeModel('gemini-3-flash-preview')
            response = model.generate_content(f"食材「{text}」で作れる料理名を1つ。回答は料理名のみ。")
            reply = f"冷蔵庫に「{text}」があるんやな！\nなら【 {response.text.strip()} 】とかどう？"
        except Exception as e:
            reply = f"デバッグ情報：{str(e)[:40]}"
    
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
