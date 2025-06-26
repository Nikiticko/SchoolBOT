import threading
import time
from state.users import pending
from telebot import types
from utils.menu import get_main_menu
from data.db import get_application_by_tg_id, update_application_lesson
from config import CHECK_INTERVAL
from utils.logger import log_error, log_user_action

def monitor_loop(bot, logger):
    """Основной цикл мониторинга заявок"""
    while True:
        try:
            logger.debug(f"🔍 Checking {len(pending)} pending notifications...")
            
            for user_id, info in list(pending.items()):
                try:
                    app = get_application_by_tg_id(str(user_id))
                    if not app or len(app) < 9:
                        logger.warning(f"⚠️ Invalid application data for user {user_id}")
                        continue

                    course = app[6]
                    date = app[7]
                    link = app[8]

                    if date and link:
                        msg = (
                            f"📅 Ваш урок назначен: {date}\n"
                            f"📘 Курс: {course}\n"
                            f"🔗 Ссылка: {link}"
                        )
                        bot.send_message(user_id, msg, reply_markup=get_main_menu())
                        update_application_lesson(app[0], date, link)
                        pending.pop(user_id, None)
                        logger.info(f"✅ Lesson notification sent to user {user_id}")
                        log_user_action(logger, user_id, "lesson_notification_sent", f"course: {course}")

                except Exception as e:
                    log_error(logger, e, f"Processing user {user_id} in monitoring")
                    # Удаляем проблемного пользователя из очереди
                    pending.pop(user_id, None)

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            log_error(logger, e, "Monitoring loop")
            time.sleep(CHECK_INTERVAL)

def start_monitoring(bot, logger):
    """Запуск мониторинга в отдельном потоке"""
    try:
        thread = threading.Thread(target=monitor_loop, args=(bot, logger), daemon=True)
        thread.start()
        logger.info("✅ Monitoring thread started successfully")
    except Exception as e:
        log_error(logger, e, "Starting monitoring thread")
        raise
