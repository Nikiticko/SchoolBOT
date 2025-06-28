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
from data.db import init_db, migrate_database
from services.monitor import start_monitoring
from utils.logger import setup_logger, log_bot_startup, log_bot_shutdown, log_error
from utils.exceptions import (
    BotException, DatabaseException, ConfigurationException, 
    TelegramAPIException, handle_exception
)
from state.state_manager import state_manager

# Регистрация хендлеров
from handlers import commands, registration, admin
from handlers.course_editor import register_course_editor
from handlers.admin_actions import register_admin_actions, set_review_request_function
from handlers.reviews import register as register_reviews
import os
os.system('cls || clear')

# Настройка логирования
logger = setup_logger('bot')

# Инициализация бота и БД
try:
    bot = TeleBot(API_TOKEN)
    init_db()
    
    # Выполняем миграцию БД
    if migrate_database():
        logger.info("✅ Database migration completed successfully")
    else:
        logger.warning("⚠️ Database migration failed, but bot will continue")
    
    logger.info("✅ Bot and database initialized successfully")
except Exception as e:
    error_msg = handle_exception(e, logger, "Bot initialization")
    logger.error(f"❌ {error_msg}")
    raise

# Запуск мониторинга заявок
try:
    start_monitoring(bot, logger)
    logger.info(f"✅ Monitoring started with interval {CHECK_INTERVAL}s")
except Exception as e:
    error_msg = handle_exception(e, logger, "Monitoring startup")
    logger.error(f"❌ {error_msg}")

# Регистрация всех обработчиков
try:
    commands.register_handlers(bot)
    registration.register_handlers(bot)
    admin.register_handlers(bot)  # Регистрируем новые админские хендлеры
    register_course_editor(bot, logger)
    register_admin_actions(bot, logger)
    send_review_request = register_reviews(bot, logger)  # обработчики отзывов
    
    # Устанавливаем функцию отправки отзывов для admin_actions
    set_review_request_function(send_review_request)
    
    logger.info("✅ All handlers registered successfully")
except Exception as e:
    error_msg = handle_exception(e, logger, "Handler registration")
    logger.error(f"❌ {error_msg}")

# Логируем запуск бота
log_bot_startup(logger)

# Запуск бота
try:
    logger.info("🚀 Starting bot polling...")
    bot.infinity_polling(timeout=30, long_polling_timeout=5)
except KeyboardInterrupt:
    logger.info("⚠️ Bot stopped by user (Ctrl+C)")
    log_bot_shutdown(logger)
    # Останавливаем StateManager
    state_manager.stop()
except Exception as e:
    # Обработка ошибки 409 (Conflict: terminated by other getUpdates request)
    import telebot
    if isinstance(e, telebot.apihelper.ApiTelegramException) and '409' in str(e):
        logger.error("❌ [FATAL] 409 Conflict: Бот уже запущен где-то ещё! Завершаем работу.")
        print("❌ [FATAL] 409 Conflict: Бот уже запущен где-то ещё! Завершаем работу.")
        log_bot_shutdown(logger)
        state_manager.stop()
        import sys
        sys.exit(1)
    
    error_msg = handle_exception(e, logger, "Bot polling")
    logger.error(f"❌ {error_msg}")
    log_bot_shutdown(logger)
    state_manager.stop()
