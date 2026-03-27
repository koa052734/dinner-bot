import os
import random
import json
import google.generativeai as genai
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# --- 設定（RenderのEnvironmentから読み込み） ---
YOUR_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
YOUR_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')

# ここで先に準備するから、さっきのエラーは消えます！
line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

def load_menu_data():
    with open('menu_data.json', 'r', encoding='utf-8') as f:
        return json.load(f)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text
    
    # データの読み込み
    try:
        data = load_menu_data()
        recipes = data["recipes"]
    except Exception as e:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="データの読み込みに失敗したわ。"))
        return

    # 1. 固定キーワード判定
    if "単品" in text:
        choices = [r["name"] for r in recipes if r["category"] == "単品"]
        reply = f"今日の単品は... 【 {random.choice(choices)} 】やで！"
        
    elif any(word in text for word in ["献立", "調理", "三菜"]):
        main_list = [r["name"] for r in recipes if r["category"] == "主菜"]
        side_list = [r["name"] for r in recipes if r["category"] == "副菜"]
        soup_list = [r["name"] for r in recipes if r["category"] == "汁物"]
        reply = f"本日の献立はこちら！\n【主菜】{random.choice(main_list)}\n【副菜1】{random.choice(side_list)}\n【汁物】{random.choice(soup_list)}"

    elif "手軽" in text:
        choices = [r["name"] for r in recipes if r["category"] == "手軽"]
        reply = f"お手軽に！ 【 {random.choice(choices)} 】や！"

# 2. AI食材検索モード（404エラーを物理的に回避する書き方）
    else:
        api_key = os.environ.get('GEMINI_API_KEY')
        try:
            genai.configure(api_key=api_key)
            
            # 修正ポイント：'models/' を含めず、かつ最新のフラッシュモデルを指定
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # AIへの命令（ここをシンプルにするのが一番エラーが出にくい）
            prompt = f"{text}を使って作れる料理名を1つだけ教えて。料理名のみ出力。"
            
            # 実行！
            response = model.generate_content(prompt)
            
            if response and response.text:
                reply = f"冷蔵庫にそれがあるんやな！\nなら【 {response.text.strip()} 】とかどう？"
            else:
                reply = "AIがちょっと言葉に詰まってるわ。もう一回送って！"
                
        except Exception as e:
            # まだエラーが出るなら、その正体を暴く（今度は 404 以外が出るはず）
            reply = f"デバッグ情報：{str(e)[:100]}"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
