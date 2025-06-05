from telebot import types
from state.users import user_data, used_contacts, chat_contact_map, pending
from utils.menu import get_main_menu

import gspread
import os

SERVICE_ACCOUNT_FILE = "creds.json"
GOOGLE_SHEET_NAME = "Заявки на обучение"

gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
sh = gc.open(GOOGLE_SHEET_NAME)
worksheet = sh.sheet1

def get_user_row(contact):
    try:
        cell = worksheet.find(contact)
        return worksheet.row_values(cell.row) if cell else None
    except Exception:
        return None


def finish_registration(bot, chat_id):
    if chat_id not in user_data:
        return
    data = user_data[chat_id]
    row = [
        data.get('name', '').strip(),
        data.get('age', '').strip(),
        data.get('goal', '').strip(),
        data.get('contact', '').strip(),
        data.get('course', '').strip(),
        "",  # дата занятия
        ""   # ссылка на занятие
    ]
    try:
        worksheet.append_row(row)
    except Exception as e:
        bot.send_message(chat_id, "Произошла ошибка при сохранении данных. Попробуйте позже.")
        return
    used_contacts.add(data['contact'])
    chat_contact_map[chat_id] = data['contact']
    pending[data['contact']] = {"chat_id": chat_id}
    markup = get_main_menu()
    bot.send_message(chat_id, "Спасибо! Ваша заявка принята. Ожидайте расписание своего урока.", reply_markup=markup)
    user_data.pop(chat_id, None)
