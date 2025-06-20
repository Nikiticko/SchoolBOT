# === handlers/commands.py ===
from telebot import types
from utils.menu import get_main_menu
from data.db import get_application_by_tg_id
from handlers.admin import is_admin
from data.db import get_active_courses
from utils.menu import get_main_menu, get_admin_menu


def register(bot):  

    @bot.message_handler(commands=["start"])
    def handle_start(message):
        chat_id = message.chat.id

        if is_admin(chat_id):
            bot.send_message(chat_id, "👋 Добро пожаловать в админ-панель!", reply_markup=get_admin_menu())
        else:
            bot.send_message(chat_id, "👋 Добро пожаловать! Выберите действие:", reply_markup=get_main_menu(chat_id))


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
        courses = get_active_courses()
        if not courses:
            bot.send_message(message.chat.id, "Курсы временно недоступны.")
            return

        markup = types.InlineKeyboardMarkup()
        for course in courses:
            course_id, name, description, active = course
            markup.add(types.InlineKeyboardButton(name, callback_data=f"course_info:{course_id}"))

        bot.send_message(message.chat.id, "Выберите интересующий курс:", reply_markup=markup)
    
    
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("course_info:"))
    def show_course_info(call):
        course_id = int(call.data.split(":")[1])
        courses = get_active_courses()
        course = next((c for c in courses if c[0] == course_id), None)

        if course:
            name = course[1]
            description = course[2]
            msg = f"📘 *{name}*\n\n📝 {description}"
            bot.send_message(call.message.chat.id, msg, parse_mode="Markdown", reply_markup=get_main_menu(call.message.chat.id))
        else:
            bot.send_message(call.message.chat.id, "⚠️ Курс не найден.", reply_markup=get_main_menu(call.message.chat.id))
