import os
import random
import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# --- Renderの環境変数（Environment）から読み込む ---
# ここは書き換え不要です。Render側の設定が反映されます。
YOUR_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
YOUR_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

# --- データを読み込む関数（エラー対策済み） ---
def load_menu_data():
    # encoding='utf-8' を指定することで日本語文字化けを防ぎます
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
    
    # 1. データの読み込み
    try:
        data = load_menu_data()
        recipes = data["recipes"]
    except Exception as e:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="データ読み込みエラーや。JSONを確認してな。"))
        return

    # 2. 条件分岐（上から順番にチェック）
    
    # 【単品モード】
    if "単品" in text:
        choices = [r["name"] for r in recipes if r["category"] == "単品"]
        if choices:
            reply = f"今日の単品は... 【 {random.choice(choices)} 】やで！"
        else:
            reply = "ごめん、単品リストが空っぽやわ。"
        
    # 【一汁三菜モード】
    elif any(word in text for word in ["献立", "調理", "三菜"]):
        main_list = [r["name"] for r in recipes if r["category"] == "主菜"]
        side_list = [r["name"] for r in recipes if r["category"] == "副菜"]
        soup_list = [r["name"] for r in recipes if r["category"] == "汁物"]
        
        # リストが足りているか確認
        if main_list and len(side_list) >= 2 and soup_list:
            main = random.choice(main_list)
            sides = random.sample(side_list, 2)
            soup = random.choice(soup_list)
            reply = (f"本日の献立はこちら！\n"
                     f"【主菜】{main}\n"
                     f"【副菜1】{sides[0]}\n"
                     f"【副菜2】{sides[1]}\n"
                     f"【汁物】{soup}\n"
                     "しっかり食べてな！")
        else:
            reply = "献立を作るためのデータ（主菜・副菜・汁物）が足りへんみたいや。"

    # 【手軽モード】
    elif "手軽" in text:
        choices = [r["name"] for r in recipes if r["category"] == "手軽"]
        if choices:
            reply = f"お手軽に！ 【 {random.choice(choices)} 】や！"
        else:
            reply = "手軽なメニューがまだ登録されてへんわ。"

    # 【食材検索モード】（上のどれにも当てはまらない時）
    else:
        # tagsの中にユーザーが入力した文字が含まれている料理を探す
        matches = [r["name"] for r in recipes if text in r["tags"]]
        
        if matches:
            suggestion = random.choice(matches)
            reply = f"冷蔵庫に『{text}』があるんやな！\nそれなら【 {suggestion} 】とかどう？"
        else:
            reply = f"『{text}』を使ったレシピ、まだ俺のリストにないわ…メンボクナイ！\n「単品」とか「献立」って送ってみて！"

    # メッセージ送信
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

# --- Render用ポート設定 ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
