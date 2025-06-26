import threading
import time
from state.users import pending
from telebot import types
from utils.menu import get_main_menu
from data.db import get_application_by_tg_id, update_application_lesson, get_upcoming_lessons, mark_reminder_sent
from config import CHECK_INTERVAL
from utils.logger import log_error, log_user_action

def monitor_loop(bot, logger):
    """Основной цикл мониторинга заявок и напоминаний"""
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

            # --- Напоминания о предстоящем уроке ---
            try:
                lessons = get_upcoming_lessons(minutes=30)
                for app in lessons:
                    app_id = app[0]
                    tg_id = app[1]
                    parent_name = app[2]
                    student_name = app[3]
                    course = app[6]
                    lesson_date = app[7]
                    lesson_link = app[8]
                    reminder_sent = app[11]
                    # Форматируем дату
                    from data.db import format_date_for_display
                    import datetime
                    now = datetime.datetime.now()
                    # Универсальный парсер даты (дублируем для лога)
                    dt = None
                    parse_error = None
                    try:
                        dt = datetime.datetime.fromisoformat(lesson_date)
                    except Exception as e:
                        try:
                            dt = datetime.datetime.strptime(lesson_date, "%Y-%m-%d %H:%M:%S")
                        except Exception as e2:
                            try:
                                dt = datetime.datetime.strptime(lesson_date, "%Y-%m-%d %H:%M:%S.%f")
                            except Exception as e3:
                                parse_error = f"fromisoformat: {e}; strptime1: {e2}; strptime2: {e3}"
                    logger.info(f"[DEBUG] app_id={app_id}, tg_id={tg_id}, lesson_date={lesson_date}, now={now}, parsed_dt={dt}, parse_error={parse_error}, reminder_sent={reminder_sent}, lesson_link={lesson_link}")
                    if not dt:
                        continue
                    delta = (dt - now).total_seconds() / 60
                    logger.info(f"[DEBUG] app_id={app_id}, delta={delta}")
                    if not lesson_link:
                        logger.info(f"[DEBUG] app_id={app_id}: lesson_link пустой, пропуск")
                        continue
                    if not (0 < delta <= 30):
                        logger.info(f"[DEBUG] app_id={app_id}: delta не в диапазоне, пропуск")
                        continue
                    msg = (
                        f"⏰ Напоминание! Ваш урок начнётся через 30 минут или меньше.\n"
                        f"📅 Дата: {format_date_for_display(lesson_date)}\n"
                        f"📘 Курс: {course}\n"
                        f"🔗 Ссылка: {lesson_link}"
                    )
                    try:
                        bot.send_message(tg_id, msg)
                        mark_reminder_sent(app_id)
                        logger.info(f"[REMINDER] Sent to user {tg_id} for lesson {app_id}")
                    except Exception as e:
                        logger.error(f"[REMINDER] Failed to send to {tg_id}: {e}")
            except Exception as e:
                logger.error(f"[REMINDER] Error in reminder logic: {e}")

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
