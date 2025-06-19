import threading
import time
from services.sheets_service import get_user_row, update_status_by_user_id
from state.users import pending
from telebot import types
from utils.menu import get_main_menu

CHECK_INTERVAL = 60  # интервал в секундах

def monitor_loop(bot):
    while True:
        try:
            for user_id, info in list(pending.items()):
                row = get_user_row(str(user_id))
                if not row or len(row) < 9:
                    continue

                course = row[5].strip()    # Курс
                date = row[6].strip()      # Дата занятия
                link = row[7].strip()      # Ссылка
                status = row[8].strip()    # Статус

                if date and link and status.lower() == "новая":
                    msg = (
                        f"📅 Ваш урок назначен: {date}\n"
                        f"📘 Курс: {course}\n"
                        f"🔗 Ссылка: {link}"
                    )
                    bot.send_message(user_id, msg, reply_markup=get_main_menu())

                    update_status_by_user_id(str(user_id), "Назначена")
                    pending.pop(user_id, None)

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print("❌ Ошибка мониторинга таблицы:", e)
            time.sleep(CHECK_INTERVAL)

def start_monitoring(bot):
    threading.Thread(target=monitor_loop, args=(bot,), daemon=True).start()
