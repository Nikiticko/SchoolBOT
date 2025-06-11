# === services/sheets_service.py ===
from telebot import types
from state.users import user_data, used_contacts, chat_contact_map, pending
from utils.menu import get_main_menu

import gspread
import os

SERVICE_ACCOUNT_FILE = "creds.json"
GOOGLE_SHEET_NAME = "Заявки на обучение"

# Подключение к Google Sheets
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
        str(chat_id),                                 # ID
        data.get('name', '').strip(),                # Имя
        data.get('age', '').strip(),                 # Возраст
        data.get('goal', '').strip(),                # Цель
        data.get('contact', '').strip(),             # Контакты
        data.get('course', '').strip(),              # Курс
        "",                                           # Дата занятия
        ""                                            # Ссылка на занятие
    ]

    try:
        worksheet.append_row(row)
    except Exception as e:
        bot.send_message(chat_id, "Произошла ошибка при сохранении данных. Попробуйте позже.")
        print("Ошибка при добавлении строки:", e)
        return

    contact = data['contact']
    used_contacts.add(contact)
    chat_contact_map[chat_id] = contact
    pending[contact] = {"chat_id": chat_id}
    del user_data[chat_id]

    bot.send_message(chat_id, "✅ Ваша заявка принята. Ожидайте расписание своего урока.",
                     reply_markup=get_main_menu())
