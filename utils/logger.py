import logging
import os
from datetime import datetime

# Опциональный импорт config для случаев, когда dotenv недоступен
try:
    from config import LOG_LEVEL, LOG_FILE
except ImportError:
    LOG_LEVEL = "INFO"
    LOG_FILE = "bot.log"

def setup_logger(name='bot'):
    """Настройка логгера для бота"""
    
    # Создаем директорию для логов если её нет
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Настраиваем логгер
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL.upper()))
    
    # Очищаем существующие обработчики
    logger.handlers.clear()
    
    # Создаем форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Обработчик для файла
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Добавляем обработчики
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def log_user_action(logger, user_id, action, details=None):
    """Логирование действий пользователя"""
    message = f"USER {user_id}: {action}"
    if details:
        message += f" - {details}"
    logger.info(message)

def log_admin_action(logger, admin_id, action, details=None):
    """Логирование действий администратора"""
    message = f"ADMIN {admin_id}: {action}"
    if details:
        message += f" - {details}"
    logger.info(message)

def log_error(logger, error, context=None):
    """Логирование ошибок"""
    message = f"ERROR: {error}"
    if context:
        message += f" | Context: {context}"
    logger.error(message)

def log_database_operation(logger, operation, table, details=None):
    """Логирование операций с базой данных"""
    message = f"DB {operation} on {table}"
    if details:
        message += f" - {details}"
    logger.debug(message)

def log_bot_startup(logger):
    """Логирование запуска бота"""
    logger.info("🤖 Bot started successfully")
    logger.info(f"📝 Log level: {LOG_LEVEL}")
    logger.info(f"📁 Log file: {LOG_FILE}")

def log_bot_shutdown(logger):
    """Логирование остановки бота"""
    logger.info("🛑 Bot shutdown") 