import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла
load_dotenv('config.env')

# Telegram Bot Configuration
API_TOKEN = os.getenv("API_TOKEN", "7906419182:AAFkvUNgQpbgAka959-gC1oL0WGvq58SPJs")
ADMIN_ID = os.getenv("ADMIN_ID", "853510094")

# Database Configuration
DB_NAME = os.getenv("DB_NAME", "data/database.db")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "bot.log")

# Monitoring Configuration
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))

