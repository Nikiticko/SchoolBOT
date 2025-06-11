# === services/monitor.py ===
import threading
import time
from services.sheets_service import get_user_row
from state.users import pending
from telebot import types
from utils.menu import get_main_menu

def monitor_loop(bot):
    while True:
        try:
            for user_id, info in list(pending.items()):
                row = get_user_row(str(user_id))
                if not row:
                    continue
                course = row[5] if len(row) > 5 else ""
                date = row[6] if len(row) > 6 else ""
                link = row[7] if len(row) > 7 else ""
                if date.strip():
                    msg = (
                        f"📅 Ваш урок назначен: {date.strip()}\n"
                        f"📘 Курс: {course.strip()}\n"
                        f"🔗 Ссылка: {link.strip()}"
                    )
                    bot.send_message(user_id, msg, reply_markup=get_main_menu())
                    pending.pop(user_id, None)
            time.sleep(30)
        except Exception as e:
            print("Ошибка мониторинга таблицы:", e)
            time.sleep(30)

def start_monitoring(bot):
    threading.Thread(target=monitor_loop, args=(bot,), daemon=True).start()
