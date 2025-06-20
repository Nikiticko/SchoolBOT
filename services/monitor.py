import threading
import time
from state.users import pending
from telebot import types
from utils.menu import get_main_menu
from data.db import get_application_by_tg_id, update_application_lesson

CHECK_INTERVAL = 60  # интервал в секундах

def monitor_loop(bot):
    while True:
        try:
            for user_id, info in list(pending.items()):
                app = get_application_by_tg_id(str(user_id))
                if not app or len(app) < 9:
                    continue

                course = app[6]
                date = app[7]
                link = app[8]
                status = app[9]

                if date and link and status.lower() == "ожидает":
                    msg = (
                        f"📅 Ваш урок назначен: {date}\n"
                        f"📘 Курс: {course}\n"
                        f"🔗 Ссылка: {link}"
                    )
                    bot.send_message(user_id, msg, reply_markup=get_main_menu())

                    update_application_lesson(app[0], date, link)
                    pending.pop(user_id, None)

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print("❌ Ошибка мониторинга базы данных:", e)
            time.sleep(CHECK_INTERVAL)

def start_monitoring(bot):
    threading.Thread(target=monitor_loop, args=(bot,), daemon=True).start()
