import os

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
SERVER_TIMEZONE = "America/Los_Angeles"

if __name__ == "__main__":
    print(TELEGRAM_TOKEN)
    print(DATABASE_URL)
    print(SERVER_TIMEZONE)
    