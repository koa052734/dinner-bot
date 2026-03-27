# --- (上略：importや設定はそのまま) ---

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text
    
    # 1. 固定キーワード判定（ここは爆速で返します）
    if "単品" in text:
        data = load_menu_data()
        choices = [r["name"] for r in recipes if r["category"] == "単品"]
        reply = f"今日の単品は... 【 {random.choice(choices)} 】やで！"
        
    elif any(word in text for word in ["献立", "調理", "三菜"]):
        data = load_menu_data()
        recipes = data["recipes"]
        main_list = [r["name"] for r in recipes if r["category"] == "主菜"]
        side_list = [r["name"] for r in recipes if r["category"] == "副菜"]
        soup_list = [r["name"] for r in recipes if r["category"] == "汁物"]
        reply = f"本日の献立はこちら！\n【主菜】{random.choice(main_list)}\n【副菜1】{random.choice(side_list)}\n【汁物】{random.choice(soup_list)}"

    elif "手軽" in text:
        data = load_menu_data()
        choices = [r["name"] for r in recipes if r["category"] == "手軽"]
        reply = f"お手軽に！ 【 {random.choice(choices)} 】や！"

    # 2. ★ここが重要！それ以外の言葉（たまご等）が来たら「全部AIに任せる」
    else:
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            reply = "【エラー】Renderの環境変数にGEMINI_API_KEYが入ってへんよ！"
        else:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # AIに料理名を1つだけ出させる（超シンプルに）
                prompt = f"「{text}」を使って作れる料理名を1つだけ教えて。挨拶抜きで料理名のみ。例：オムレツ"
                response = model.generate_content(prompt)
                ai_suggest = response.text.strip()
                
                reply = f"冷蔵庫にそれがあるんやな！\nなら【 {ai_suggest} 】とかどう？"
            
            except Exception as e:
                # ここでエラーが出たらAI通信の問題
                reply = f"AIがちょっと風邪気味やわ（エラー：{str(e)}）"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

# --- (下略：if __name__ == "__main__": はそのまま) ---

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
