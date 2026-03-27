import os, random, json, threading, time, requests
import google.generativeai as genai
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# --- 【新機能】自分自身を叩き起こし続ける「セルフ・ノック」 ---
def keep_alive():
    while True:
        try:
            # 自分自身のURLを5分ごとに叩く
            requests.get("https://dinner-bot.onrender.com/")
        except:
            pass
        time.sleep(300) # 300秒（5分）おき

# サーバー起動時に、別スレッドで「不眠タイマー」を開始
threading.Thread(target=keep_alive, daemon=True).start()

@app.route("/", methods=['GET'])
def index():
    return "Bot is awake!", 200

# --- 以下、設定（ここは今まで通り） ---
YOUR_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
YOUR_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

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
        model = genai.GenerativeModel('gemini-1.5-flash')
        # 応答を極限まで短くして、LINEのタイムアウト（5秒）を回避！
        response = model.generate_content(f"食材「{text}」で作れる料理名を1つだけ。回答は料理名のみ。")
        reply = f"冷蔵庫にそれがあるんやな！\nなら【 {response.text.strip()} 】とかどう？"
    except Exception as e:
        reply = f"デバッグ情報：{str(e)[:50]}"
    
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
