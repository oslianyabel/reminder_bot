import logging
import re
from datetime import datetime, timedelta

import config
import pytz
import telebot
from database import db
from logging_conf import configure_logging
from telebot.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

configure_logging()
logger = logging.getLogger("remember.bot")
bot = telebot.TeleBot(config.TELEGRAM_TOKEN)
db.connect()

USER_STATES = {}


def send_msg(obj_msg, msg, markup=ReplyKeyboardRemove()):
    bot.send_chat_action(obj_msg.chat.id, "typing")
    bot.send_message(obj_msg.chat.id, msg, reply_markup=markup)


def convert_timezone(date_time, from_tz_str, to_tz_str):
    logger.warning(f"Convert datetime from {from_tz_str} to {to_tz_str}")
    from_tz = pytz.timezone(from_tz_str)
    to_tz = pytz.timezone(to_tz_str)

    from_timezone_dt = from_tz.localize(date_time)
    to_timezone_dt = from_timezone_dt.astimezone(to_tz)

    return to_timezone_dt.replace(tzinfo=None)


@bot.message_handler(commands=["start"])
def cmd_start(msg):
    logger.info("/start")
    user = db.get_model(msg.chat.id, db.users, f"get user {msg.from_user.username}")
    if not user:
        data = {
            "id": msg.chat.id,
            "username": msg.from_user.username,
            "first_name": msg.from_user.first_name,
            "last_name": msg.from_user.last_name,
            "time_zone": "America/Havana",
            "default_reminder_minutes": 60,
            "is_active": True,
        }
        db.create_model(data, db.users, f"create user {msg.from_user.username}")

    if msg.chat.id in USER_STATES:
        del USER_STATES[msg.chat.id]

    ans = (
        f"Hola {msg.from_user.first_name} 👋\n\n"
        "Puedes crear un nuevo recordatorio con /reminder\n"
        "Ver tus recordatorios con /list\n"
        "Cambiar tu zona horaria con /timezone\n"
        "Cambiar tiempo de recordatorios con /remindertime\n"
        "Desactivar/Activar recordatorios con /activate"
    )
    send_msg(msg, ans)


@bot.message_handler(commands=["reminder"])
def create_reminder(msg):
    logger.info("/reminder")
    user = db.get_model(msg.chat.id, db.users, f"get user {msg.from_user.username}")
    if not user:
        send_msg(msg, "No estás registrado. Usa /start primero.")
        return

    USER_STATES[msg.chat.id] = {"state": "title"}
    send_msg(msg, "Vamos a crear un nuevo recordatorio. Primero dime el título:")


@bot.message_handler(
    func=lambda message: USER_STATES.get(message.chat.id, {}).get("state") == "title"
)
def handle_reminder_title(msg):
    USER_STATES[msg.chat.id]["title"] = msg.text
    USER_STATES[msg.chat.id]["state"] = "description"
    send_msg(
        msg,
        "Genial. Ahora, por favor, describe el recordatorio (o escribe 'saltar' si no quieres añadir una descripción):",
    )


@bot.message_handler(
    func=lambda message: USER_STATES.get(message.chat.id, {}).get("state")
    == "description"
)
def handle_reminder_description(msg):
    if msg.text.lower() != "saltar":
        USER_STATES[msg.chat.id]["description"] = msg.text
    else:
        USER_STATES[msg.chat.id]["description"] = None

    USER_STATES[msg.chat.id]["state"] = "date"
    send_msg(
        msg,
        "Ahora, ingresa la fecha y hora del recordatorio (formato: DD/MM/AAAA HH:MM)\nEjemplo: 25/12/2023 15:30",
    )


@bot.message_handler(
    func=lambda message: USER_STATES.get(message.chat.id, {}).get("state") == "date"
)
def handle_reminder_date(msg):
    try:
        date_str = re.sub(r"[^\d/ :]", "", msg.text)
        date = datetime.strptime(date_str, "%d/%m/%Y %H:%M")

        user = db.get_model(
            msg.chat.id, db.users, f"get timezone from user {msg.from_user.username}"
        )
        if user.get("time_zone"):
            if user["time_zone"] != config.SERVER_TIMEZONE:
                date = convert_timezone(date, user["time_zone"], config.SERVER_TIMEZONE)

        if datetime.now() >= date:
            send_msg(msg, "La fecha no puede pertenecer al pasado")
            return

        USER_STATES[msg.chat.id]["date"] = date
        USER_STATES[msg.chat.id]["state"] = "confirmation"

        reminder = USER_STATES[msg.chat.id]
        summary = (
            f"📌 Resumen del recordatorio:\n\n"
            f"🏷 Título: {reminder['title']}\n"
            f"📝 Descripción: {reminder.get('description', 'Ninguna')}\n"
            f"📅 Fecha y hora: {date.strftime('%d/%m/%Y %H:%M %Z')}\n\n"
            f"¿Todo correcto? (sí/no)"
        )

        markup = ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add(KeyboardButton("Sí"), KeyboardButton("No"))

        send_msg(msg, summary, markup)

    except ValueError:
        send_msg(
            msg,
            "Formato incorrecto. Por favor ingresa la fecha y hora en formato DD/MM/AAAA HH:MM\nEjemplo: 25/12/2023 15:30",
        )


@bot.message_handler(
    func=lambda message: USER_STATES.get(message.chat.id, {}).get("state")
    == "confirmation"
)
def handle_confirmation(msg):
    if msg.text.lower() in ["sí", "si", "s"]:
        user = db.get_model(msg.chat.id, db.users, f"get user {msg.from_user.username}")
        reminder_time = USER_STATES[msg.chat.id]["date"] - timedelta(
            minutes=user["default_reminder_minutes"]
        )
        data = {
            "user_id": msg.chat.id,
            "title": USER_STATES[msg.chat.id]["title"],
            "description": USER_STATES[msg.chat.id]["description"],
            "date": USER_STATES[msg.chat.id]["date"],
            "reminder_time": reminder_time,
        }
        db.create_model(data, db.reminders, f"create reminder {data['title']}")
        send_msg(msg, "✅ Recordatorio creado exitosamente!")
    else:
        send_msg(msg, "Recordatorio cancelado. Puedes empezar de nuevo con /reminder")

    del USER_STATES[msg.chat.id]


@bot.message_handler(commands=["list"])
def list_reminders(msg):
    logger.info("/list")
    user = db.get_model(msg.chat.id, db.users, f"get user {msg.from_user.username}")
    if not user:
        send_msg(msg, "No estás registrado. Usa /start primero")
        return

    query = (
        db.reminders.select()
        .where(
            (db.reminders.c.user_id == msg.chat.id)
            & (db.reminders.c.status == "pending")
        )
        .order_by(db.reminders.c.date.asc())
    )

    result = db.session.execute(query)
    reminders = result.fetchall()

    if not reminders:
        send_msg(msg, "No tienes recordatorios pendientes")
        return

    response = "📅 Tus recordatorios pendientes:\n\n"
    reminders = [reminder._asdict() for reminder in reminders]
    for reminder in reminders:
        response += (
            f"📌 {reminder['title']}\n\n"
            f"🕒 {reminder['date'].strftime('%d/%m/%Y %H:%M %Z')}\n\n"
            f"⏰ Recordatorio: {reminder['reminder_time'].strftime('%d/%m/%Y %H:%M %Z')}\n\n"
        )
        if reminder["description"]:
            response += f"📖 {reminder['description']}\n\n"

    send_msg(msg, response)


@bot.message_handler(commands=["activate"])
def activate_reminders(msg):
    logger.info("/activate")
    user = db.get_model(msg.chat.id, db.users, f"get user {msg.from_user.username}")
    if not user:
        send_msg(msg, "No estás registrado. Usa /start primero.")
        return

    if user["is_active"]:
        db.update_model(
            msg.chat.id,
            {"is_active": False},
            db.users,
            f"reminders from user {msg.from_user.username} disabled",
        )
        send_msg(msg, "🔕 Recordatorios desactivados. No recibirás más notificaciones")
    else:
        db.update_model(
            msg.chat.id,
            {"is_active": True},
            db.users,
            f"reminders from user {msg.from_user.username} enabled",
        )
        send_msg(msg, "🔔 Recordatorios activados. Recibirás las notificaciones")


@bot.message_handler(commands=["timezone"])
def set_timezone(msg):
    logger.info("/timezone")
    user = db.get_model(msg.chat.id, db.users, f"get user {msg.from_user.username}")
    if not user:
        send_msg(msg, "No estás registrado. Usa /start primero")
        return

    USER_STATES[msg.chat.id] = {"state": "timezone"}

    common_timezones = [
        "America/Havana",
        "America/Mexico_City",
        "America/New_York",
        "America/Los_Angeles",
        "Europe/Madrid",
        "Europe/London",
        "Asia/Tokyo",
    ]

    markup = ReplyKeyboardMarkup(one_time_keyboard=True)
    for tz in common_timezones:
        markup.add(KeyboardButton(tz))

    send_msg(
        msg,
        "Por favor, ingresa tu zona horaria (ej: America/Havana) o selecciona una de las opciones:",
        markup,
    )


@bot.message_handler(
    func=lambda message: USER_STATES.get(message.chat.id, {}).get("state") == "timezone"
)
def handle_timezone(msg):
    try:
        # Verificar si la zona horaria es válida
        pytz.timezone(msg.text)

        db.update_model(
            msg.chat.id,
            {"time_zone": msg.text},
            db.users,
            f"update timezone for user {msg.from_user.username}",
        )

        send_msg(msg, f"✅ Zona horaria actualizada a: {msg.text}")
        del USER_STATES[msg.chat.id]

    except pytz.exceptions.UnknownTimeZoneError:
        send_msg(msg, "❌ Zona horaria no válida. Intenta de nuevo")


@bot.message_handler(commands=["remindertime"])
def set_reminder_time(msg):
    logger.info("/remindertime")
    USER_STATES[msg.chat.id] = {"state": "reminder_time"}

    markup = ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add(
        KeyboardButton("15"),
        KeyboardButton("30"),
        KeyboardButton("60"),
        KeyboardButton("120"),
    )

    send_msg(
        msg,
        "¿Cuántos minutos antes del recordatorio quieres recibir el recordatorio? (ej: 30 para 30 minutos antes)",
        markup,
    )


@bot.message_handler(
    func=lambda message: USER_STATES.get(message.chat.id, {}).get("state")
    == "reminder_time"
)
def handle_reminder_time(msg):
    try:
        if not msg.text.isdigit():
            raise ValueError
        minutes = int(msg.text)
        if minutes <= 0:
            raise ValueError

        db.update_model(
            msg.chat.id,
            {"default_reminder_minutes": minutes},
            db.users,
            f"update reminder time for user {msg.from_user.username}",
        )

        send_msg(
            msg, f"✅ Recordatorio configurado para {minutes} minutos antes de la hora"
        )
        del USER_STATES[msg.chat.id]

    except ValueError:
        send_msg(msg, "❌ Por favor ingresa un número válido de minutos (ej: 30).")


if __name__ == "__main__":
    logger.info("Iniciando Bot")
    bot.polling()
