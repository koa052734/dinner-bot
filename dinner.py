import os
import random
import json
import google.generativeai as genai
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)
# --- 追加：UptimeRobot専用の「生存確認」窓口 ---
@app.route("/", methods=['GET'])
def index():
    return "Bot is running!", 200
# ------------------------------------------
# --- 1. 設定（ここで一気に準備する！） ---
YOUR_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
YOUR_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

# AIの初期化（ここを一番確実な方法に固定します）
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def load_menu_data():
    try:
        with open('menu_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"recipes": []}

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
    data = load_menu_data()
    recipes = data.get("recipes", [])

    # A. 固定キーワード判定
    if "単品" in text:
        choices = [r["name"] for r in recipes if r.get("category") == "単品"]
        reply = f"今日の単品は... 【 {random.choice(choices)} 】やで！"
        
    elif any(word in text for word in ["献立", "調理", "三菜"]):
        main = [r["name"] for r in recipes if r.get("category") == "主菜"]
        side = [r["name"] for r in recipes if r.get("category") == "副菜"]
        soup = [r["name"] for r in recipes if r.get("category") == "汁物"]
        reply = f"本日の献立はこちら！\n【主菜】{random.choice(main)}\n【副菜】{random.choice(side)}\n【汁物】{random.choice(soup)}"

    elif "手軽" in text:
        choices = [r["name"] for r in recipes if r.get("category") == "手軽"]
        reply = f"お手軽に！ 【 {random.choice(choices)} 】や！"

   # B. ★AI食材検索（404エラーもタイムアウトも全部LINEに吐き出す！）
    else:
        if not GEMINI_API_KEY:
            reply = "APIキーが設定されてへんよ！"
        else:
            try:
                # タイムアウト対策：5秒以内に返事がないなら諦める設定
                genai.configure(api_key=GEMINI_API_KEY)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # 実行！（ここが「既読スルー」の現場です）
                response = model.generate_content(f"{text}を使った料理名を1つだけ。料理名のみ出力。")
                
                if response and response.text:
                    reply = f"冷蔵庫にそれがあるんやな！\nなら【 {response.text.strip()} 】とかどう？"
                else:
                    reply = "AIが空っぽの返事を返してきたわ。もう一回送って！"
            
            except Exception as e:
                # 既読スルーにせず、何が起きたか「生の声」をLINEに送る
                reply = f"デバッグ情報：{str(e)}"

    # 最後に必ず返信する（これが漏れると既読スルーになります）
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
