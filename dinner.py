import os
import random
import json
import google.generativeai as genai
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

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

    # B. ★AI食材検索（404エラーを物理的に回避する最新ルート）
    else:
        if not GEMINI_API_KEY:
            reply = "APIキーが設定されてへんよ！"
        else:
            try:
                # モデルの指定から 'models/' を完全に排除して直接指定
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # AIへの命令（プロンプト）をさらに短くしてタイムアウト回避
                prompt = f"食材「{text}」で作れる料理名を1つ。料理名のみ出力。"
                
                # AIに聞く（ここでエラーが出たら except に飛ぶ）
                response = model.generate_content(prompt)
                
                if response and response.text:
                    ai_suggest = response.text.strip()
                    reply = f"冷蔵庫にそれがあるんやな！\nなら【 {ai_suggest} 】とかどう？"
                else:
                    reply = "AIがちょっと考え込んでるわ。もう一回送って！"
            
            except Exception as e:
                # 404エラーが出る場合は、ここが反応します
                error_msg = str(e)
                if "404" in error_msg:
                    reply = "AIモデルの準備中やわ。3分後にまた送ってみて！"
                else:
                    reply = f"AI通信エラー：{error_msg[:50]}"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
