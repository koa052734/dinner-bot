import os
import random
import json
import google.generativeai as genai  # AIライブラリを追加
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# --- 設定（環境変数から読み込み） ---
YOUR_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
YOUR_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

# Geminiの設定
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

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
    data = load_menu_data()
    recipes = data["recipes"]
    
    # 1. 固定キーワード判定（ここはAIを通さず高速反応）
    if "単品" in text:
        choices = [r["name"] for r in recipes if r["category"] == "単品"]
        reply = f"今日の単品は... 【 {random.choice(choices)} 】やで！"
        
    elif any(word in text for word in ["献立", "調理", "三菜"]):
        main = random.choice([r["name"] for r in recipes if r["category"] == "主菜"])
        sides = random.sample([r["name"] for r in recipes if r["category"] == "副菜"], 2)
        soup = random.choice([r["name"] for r in recipes if r["category"] == "汁物"])
        reply = (f"本日の献立はこちら！\n【主菜】{main}\n【副菜1】{sides[0]}\n【副菜2】{sides[1]}\n【汁物】{soup}")

    elif "手軽" in text:
        choices = [r["name"] for r in recipes if r["category"] == "手軽"]
        reply = f"お手軽に！ 【 {random.choice(choices)} 】や！"

   # 2. 【AIモード】
    else:
        try:
            # AIへの頼み方をさらにシンプルに
            prompt = f"「{text}」という文章から、料理の材料（名詞）を抜き出して。スペース区切りで、ひらがなと漢字の両方を出して。例：卵 たまご 豚肉。余計な説明は禁止。"
            response = model.generate_content(prompt)
            keywords = response.text.strip().split()
            
            # デバッグ用：AIが何を抜き出したかLINEで教えてくれるようにする（後で消してOK）
            # line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"AI抽出: {keywords}"))

            matches = []
            for r in recipes:
                # レシピの全タグを1つの長い文字列にする
                all_tags_str = "".join(r.get("tags", []))
                
                # AIが抜いたキーワードのどれか1つでも、タグのどこかに含まれてればOK！
                for kw in keywords:
                    if kw in all_tags_str or all_tags_str in kw:
                        matches.append(r["name"])
                        break # 1つ見つかればその料理は採用
            
            if matches:
                suggestion = random.choice(list(set(matches))) # 重複排除
                reply = f"AIの分析：『{text}』には「{'・'.join(set(keywords))}」が入ってるな！\nそれなら【 {suggestion} 】がええと思うで！"
            else:
                # 何もヒットしなかった時、AIに直接「何が作れるか」聞いちゃう最終手段
                prompt_fallback = f"「{text}」にある食材を使って作れる一般的な料理名を1つだけ答えて。例：肉じゃが"
                ai_suggest = model.generate_content(prompt_fallback).text.strip()
                reply = f"俺のリストにはなかったけど、AIいわく【 {ai_suggest} 】とかどうや？\n（「献立」って送ればセットも出すで！）"

        except Exception as e:
            reply = "AIがちょっと迷子やわ。もう一回短く送ってみて！"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
