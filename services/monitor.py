import threading
import time
from services.sheets_service import get_user_row
from state.users import pending
from telebot import types

def monitor_loop(bot):
    while True:
        for contact, info in list(pending.items()):
            row = get_user_row(contact)
            if not row:
                continue
            course = row[4] if len(row) > 4 else ""
            date = row[5] if len(row) > 5 else ""
            link = row[6] if len(row) > 6 else ""
            if date.strip():
                msg = f"Ваш урок назначен на {date.strip()}\nКурс: {course.strip()}\nСсылка: {link.strip()}"
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.add("📅 Мое занятие")
                bot.send_message(info["chat_id"], msg, reply_markup=markup)
                pending.pop(contact, None)
        time.sleep(30)

def start_monitoring(bot):
    threading.Thread(target=monitor_loop, args=(bot,), daemon=True).start()
