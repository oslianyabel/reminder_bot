from enum import Enum


class TimeZoneEnum(Enum):
    HAVANA = "America/Havana"
    MEXICO_CITY = "America/Mexico_City"
    NEW_YORK = "America/New_York"
    LOS_ANGELES = "America/Los_Angeles"
    MADRID = "Europe/Madrid"
    LONDON = "Europe/London"
    TOKYO = "Asia/Tokyo"
    
    @classmethod
    def get_all(cls):
        return [tz.value for tz in cls]
    
    @classmethod
    def is_valid(cls, timezone_str):
        return any(timezone_str == tz.value for tz in cls)