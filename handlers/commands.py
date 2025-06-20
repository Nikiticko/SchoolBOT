# === handlers/commands.py ===
from telebot import types
from utils.menu import get_main_menu
from data.db import get_application_by_tg_id
from handlers.admin import is_admin

def register(bot):  
    @bot.message_handler(commands=["start"])
    def handle_start(message):
        chat_id = message.chat.id

        if is_admin(chat_id):
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.row("📋 Список заявок", "📚 Редактировать курсы")
            bot.send_message(chat_id, "👋 Добро пожаловать в админ-панель!", reply_markup=markup)
            return

        # Обычный пользователь — стандартное меню
        bot.send_message(chat_id, "Добро пожаловать! Выберите действие:",
                         reply_markup=get_main_menu(chat_id))

    @bot.message_handler(func=lambda m: m.text == "📅 Мое занятие")
    def handle_my_lesson(message):
        chat_id = message.chat.id
        app = get_application_by_tg_id(str(chat_id))

        if app:
            course = app[6]
            date = app[7]
            link = app[8]
            if date and link:
                msg = f"📅 Дата: {date}\n📘 Курс: {course}\n🔗 Ссылка: {link}"
            else:
                msg = "📝 Ваша заявка принята. Ожидайте назначения урока."
        else:
            msg = "Вы ещё не регистрировались. Нажмите «📋 Записаться»."

        bot.send_message(chat_id, msg, reply_markup=get_main_menu())

    @bot.message_handler(func=lambda m: m.text == "ℹ️ О преподавателе")
    def handle_about(message):
        bot.send_message(message.chat.id, "🧑‍🏫 Преподаватель: Никита\nОпыт: 3 года\nPython для детей 10–18 лет")

    @bot.message_handler(func=lambda m: m.text == "💰 Цены и форматы")
    def handle_prices(message):
        bot.send_message(message.chat.id, "💰 Индивидуально: 600₽\n👥 Группа: 400₽\nФормат: Zoom/Discord")

    @bot.message_handler(func=lambda m: m.text == "📚 Доступные курсы")
    def handle_courses(message):
        bot.send_message(message.chat.id, "📘 Python с нуля (10–14 лет)\n📗 Подготовка к ЕГЭ/ОГЭ\n📙 Проектное программирование")
