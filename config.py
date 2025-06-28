import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла
load_dotenv('config.env')

def validate_required_env_var(var_name, value):
    """Валидация обязательных переменных окружения"""
    if not value:
        raise ValueError(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Переменная {var_name} не установлена!")
    return value

def validate_telegram_token(token):
    """Валидация формата Telegram токена"""
    if not token or not isinstance(token, str):
        raise ValueError("❌ КРИТИЧЕСКАЯ ОШИБКА: API_TOKEN должен быть строкой!")
    
    # Проверяем формат токена (число:буквы_цифры)
    if not token.count(':') == 1:
        raise ValueError("❌ КРИТИЧЕСКАЯ ОШИБКА: Неверный формат API_TOKEN!")
    
    bot_id, token_part = token.split(':')
    if not bot_id.isdigit() or len(token_part) < 30:
        raise ValueError("❌ КРИТИЧЕСКАЯ ОШИБКА: Неверный формат API_TOKEN!")
    
    return token

def validate_admin_id(admin_id):
    """Валидация ID администратора"""
    if not admin_id or not str(admin_id).isdigit():
        raise ValueError("❌ КРИТИЧЕСКАЯ ОШИБКА: ADMIN_ID должен быть числом!")
    return str(admin_id)

# Telegram Bot Configuration
API_TOKEN = validate_telegram_token(
    validate_required_env_var("API_TOKEN", os.getenv("API_TOKEN"))
)
ADMIN_ID = validate_admin_id(
    validate_required_env_var("ADMIN_ID", os.getenv("ADMIN_ID"))
)

# Database Configuration
DB_NAME = os.getenv("DB_NAME", "data/database.db")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "bot.log")

# Monitoring Configuration
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))

# Security Configuration
MAX_MESSAGE_LENGTH = int(os.getenv("MAX_MESSAGE_LENGTH", "1000"))
MAX_NAME_LENGTH = int(os.getenv("MAX_NAME_LENGTH", "50"))
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
BAN_THRESHOLD = int(os.getenv("BAN_THRESHOLD", "5"))

