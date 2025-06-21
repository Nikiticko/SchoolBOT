# === handlers/commands.py ===
from telebot import types
from utils.menu import get_main_menu, get_admin_menu
from data.db import get_application_by_tg_id, format_date_for_display, get_active_courses
from handlers.admin import is_admin
from utils.logger import log_user_action, log_error


def register(bot, logger):  

    @bot.message_handler(commands=["start"])
    def handle_start(message):
        try:
            if is_admin(message.from_user.id):
                markup = get_admin_menu()
                welcome = "👋 Добро пожаловать, администратор!\n\nВыберите действие из админ-меню:"
            else:
                markup = get_main_menu()
                welcome = "👋 Добро пожаловать! Я бот для записи на занятия.\n\n📋 Выберите действие:"
            bot.send_message(
                message.chat.id,
                welcome,
                reply_markup=markup
            )
            log_user_action(logger, message.from_user.id, "start_command")
        except Exception as e:
            log_error(logger, e, f"Start command for user {message.from_user.id}")

    def _handle_my_lesson_logic(chat_id, show_menu=False):
        """Общая логика для обработки запроса информации о занятии"""
        try:
            app = get_application_by_tg_id(str(chat_id))
            
            if not app:
                return "Вы ещё не регистрировались. Нажмите «📋 Записаться».", show_menu
            
            course = app[6]
            date = app[7]
            link = app[8]
            
            if date and link:
                formatted_date = format_date_for_display(date)
                msg = f"📅 Дата: {formatted_date}\n📘 Курс: {course}\n🔗 Ссылка: {link}"
            else:
                msg = "📝 Ваша заявка принята. Ожидайте назначения урока."
            
            return msg, show_menu
        except Exception as e:
            log_error(logger, e, f"My lesson logic for user {chat_id}")
            return "❌ Произошла ошибка при получении информации о занятии.", show_menu

    @bot.message_handler(commands=["my_lesson"])
    def handle_my_lesson_command(message):
        try:
            msg, _ = _handle_my_lesson_logic(message.chat.id)
            bot.send_message(message.chat.id, msg)
            log_user_action(logger, message.from_user.id, "my_lesson_command")
        except Exception as e:
            log_error(logger, e, f"My lesson command for user {message.from_user.id}")

    @bot.message_handler(commands=["help"])
    def handle_help(message):
        try:
            help_text = (
                "🤖 Доступные команды:\n\n"
                "/start - Главное меню\n"
                "/my_lesson - Информация о моем занятии\n"
                "/help - Эта справка\n\n"
                "📞 По всем вопросам обращайтесь к администратору."
            )
            bot.send_message(message.chat.id, help_text)
            log_user_action(logger, message.from_user.id, "help_command")
        except Exception as e:
            log_error(logger, e, f"Help command for user {message.from_user.id}")

    @bot.message_handler(func=lambda m: m.text == "📅 Мое занятие")
    def handle_my_lesson_button(message):
        try:
            msg, show_menu = _handle_my_lesson_logic(message.chat.id, show_menu=True)
            if show_menu:
                bot.send_message(message.chat.id, msg, reply_markup=get_main_menu())
            else:
                bot.send_message(message.chat.id, msg)
            log_user_action(logger, message.from_user.id, "my_lesson_button")
        except Exception as e:
            log_error(logger, e, f"My lesson button for user {message.from_user.id}")

    @bot.message_handler(func=lambda m: m.text == "ℹ️ О преподавателе")
    def handle_about(message):
        try:
            bot.send_message(message.chat.id, "🧑‍🏫 Преподаватель: Никита\nОпыт: 3 года\nPython для детей 10–18 лет")
            log_user_action(logger, message.from_user.id, "about_teacher")
        except Exception as e:
            log_error(logger, e, f"About teacher for user {message.from_user.id}")

    @bot.message_handler(func=lambda m: m.text == "💰 Цены и форматы")
    def handle_prices(message):
        try:
            bot.send_message(message.chat.id, "💰 Индивидуально: 600₽\n👥 Группа: 400₽\nФормат: Zoom/Discord")
            log_user_action(logger, message.from_user.id, "prices_info")
        except Exception as e:
            log_error(logger, e, f"Prices info for user {message.from_user.id}")

    @bot.message_handler(func=lambda m: m.text == "📚 Доступные курсы")
    def handle_courses(message):
        try:
            courses = get_active_courses()
            if not courses:
                bot.send_message(message.chat.id, "Курсы временно недоступны.")
                return

            markup = types.InlineKeyboardMarkup()
            for course in courses:
                course_id, name, description, active = course
                markup.add(types.InlineKeyboardButton(name, callback_data=f"course_info:{course_id}"))

            bot.send_message(message.chat.id, "Выберите интересующий курс:", reply_markup=markup)
            log_user_action(logger, message.from_user.id, "courses_list", f"available: {len(courses)}")
        except Exception as e:
            log_error(logger, e, f"Courses list for user {message.from_user.id}")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("course_info:"))
    def show_course_info(call):
        try:
            course_id = int(call.data.split(":")[1])
            courses = get_active_courses()
            course = next((c for c in courses if c[0] == course_id), None)

            if course:
                name = course[1]
                description = course[2]
                msg = f"📘 *{name}*\n\n📝 {description}"
                bot.send_message(call.message.chat.id, msg, parse_mode="Markdown", reply_markup=get_main_menu(call.message.chat.id))
                log_user_action(logger, call.from_user.id, "course_info_viewed", f"course: {name}")
            else:
                bot.send_message(call.message.chat.id, "⚠️ Курс не найден.", reply_markup=get_main_menu(call.message.chat.id))
                log_user_action(logger, call.from_user.id, "course_not_found", f"course_id: {course_id}")
        except Exception as e:
            log_error(logger, e, f"Course info for user {call.from_user.id}")
