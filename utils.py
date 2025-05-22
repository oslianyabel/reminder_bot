import logging

import pytz
from telebot.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

from bot import bot
from logging_conf import configure_logging
from time_zone_enum import TimeZoneEnum

configure_logging()
logger = logging.getLogger("app")


def send_msg(obj_msg, msg, markup=ReplyKeyboardRemove()):
    bot.send_chat_action(obj_msg.chat.id, "typing")
    bot.send_message(obj_msg.chat.id, msg, reply_markup=markup)


def time_zone_markup():
    markup = ReplyKeyboardMarkup(one_time_keyboard=True)
    for tz in TimeZoneEnum.get_all():
        markup.add(KeyboardButton(tz))

    return markup


def convert_timezone(date_time, from_tz_str, to_tz_str):
    logger.info(f"Convert datetime from {from_tz_str} to {to_tz_str}")
    from_tz = pytz.timezone(from_tz_str)
    to_tz = pytz.timezone(to_tz_str)

    from_timezone_dt = from_tz.localize(date_time)
    to_timezone_dt = from_timezone_dt.astimezone(to_tz)

    result = to_timezone_dt.replace(tzinfo=None)
    logger.info(f"Date converted to: {result}")
    return result
