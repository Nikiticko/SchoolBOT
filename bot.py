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
from handlers import admin
from handlers.users import commands, registration, reviews
from handlers.admin import register_all_admin_handlers
from state.users import cleanup_expired_registrations
import threading
import time
import signal
import sys
import telebot

# Настройка логирования
logger = setup_logger('bot')

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения работы"""
    logger.info(f"Received signal {signum}, shutting down...")
    stop_review_monitor()
    stop_lesson_reminder_monitor()
    log_bot_shutdown(logger)
    
    # Безопасная остановка FSM
    try:
        state_manager.stop()
    except Exception as e:
        logger.warning(f"Ошибка при остановке FSM: {e}")
    
    sys.exit(0)

# Регистрируем обработчики сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Инициализация бота и БД
try:
    # Улучшенная инициализация бота с настройками
    bot = TeleBot(API_TOKEN, parse_mode="HTML", threaded=False)
    
    # Инициализируем БД
    init_db()
    
    # Проверяем целостность БД
    from data.db import check_database_integrity
    is_ok, error_msg = check_database_integrity()
    
    if not is_ok:
        logger.error(f"❌ Критическая ошибка БД: {error_msg}")
        raise Exception(f"Не удалось проверить целостность БД: {error_msg}")
    
    logger.info("✅ База данных проверена и готова к работе")
    
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
    
    # Системные события
    logger.info("🔄 Auto-cleanup started (every 6 hours)")
    
except Exception as e:
    error_msg = handle_exception(e, logger, "Auto-cleanup startup")
    logger.error(f"❌ {error_msg}")

# Функция для периодического логирования статистики
def log_system_stats():
    """Периодически логирует статистику системы"""
    import time
    import psutil
    from data.db import get_pending_applications, get_assigned_applications
    
    while True:
        try:
            time.sleep(3600)  # Каждые 60 минут
            
            # Статистика БД
            pending_apps = len(get_pending_applications())
            assigned_apps = len(get_assigned_applications())
            
            # Статистика системы
            memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # МБ
            cpu_percent = psutil.Process().cpu_percent()
            
            # Логирование статистики
            logger.info(f"📊 System stats: {pending_apps} pending, {assigned_apps} assigned applications")
            logger.info(f"💾 Memory usage: {memory_usage:.1f} MB, CPU: {cpu_percent:.1f}%")
            logger.info(f"📊 Daily stats: {pending_apps + assigned_apps} total applications in system")
            
        except Exception as e:
            logger.error(f"Error in system stats logging: {e}")

# Функция для периодической проверки целостности БД
def periodic_database_integrity_check():
    """Периодически проверяет целостность БД"""
    from data.db import check_database_integrity
    
    while True:
        try:
            time.sleep(86400)  # Каждые 24 часа
            
            logger.info("🔍 Выполняется периодическая проверка целостности БД...")
            
            # Проверяем целостность
            is_ok, error_msg = check_database_integrity()
            
            if not is_ok:
                logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: БД повреждена: {error_msg}")
                
                # Отправляем уведомление админу (если возможно)
                try:
                    from config import ADMIN_ID
                    bot.send_message(ADMIN_ID, f"🚨 КРИТИЧЕСКАЯ ОШИБКА БД!\n\nБД повреждена: {error_msg}\n\nТребуется вмешательство администратора.")
                except Exception as e:
                    logger.error(f"Не удалось отправить уведомление админу: {e}")
            else:
                logger.info("✅ Периодическая проверка целостности БД пройдена успешно")
            
        except Exception as e:
            logger.error(f"Error in database integrity check: {e}")

# Запуск логирования статистики в отдельном потоке
try:
    stats_thread = threading.Thread(target=log_system_stats, daemon=True)
    stats_thread.start()
    logger.info("✅ System stats logging thread started")
except Exception as e:
    logger.error(f"❌ Failed to start stats logging: {e}")

# Запуск проверки целостности БД в отдельном потоке
try:
    integrity_thread = threading.Thread(target=periodic_database_integrity_check, daemon=True)
    integrity_thread.start()
    logger.info("✅ Database integrity check thread started")
except Exception as e:
    logger.error(f"❌ Failed to start database integrity check: {e}")

# Очистка старых rate limit данных при запуске
try:
    from utils.security import clear_old_rate_limit_data
    clear_old_rate_limit_data()
    logger.info("✅ Old rate limit data cleared")
except Exception as e:
    logger.warning(f"⚠️ Failed to clear old rate limit data: {e}")

# Регистрация всех обработчиков с обработкой ошибок
try:
    # Сначала регистрируем админские обработчики (включая /start для админа)
    try:
        admin.register_all_admin_handlers(bot, logger)
        logger.info("✅ Admin handlers registered successfully")
    except Exception as e:
        logger.error(f"❌ Error registering admin handlers: {e}")
    
    # Потом обычные обработчики
    try:
        commands.register_handlers(bot)
        logger.info("✅ User commands handlers registered successfully")
    except Exception as e:
        logger.error(f"❌ Error registering user commands handlers: {e}")
    
    try:
        registration.register_handlers(bot)
        logger.info("✅ Registration handlers registered successfully")
    except Exception as e:
        logger.error(f"❌ Error registering registration handlers: {e}")
    
    try:
        reviews.register(bot, logger)
        logger.info("✅ Reviews handlers registered successfully")
    except Exception as e:
        logger.error(f"❌ Error registering reviews handlers: {e}")
    
    logger.info("✅ All handlers registered successfully")
except Exception as e:
    error_msg = handle_exception(e, logger, "Handler registration")
    logger.error(f"❌ {error_msg}")

# Fallback-хендлер для нераспознанных сообщений
@bot.message_handler(func=lambda message: True)
def fallback_handler(message):
    """Обработчик для нераспознанных сообщений"""
    try:
        # Проверяем, не является ли это командой
        if message.text and message.text.startswith('/'):
            bot.send_message(
                message.chat.id, 
                "❓ Неизвестная команда. Используйте /start для начала работы."
            )
        else:
            bot.send_message(
                message.chat.id, 
                "🤖 Извините, я не понял ваше сообщение. Используйте меню или команду /start для навигации."
            )
        
        logger.info(f"Fallback handler triggered for user {message.from_user.id}: {message.text[:50]}...")
        
    except Exception as e:
        logger.error(f"Error in fallback handler: {e}")

# Логируем запуск бота
log_bot_startup(logger)


# Запуск бота с улучшенной обработкой ошибок
try:
    logger.info("🚀 Starting bot polling...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
except KeyboardInterrupt:
    logger.info("⚠️ Bot stopped by user (Ctrl+C)")
    log_bot_shutdown(logger)
    # Останавливаем StateManager
    try:
        state_manager.stop()
    except Exception as e:
        logger.warning(f"Ошибка при остановке FSM: {e}")
except Exception as e:
    # Обработка ошибки 409 (Conflict: terminated by other getUpdates request)
    if isinstance(e, telebot.apihelper.ApiTelegramException) and '409' in str(e):
        logger.error("❌ [FATAL] 409 Conflict: Бот уже запущен где-то ещё! Завершаем работу.")
        print("❌ [FATAL] 409 Conflict: Бот уже запущен где-то ещё! Завершаем работу.")
        log_bot_shutdown(logger)
        try:
            state_manager.stop()
        except Exception as stop_error:
            logger.warning(f"Ошибка при остановке FSM: {stop_error}")
        sys.exit(1)
    
    error_msg = handle_exception(e, logger, "Bot polling")
    logger.error(f"❌ {error_msg}")
    log_error(logger, "Ошибка при запуске polling", e)
    log_bot_shutdown(logger)
    try:
        state_manager.stop()
    except Exception as stop_error:
        logger.warning(f"Ошибка при остановке FSM: {stop_error}")
