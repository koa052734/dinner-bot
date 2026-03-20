import os
import random
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# --- 合鍵はRenderの設定画面（Environment）から読み込む ---
YOUR_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
YOUR_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

# 献立データ（Yumaくんの全30種超えリストを完全反映！）
menu_simple = {
    "単品": ["カルボナーラ", "オムライス", "キーマカレー", "親子丼", "ガパオライス", "豚キムチ丼", "ソース焼きそば", "海老チャーハン", "照り焼きチキン丼", "ミートドリア", "ビビンバ", "ナポリタン", "冷やしうどん", "明太クリームパスタ", "牛丼", "タコライス", "上海焼きそば", "麻婆チャーハン", "ペペロンチーノ", "カツ丼", "ルーロー飯", "ジャージャー麺", "あんかけスパゲティ", "ドライカレー", "ロコモコ丼", "天津飯", "ソースカツ丼", "たらこスパゲティ", "ビビン麺", "焼きカレードリア"],
    "外食": ["サイゼリヤ", "スシロー", "マクドナルド", "吉野家", "丸亀製麺", "ガスト", "焼肉きんぐ", "ココイチ", "くら寿司", "天下一品", "大戸屋", "餃子の王将", "びっくりドンキー", "モスバーガー", "コメダ珈琲", "やよい軒", "はま寿司", "バーミヤン", "松屋", "ケンタッキー", "なか卯", "ジョイフル", "ロイヤルホスト", "いきなりステーキ", "かつや", "サブウェイ", "リンガーハット", "ジョリーパスタ", "てんや", "串カツ田中"],
    "手軽": ["冷凍パスタ", "カップヌードル", "セブンの金のピザ", "ファミマの汁なし担々麺", "スーパーのお寿司", "レトルトカレー", "冷凍餃子", "納豆ご飯と卵焼き", "サバ缶キャベツ和え", "冷凍うどん", "たまごかけご飯", "冷凍お好み焼き", "コンビニの弁当", "お茶漬け", "トーストと目玉焼き", "塩昆布パスタ", "サッポロ一番", "焼肉のタレTKG", "冷凍今川焼き", "コンビニおにぎり茶漬け"]
}

ichiju_sansai = {
    "主菜": ["鶏むね肉ステーキ", "サバの味噌煮", "豚バラ白菜", "鮭のムニエル", "ハンバーグ", "鶏の照り焼き", "白身魚のホイル焼き", "肉豆腐", "チキン南蛮", "肉じゃが", "エビチリ", "生姜焼き", "麻婆豆腐", "チキンカツ", "チンジャオロース", "ブリの照り焼き", "豚なす味噌炒め", "手羽元のさっぱり煮", "回鍋肉", "ささみチーズカツ", "カレイの煮付け", "八宝菜", "メンチカツ", "アジフライ", "照り焼きつくね", "鶏の唐揚げ", "肉巻きアスパラ", "厚揚げの肉挟み焼き", "ロールキャベツ", "赤魚の煮付け", "タンドリーチキン", "白菜と豚肉の重ね蒸し", "油淋鶏", "すき焼き風煮込み", "ポークチャップ"],
    "副菜": ["無限キャベツ", "冷奴", "ほうれん草のお浸し", "ちくわの磯辺揚げ", "たたききゅうり", "無限ピーマン", "小松菜のナムル", "ポテトサラダ", "きんぴらごぼう", "なすの揚げ浸し", "かぼちゃの煮物", "切り干し大根", "キャベツの塩昆布和え", "マカロニサラダ", "人参しりしり", "ブロッコリーの胡麻和え", "ジャーマンポテト", "もやしナムル", "筑前煮", "揚げ出し豆腐", "春雨サラダ", "ひじき煮", "長芋の梅和え", "コールスロー", "おから煮", "ピーマンの肉詰め", "アボカドのわさび醤油", "叩きごぼう", "里芋の煮転がし", "白和え"],
    "汁物": ["豆腐の味噌汁", "わかめスープ", "具だくさん豚汁", "オニオンスープ", "なめこの赤だし", "卵の中華スープ", "ベーコンコンソメスープ", "あおさの味噌汁", "ポトフ", "しじみ汁", "ミネストローネ", "きのこの豆乳スープ", "ワンタンスープ", "なすの味噌汁", "けんちん汁", "かきたま汁", "大根と油揚げの味噌汁", "コーンポタージュ", "春雨スープ", "里芋の味噌汁", "豚しゃぶスープ", "クラムチャウダー", "厚揚げの味噌汁", "わかめと胡麻のスープ", "トマトリゾット風スープ"]
}

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
    
    if "単品" in text:
        reply = f"今日の単品は... 【 {random.choice(menu_simple['単品'])} 】やで！"
    elif "外食" in text:
        reply = f"外食やな！オススメは... 【 {random.choice(menu_simple['外食'])} 】！"
    elif "手軽" in text:
        reply = f"お手軽に！ 【 {random.choice(menu_simple['手軽'])} 】や！"
    elif any(word in text for word in ["献立", "調理", "三菜"]):
        m = random.choice(ichiju_sansai["主菜"])
        s_list = random.sample(ichiju_sansai["副菜"], 2) # 被りなしで2つ選ぶ
        soup = random.choice(ichiju_sansai["汁物"])
        reply = (f"承知いたしました。本日のメニューはこちら\n"
                 f"【主菜】{m}\n"
                 f"【副菜1】{s_list[0]}\n"
                 f"【副菜2】{s_list[1]}\n"
                 f"【汁物】{soup}\n"
                 "お腹一杯になってくださいね！")
    else:
        reply = "「単品」「外食」「手軽」「献立」のどれか送ってみてな！"
        
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

# --- ここを修正 ---
if __name__ == "__main__":
    # Renderが指定するポート番号を読み込む。なければ10000を使う。
    port = int(os.environ.get("PORT", 10000))
    # hostを0.0.0.0にすることで、外部（LINE）からの接続を許可する
    app.run(host="0.0.0.0", port=port)
