# config.py
import os
import json
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Обязательные переменные
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("❌ BOT_TOKEN не установлен в .env файле")

    SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
    if not SPREADSHEET_ID:
        raise ValueError("❌ SPREADSHEET_ID не установлен в .env файле")

    # Опциональные с дефолтами
    ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID", "-1001234567890"))

    # Google Credentials из переменной окружения
    GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not GOOGLE_CREDENTIALS_JSON:
        raise ValueError("❌ GOOGLE_CREDENTIALS_JSON не установлен в .env")


    GOOGLE_CREDENTIALS = json.loads(GOOGLE_CREDENTIALS_JSON)


    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    # Rate limiting
    MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "30"))

    # Время ожидания для API
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))


config = Config()

