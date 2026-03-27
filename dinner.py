import os, random
import google.generativeai as genai
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# --- 1. パーツ別にバラバラにした具材リスト ---
PARTS = {
    "主菜": ["肉じゃが", "焼き鮭", "ハンバーグ", "唐揚げ", "鯖の味噌煮", "豚生姜焼き", "チキン南蛮", "回鍋肉", "とんかつ", "照り焼きチキン"],
    "副菜1": ["ほうれん草お浸し", "きんぴらごぼう", "ポテトサラダ", "千切りキャベツ", "ひじき煮", "マカロニサラダ", "タルタルソース", "春巻き", "筑前煮"],
    "副菜2": ["冷奴", "漬物", "コーン", "ポテト", "だし巻き卵", "トマト", "ブロッコリー", "きゅうり", "枝豆", "きんぴら"],
    "汁物": ["味噌汁", "豚汁", "コンソメスープ", "わかめスープ", "なめこ汁", "あおさ汁", "卵スープ", "中華スープ"]
}
# 単品・手軽・外食はそのまま
OTHER_LISTS = {
"単品": [
        "炒飯", "オムライス", "ナポリタン", "カルボナーラ", "牛丼", "カツ丼", 
        "親子丼", "ソース焼きそば", "塩焼きそば", "カレーうどん", 
        "明太パスタ", "ミートソース", "豚丼", "ビビンバ", "天津飯", "麻婆丼"
    ],
    "手軽": [
        "卵かけご飯", "納豆キムチ飯", "サバ缶キャベツ", "明太バターうどん", 
        "チーズカレー", "サラダチキン丼", "カップ麺", "ツナマヨ丼", 
        "麻婆豆腐", "茶漬け", "トースト", "冷凍ピザ"
    ],
    "外食": [
        "お好み焼き", "ラーメン", "寿司", "サイゼリヤ", "吉野家", 
        "マクドナルド", "ココイチ", "びっくりドンキー", "町中華", 
        "ガスト", "天下一品", "焼肉", "丸亀製麺", "すき家"
    ]
}
@app.route("/", methods=['GET'])
def index():
    return "Menu Shuffler Active", 200

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
    
    # --- 2. 「献立」の時だけ各パーツから1つずつランダム抽出 ---
    if text == "献立":
        s_sai = random.choice(PARTS["主菜"])
        f_sai1 = random.choice(PARTS["副菜1"])
        f_sai2 = random.choice(PARTS["副菜2"])
        shiru = random.choice(PARTS["汁物"])
        reply = f"今日の【献立】ガチャの結果です！\n\n【主菜】{s_sai}\n【副菜1】{f_sai1}\n【副菜2】{f_sai2}\n【汁物】{shiru}"

    # --- 3. 単品・手軽・外食の処理 ---
    elif text in OTHER_LISTS:
        menu = random.choice(OTHER_LISTS[text])
        reply = f"今日の【{text}】は【 {menu} 】で決まりですね！。"
    
    # --- 4. それ以外（食材）はAIが考える ---
    else:
        try:
            model = genai.GenerativeModel('gemini-3-flash-preview')
            prompt = f"食材「{text}」で、主菜、副菜2つ、汁物の献立。料理名のみを簡潔に回答して。"
            response = model.generate_content(prompt)
            reply = f"「{text}」でいくとこちらがおすすめですよ！\n\n{response.text.strip()}"
        except Exception as e:
            reply = f"エラー：{str(e)[:40]}"
    
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
