import os
import google.generativeai as genai
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

@app.route("/", methods=['GET'])
def index():
    return "Bot is running!", 200

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
    try:
        # ★ここ！先頭に半角スペースが4つ入っているのが正解です
        model = genai.GenerativeModel('gemini-3-flash-preview')
        response = model.generate_content(f"食材「{text}」で作れる料理名を1つ。回答は料理名のみ。")
        reply = f"冷蔵庫にそれがあるんやな！\nなら【 {response.text.strip()} 】とかどう？"
    except Exception as e:
        reply = f"デバッグ情報：{str(e)[:50]}"
    
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
