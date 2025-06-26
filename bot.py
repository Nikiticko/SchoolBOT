# === bot.py ===
"""
ВАЖНО:
- Не запускайте несколько экземпляров этого бота одновременно (ни на одном, ни на разных компьютерах/серверах).
- Не используйте одновременно polling и webhook! В этом проекте используется только polling (bot.infinity_polling).
- Если бот запускается автоматически (systemd, планировщик задач, автозапуск), убедитесь, что нет дубликатов.
- Если видите ошибку 409 Conflict — завершите все лишние процессы python с этим ботом.
"""
from telebot import TeleBot
from config import API_TOKEN, CHECK_INTERVAL
from data.db import init_db
from services.monitor import start_monitoring
from utils.logger import setup_logger, log_bot_startup, log_bot_shutdown, log_error

# Регистрация хендлеров
from handlers import commands, registration, admin
from handlers.course_editor import register_course_editor
from handlers.admin_actions import register_admin_actions
import os
os.system('cls || clear')
# Настройка логирования
logger = setup_logger('bot')

# Инициализация бота и БД
try:
    bot = TeleBot(API_TOKEN)
    init_db()
    logger.info("✅ Bot and database initialized successfully")
except Exception as e:
    log_error(logger, e, "Bot initialization")
    raise

# Запуск мониторинга заявок
try:
    start_monitoring(bot, logger)
    logger.info(f"✅ Monitoring started with interval {CHECK_INTERVAL}s")
except Exception as e:
    log_error(logger, e, "Monitoring startup")

# Регистрация всех обработчиков
try:
    commands.register(bot, logger)               # пользовательские команды
    registration.register(bot, logger)          # регистрация заявки
    admin.register(bot, logger)                 # меню админа + список заявок
    register_course_editor(bot, logger)        # редактор курсов
    register_admin_actions(bot, logger)        # действия с заявками
    logger.info("✅ All handlers registered successfully")
except Exception as e:
    log_error(logger, e, "Handler registration")

# Логируем запуск бота
log_bot_startup(logger)

# Запуск бота
try:
    logger.info("🚀 Starting bot polling...")
    bot.infinity_polling(timeout=30, long_polling_timeout=5)
except KeyboardInterrupt:
    logger.info("⚠️ Bot stopped by user (Ctrl+C)")
    log_bot_shutdown(logger)
except Exception as e:
    # Обработка ошибки 409 (Conflict: terminated by other getUpdates request)
    import telebot
    if isinstance(e, telebot.apihelper.ApiTelegramException) and '409' in str(e):
        logger.error("❌ [FATAL] 409 Conflict: Бот уже запущен где-то ещё! Завершаем работу.")
        print("❌ [FATAL] 409 Conflict: Бот уже запущен где-то ещё! Завершаем работу.")
        log_bot_shutdown(logger)
        import sys
        sys.exit(1)
    log_error(logger, e, "Bot polling")
    log_bot_shutdown(logger)
