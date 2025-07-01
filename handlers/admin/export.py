from telebot import types
from data.db import get_all_applications, get_all_archive, get_all_contacts, get_all_reviews
from config import ADMIN_ID
import openpyxl
import os
from datetime import datetime

def register_export_handlers(bot, logger):
    def is_admin(user_id):
        return str(user_id) == str(ADMIN_ID)

    @bot.message_handler(func=lambda m: m.text == "⬇️ Выгрузить данные" and is_admin(m.from_user.id))
    def handle_export_data(message):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Заявки", callback_data="export_applications"))
        markup.add(types.InlineKeyboardButton("Архив", callback_data="export_archive"))
        markup.add(types.InlineKeyboardButton("Обращения", callback_data="export_contacts"))
        markup.add(types.InlineKeyboardButton("Отзывы", callback_data="export_reviews"))
        bot.send_message(message.chat.id, "Выберите, что выгрузить:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data in ["export_applications", "export_archive", "export_contacts", "export_reviews"])
    def handle_export_choice(call):
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "Нет прав")
            return
        try:
            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            if call.data == "export_applications":
                data = get_all_applications()
                filename = f"applications_{now}.xlsx"
                headers = ["ID", "TG ID", "Родитель", "Ученик", "Возраст", "Контакт", "Курс", "Дата", "Ссылка", "Статус", "Создано", "Напоминание"]
            elif call.data == "export_archive":
                data = get_all_archive()
                filename = f"archive_{now}.xlsx"
                headers = ["ID", "TG ID", "Родитель", "Ученик", "Возраст", "Контакт", "Курс", "Дата", "Ссылка", "Статус", "Создано", "Напоминание"]
            elif call.data == "export_contacts":
                data = get_all_contacts()
                filename = f"contacts_{now}.xlsx"
                headers = ["ID", "TG ID", "Имя", "Контакт", "Вопрос", "Статус", "Создано"]
            elif call.data == "export_reviews":
                data = get_all_reviews()
                filename = f"reviews_{now}.xlsx"
                headers = ["ID", "TG ID", "Курс", "Оценка", "Комментарий", "Дата", "Статус"]
            else:
                bot.answer_callback_query(call.id, "Неизвестный тип выгрузки")
                return
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.append(headers)
            for row in data:
                ws.append(list(row))
            wb.save(filename)
            with open(filename, "rb") as f:
                caption = f"📊 {filename}\n\n⚠️ <b>Внимание:</b> Файл будет автоматически удален через 24 часа\n💾 Сохраните его, если он вам нужен надолго"
                bot.send_document(call.message.chat.id, f, caption=caption, parse_mode="HTML")
            os.remove(filename)
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ Ошибка при экспорте: {str(e)}") 