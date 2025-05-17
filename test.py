from datetime import datetime

import pytz


def convert_timezone(
    date_time, from_tz_str, to_tz_str, date_format="%Y-%m-%d %H:%M:%S"
):
    from_tz = pytz.timezone(from_tz_str)
    to_tz = pytz.timezone(to_tz_str)

    from_timezone_dt = from_tz.localize(date_time)
    to_timezone_dt = from_timezone_dt.astimezone(to_tz)

    return to_timezone_dt


# Ejemplo de uso
date_time_str = datetime.now()
from_tz_str = "America/Havana"
to_tz_str = "Europe/Madrid"

converted_time = convert_timezone(date_time_str, from_tz_str, to_tz_str)
print(f"Original: {date_time_str} {from_tz_str}")
print(f"Convertido: {converted_time.strftime('%Y-%m-%d %H:%M:%S')} {to_tz_str}")
