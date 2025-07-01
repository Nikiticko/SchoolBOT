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
from services.monitor import init_review_monitor, stop_review_monitor, init_lesson_reminder_monitor, stop_lesson_reminder_monitor
from utils.logger import setup_logger, log_bot_startup, log_bot_shutdown, log_error
from utils.exceptions import (
    BotException, DatabaseException, ConfigurationException, 
    TelegramAPIException, handle_exception
)
from state.state_manager import state_manager
from utils.cleanup import auto_cleanup

# Регистрация хендлеров
from handlers import commands, registration, admin, reviews
from handlers.admin import register_all_admin_handlers
from handlers.reviews import register as register_reviews
from state.users import cleanup_expired_registrations
import os
import threading
import time
import signal
import sys
os.system('cls || clear')

# Настройка логирования
logger = setup_logger('bot')

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения работы"""
    logger.info(f"Received signal {signum}, shutting down...")
    stop_review_monitor()
    stop_lesson_reminder_monitor()
    log_bot_shutdown(logger)
    state_manager.stop()
    sys.exit(0)

# Регистрируем обработчики сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

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
# try:
#     start_monitoring(bot, logger)
#     logger.info(f"✅ Monitoring started with interval {CHECK_INTERVAL}s")
# except Exception as e:
#     error_msg = handle_exception(e, logger, "Monitoring startup")
#     logger.error(f"❌ {error_msg}")

# Инициализация монитора запросов на оценку
try:
    review_monitor = init_review_monitor(bot)
    lesson_reminder_monitor = init_lesson_reminder_monitor(bot)
    logger.info("✅ Review and lesson reminder monitors initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize monitors: {e}")

# Функция для периодической очистки просроченных регистраций
def cleanup_registrations_periodically():
    """Периодически очищает просроченные регистрации"""
    while True:
        try:
            time.sleep(300)  # Проверяем каждые 5 минут
            cleaned_count = cleanup_expired_registrations(timeout_minutes=30)
            if cleaned_count > 0:
                logger.info(f"🧹 Cleaned up {cleaned_count} expired registrations")
        except Exception as e:
            log_error(logger, e, "Error in registration cleanup")

# Запуск очистки регистраций в отдельном потоке
try:
    cleanup_thread = threading.Thread(target=cleanup_registrations_periodically, daemon=True)
    cleanup_thread.start()
    logger.info("✅ Registration cleanup thread started")
except Exception as e:
    error_msg = handle_exception(e, logger, "Registration cleanup startup")
    logger.error(f"❌ {error_msg}")

# Запуск автоочистки временных файлов
try:
    auto_cleanup.start_periodic_cleanup(interval_hours=6)  # Каждые 6 часов
    logger.info("✅ Auto-cleanup thread started")
except Exception as e:
    error_msg = handle_exception(e, logger, "Auto-cleanup startup")
    logger.error(f"❌ {error_msg}")

# Регистрация всех обработчиков
try:
    # Сначала регистрируем админские обработчики (включая /start для админа)
    admin.register_all_admin_handlers(bot, logger)
    # Потом обычные обработчики
    commands.register_handlers(bot)
    registration.register_handlers(bot)
    register_reviews(bot, logger)  # обработчики отзывов
    
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
    if isinstance(e, telebot.apihelper.ApiTelegramException) and '409' in str(e):
        logger.error("❌ [FATAL] 409 Conflict: Бот уже запущен где-то ещё! Завершаем работу.")
        print("❌ [FATAL] 409 Conflict: Бот уже запущен где-то ещё! Завершаем работу.")
        log_bot_shutdown(logger)
        state_manager.stop()
        sys.exit(1)
    
    error_msg = handle_exception(e, logger, "Bot polling")
    logger.error(f"❌ {error_msg}")
    log_bot_shutdown(logger)
    state_manager.stop()
