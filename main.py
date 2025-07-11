def main():
    bot_token = os.getenv('BOT_TOKEN')
    chat_id = os.getenv('CHAT_ID')

    if not bot_token or not chat_id:
        print("ERROR: BOT_TOKEN eller CHAT_ID saknas!")
        return

    message = "✅ Test – din bot fungerar! 🚗"
    send_telegram_message(bot_token, chat_id, message)
