import os

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

SERVER_TIMEZONE = (
    os.getenv("SERVER_TIMEZONE_PROD")
    if os.getenv("ENVIRONMENT") == "prod"
    else os.getenv("SERVER_TIMEZONE_DEV")
)

if __name__ == "__main__":
    print(TELEGRAM_TOKEN)
    print(DATABASE_URL)
    print(SERVER_TIMEZONE)
