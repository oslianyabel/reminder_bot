from enum import Enum

class TimeZoneEnum(Enum):
    LOS_ANGELES = "America/Los_Angeles" # EEUU (UTC-7/-8)
    
    HAVANA = "America/Havana" # Cuba (UTC-5/-4) 
    
    BUENOS_AIRES = "America/Argentina/Buenos_Aires" # Argentina (UTC-3)
    
    LONDON = "Europe/London" # Reino Unido (UTC+0/+1)
    
    TOKYO = "Asia/Tokyo" # Japón (UTC+9)
    
    CAIRO = "Africa/Cairo" # Egipto (UTC+2)
    
    SYDNEY = "Australia/Sydney" # Australia (UTC+10/+11)
    
    @classmethod
    def get_all(cls):
        return [tz.name for tz in cls]
    
    @classmethod
    def is_valid(cls, timezone_str):
        return any(timezone_str == tz.name for tz in cls)
    

if __name__ == "__main__":
    print(TimeZoneEnum.is_valid("HAVANA"))
