import logging
import time
from datetime import datetime

import config
import schedule
import telebot
from database import db
from logging_conf import configure_logging

configure_logging()
logger = logging.getLogger("remember.bot")

bot = telebot.TeleBot(config.TELEGRAM_TOKEN)
db.connect()


def check_reminders():
    query = (
        db.reminders.select()
        .where(db.reminders.c.status != "completed")
        .order_by(db.reminders.c.date.asc())
    )
    result = db.session.execute(query)
    reminders = result.fetchall()
    reminders = [reminder._asdict() for reminder in reminders]
    logger.debug(reminders)
    for reminder in reminders:
        user = db.get_model(reminder["user_id"], db.users, "get user")
        if not user["is_active"]:
            continue

        if datetime.now() >= reminder["date"]:
            message = f"⏰ Recordatorio: {reminder['title']}\n🔔 Es ahora!\n"
            bot.send_message(reminder["user_id"], message)
            db.update_model(
                reminder["id"],
                {"status": "completed"},
                db.reminders,
                f"update reminder {reminder['title']}",
            )
        elif (
            datetime.now() >= reminder["reminder_time"]
            and reminder["status"] == "pending"
        ):
            message = (
                f"⏰ Recordatorio: {reminder['title']}\n📅 Fecha: {reminder['date']}\n"
            )
            bot.send_message(reminder["user_id"], message)
            db.update_model(
                reminder["id"],
                {"status": "incoming"},
                db.reminders,
                f"update reminder {reminder['title']}",
            )


if __name__ == "__main__":
    check_reminders()
    schedule.every(1).minutes.do(check_reminders)

    print("Scheduler iniciado. Verificando recordatorios cada minuto...")
    while True:
        schedule.run_pending()
        time.sleep(1)
