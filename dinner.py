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

  else:
        try:
            # AIへの指示をさらに強力にする
            prompt = f"「{text}」から料理の材料（名詞）を抜き出して。スペース区切りで、ひらがなと漢字の両方を出して。例：卵 たまご 豚肉。余計な説明は一切不要。"
            response = model.generate_content(prompt)
            keywords = response.text.strip().split()
            
            # 【重要】AIが何を抜き出したか、まずLINEで返信させる（デバッグ用）
            debug_msg = f"AI抽出ワード: {keywords}"
            
            matches = []
            for r in recipes:
                # 全タグを1つの文字列にして、キーワードが含まれるかチェック
                all_tags_str = "".join(r.get("tags", []))
                for kw in keywords:
                    if kw in all_tags_str:
                        matches.append(r["name"])
                        break
            
            if matches:
                suggestion = random.choice(list(set(matches)))
                reply = f"{debug_msg}\n\n冷蔵庫に『{text}』があるんやな！\nそれなら【 {suggestion} 】がおすすめや！"
            else:
                # ヒットしなかった場合、AIに直接「世の中のレシピ」を聞く
                fallback_prompt = f"「{text}」に含まれる食材を使って作れる一般的な料理名を1つだけ答えて。例：肉じゃが"
                ai_suggest = model.generate_content(fallback_prompt).text.strip()
                reply = f"{debug_msg}\n\n俺のリストにはなかったけど、AIいわく【 {ai_suggest} 】とかどう？"

        except Exception as e:
            reply = f"AIエラー発生: {str(e)}"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
