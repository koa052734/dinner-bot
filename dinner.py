import os, random, json
import google.generativeai as genai
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# --- 1. 玄関（UptimeRobot用） ---
@app.route("/", methods=['GET'])
def index():
    return "OK", 200

# --- 2. 設定（環境変数から読み込み） ---
line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))
genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))

# --- 3. LINEからの窓口 ---
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# --- 4. AIの返信処理 ---
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text
    try:
        # 最新の安定モデルを指定
        model = genai.GenerativeModel('gemini-1.5-flash')
        # LINEの5秒ルールに間に合わせるため、超短く回答させる
        response = model.generate_content(f"食材「{text}」で料理名を1つ。回答は料理名のみ。")
        reply = f"冷蔵庫にそれがあるんやな！\nなら【 {response.text.strip()} 】とかどう？"
    except Exception as e:
        reply = f"デバッグ情報：{str(e)[:50]}"
    
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
