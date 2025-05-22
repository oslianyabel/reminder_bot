import logging
import re
from datetime import datetime, timedelta

import pytz
from telebot.types import KeyboardButton, ReplyKeyboardMarkup

import config
from bot import bot
from database import db
from logging_conf import configure_logging
from utils import convert_timezone, send_msg, time_zone_markup

configure_logging()
logger = logging.getLogger("app")

db.connect()

USER_STATES = {}


@bot.message_handler(commands=["start"])
def cmd_start(msg):
    logger.info("/start")
    user = db.get_model(msg.chat.id, db.users, f"get user {msg.from_user.username}")
    if not user:
        user_data = {
            "id": msg.chat.id,
            "username": msg.from_user.username,
            "first_name": msg.from_user.first_name,
            "last_name": msg.from_user.last_name,
        }
        bot.register_next_step_handler(msg, get_timezone, user_data)
        markup = time_zone_markup()

        send_msg("Seleccione su zona horaria", markup)
        return

    ans = (
        f"Hola {msg.from_user.first_name} 👋\n\n"
        "Puedes crear un nuevo recordatorio con /reminder\n"
        "Ver tus recordatorios con /list\n"
        "Cambiar tu zona horaria con /timezone\n"
        "Cambiar tiempo de recordatorios con /remindertime\n"
        "Desactivar/Activar recordatorios con /activate"
    )
    send_msg(msg, ans)


def get_timezone(msg, user_data):
    try:
        pytz.timezone(msg.text)  # Verificar si la zona horaria es válida
        user_data["time_zone"] = msg.text
        db.create_model(user_data, db.users, f"create user {user_data['username']}")

        ans = (
            f"¡Bienvenido {msg.from_user.first_name}! 👋\n\n"
            f"Tu zona horaria se ha configurado como: {msg.text}\n\n"
            "Ahora puedes:\n"
            "- Crear recordatorios con /reminder\n"
            "- Ver tus recordatorios con /list\n"
            "- Cambiar tu zona horaria con /timezone\n"
            "- Ajustar el tiempo de recordatorios con /remindertime\n"
            "- Activar/desactivar notificaciones con /activate"
        )
        send_msg(msg, ans)

    except pytz.exceptions.UnknownTimeZoneError:
        # Si la zona horaria no es válida, volver a pedirla
        markup = time_zone_markup()
        send_msg(
            msg,
            "❌ Zona horaria no válida. Por favor selecciona una de las opciones:",
            markup,
        )
        bot.register_next_step_handler(msg, get_timezone, user_data)


@bot.message_handler(commands=["reminder"])
def create_reminder(msg):
    logger.info("/reminder")
    user = db.get_model(msg.chat.id, db.users, f"get user {msg.from_user.username}")
    if not user:
        send_msg(msg, "No estás registrado. Usa /start primero.")
        return

    send_msg(msg, "Vamos a crear un nuevo recordatorio. Primero dime el título:")
    bot.register_next_step_handler(msg, process_reminder_title)


def process_reminder_title(msg):
    try:
        reminder_data = {"title": msg.text}
        sent_msg = bot.send_message(
            msg.chat.id,
            "Genial. Ahora, por favor, describe el recordatorio (o escribe 'saltar' si no quieres añadir una descripción):",
        )
        bot.register_next_step_handler(
            sent_msg, process_reminder_description, reminder_data
        )
    except Exception as exc:
        logger.error(f"Error en process_reminder_title: {exc}")
        send_msg(msg, "Ocurrió un error. Por favor intenta nuevamente con /reminder")


def process_reminder_description(msg, reminder_data):
    try:
        if msg.text.lower() != "saltar":
            reminder_data["description"] = msg.text
        else:
            reminder_data["description"] = None

        sent_msg = bot.send_message(
            msg.chat.id,
            "Ahora, ingresa la fecha y hora del recordatorio (formato: DD/MM/AAAA HH:MM)\nEjemplo: 25/12/2023 15:30",
        )
        bot.register_next_step_handler(sent_msg, process_reminder_date, reminder_data)
    except Exception as e:
        logger.error(f"Error en process_reminder_description: {e}")
        send_msg(msg, "Ocurrió un error. Por favor intenta nuevamente con /reminder")


def process_reminder_date(msg, reminder_data):
    try:
        date_str = re.sub(r"[^\d/ :]", "", msg.text)
        date = datetime.strptime(date_str, "%d/%m/%Y %H:%M")

        user = db.get_model(
            msg.chat.id, db.users, f"get timezone from user {msg.from_user.username}"
        )
        user_time_zone = user.get("time_zone")

        if user_time_zone != config.SERVER_TIMEZONE:
            date = convert_timezone(date, user_time_zone, config.SERVER_TIMEZONE)

        if datetime.now() > date:
            send_msg(msg, "La fecha no puede pertenecer al pasado")
            return

        reminder_data["date"] = date

        # Mostrar resumen y pedir confirmación
        summary = (
            f"📌 Resumen del recordatorio:\n\n"
            f"🏷 Título: {reminder_data['title']}\n"
            f"📝 Descripción: {reminder_data.get('description', 'Ninguna')}\n"
            f"📅 Fecha y hora: {date.strftime('%d/%m/%Y %H:%M')}\n\n"
            f"¿Todo correcto? (sí/no)"
        )

        markup = ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add(KeyboardButton("Sí"), KeyboardButton("No"))

        sent_msg = bot.send_message(msg.chat.id, summary, reply_markup=markup)
        bot.register_next_step_handler(
            sent_msg, process_reminder_confirmation, reminder_data
        )

    except ValueError:
        send_msg(
            msg,
            "Formato incorrecto. Por favor ingresa la fecha y hora en formato DD/MM/AAAA HH:MM\nEjemplo: 25/12/2023 15:30",
        )
    except Exception as exc:
        logger.error(f"Error en process_reminder_date: {exc}")
        send_msg(msg, "Ocurrió un error. Por favor intenta nuevamente con /reminder")


def process_reminder_confirmation(msg, reminder_data):
    try:
        if msg.text.lower() in ["sí", "si", "s"]:
            user = db.get_model(
                msg.chat.id, db.users, f"get user {msg.from_user.username}"
            )
            reminder_time = reminder_data["date"] - timedelta(
                minutes=user["default_reminder_minutes"]
            )
            data = {
                "user_id": msg.chat.id,
                "title": reminder_data["title"],
                "description": reminder_data["description"],
                "date": reminder_data["date"],
                "reminder_time": reminder_time,
            }
            db.create_model(data, db.reminders, f"create reminder {data['title']}")
            send_msg(msg, "✅ Recordatorio creado exitosamente!")
        else:
            send_msg(
                msg, "Recordatorio cancelado. Puedes empezar de nuevo con /reminder"
            )
    except Exception as e:
        logger.error(f"Error en process_reminder_confirmation: {e}")
        send_msg(
            msg,
            "Ocurrió un error al crear el recordatorio. Por favor intenta nuevamente.",
        )


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

    markup = time_zone_markup()

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
    bot.delete_webhook()
    bot.polling()
