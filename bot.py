import os

import telebot
from dotenv import load_dotenv

load_dotenv()


class MyBot(telebot.TeleBot):
    def __init__(token, **kwargs):
        super().__init__(token, **kwargs)

    def send_message(self, chat_id, text, **kwargs):
        bot.send_chat_action(chat_id, "typing")
        return super().send_message(chat_id, text, **kwargs)


TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = MyBot(TOKEN)
