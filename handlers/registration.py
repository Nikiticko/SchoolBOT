from telebot import types

from state.users import user_data
from utils.menu import get_main_menu, get_admin_menu, get_cancel_button, handle_cancel_action
from handlers.admin import notify_admin_new_application, is_admin
from data.db import (
    add_application,
    get_application_by_tg_id,
    get_active_courses,
    get_archive_count_by_tg_id,
    format_date_for_display,
    get_cancelled_count_by_tg_id,
    get_finished_count_by_tg_id
)
from utils.logger import log_user_action, log_error, setup_logger
from utils.security import check_user_security, validate_user_input, security_manager


def handle_existing_registration(bot, chat_id):
    markup = get_main_menu()
    bot.send_message(chat_id, "📝 Вы уже оставляли заявку. Ожидайте назначения урока.", reply_markup=markup)


def register(bot, logger):
    @bot.message_handler(func=lambda m: m.text == "📋 Записаться")
    def handle_signup(message):
        try:
            chat_id = message.chat.id

            # Проверка безопасности
            security_ok, error_msg = check_user_security(message.from_user.id, "signup")
            if not security_ok:
                bot.send_message(chat_id, f"🚫 {error_msg}")
                return

            # 1. Проверка отмен
            if get_cancelled_count_by_tg_id(str(chat_id)) >= 2:
                bot.send_message(chat_id, "🚫 У вас 2 или более отменённых заявок или уроков. Запись невозможна. Свяжитесь с администратором.")
                return

            # 2. Проверка завершённых уроков
            if get_finished_count_by_tg_id(str(chat_id)) >= 1:
                bot.send_message(chat_id, "✅ Вы уже проходили пробный урок. Для дальнейших занятий свяжитесь с администратором.")
                return

            # 3. Архивный лимит
            if get_archive_count_by_tg_id(str(chat_id)) >= 2:
                bot.send_message(chat_id, "🚫 Вы уже записывались несколько раз. Пожалуйста, свяжитесь с администратором.")
                return

            # 4. Наличие курсов
            if not get_active_courses():
                bot.send_message(chat_id, "⚠️ Сейчас запись недоступна. Курсы временно неактивны.")
                return

            # 5. Текущая регистрация
            if user_data.get(chat_id, {}).get("in_progress"):
                bot.send_message(chat_id, "⏳ Пожалуйста, завершите текущую регистрацию.")
                return

            # 6. Уже есть активная заявка
            app = get_application_by_tg_id(str(chat_id))
            if app:
                course, date, link, status = app[6], app[7], app[8], app[9]
                if status != "Назначено":
                    handle_existing_registration(bot, chat_id)
                else:
                    formatted_date = format_date_for_display(date)
                    bot.send_message(chat_id, f"Вы уже записаны на занятие:\n📅 {formatted_date}\n📘 {course}\n🔗 {link}", reply_markup=get_main_menu())
                return

            # Начало регистрации
            user_data[chat_id] = {
                "in_progress": True,
                "stage": "parent_name"
            }
            bot.send_message(chat_id, "Введите ваше имя (имя родителя):", reply_markup=get_cancel_button())
            bot.register_next_step_handler(message, process_parent_name)
            logger.info(f"User {chat_id} started registration")
        except Exception as e:
            log_error(logger, e, f"Error in handle_signup for user {message.chat.id}")

    def process_parent_name(message):
        chat_id = message.chat.id
        
        # Проверка безопасности
        security_ok, error_msg = check_user_security(message.from_user.id, "process_parent_name")
        if not security_ok:
            bot.send_message(chat_id, f"🚫 {error_msg}")
            return
        
        # Проверяем отмену
        if message.text == "🔙 Отмена":
            handle_cancel_action(bot, message, "регистрация", logger)
            return
            
        if user_data.get(chat_id, {}).get("stage") != "parent_name":
            return
        
        # Валидация имени
        is_valid, error_msg = validate_user_input(message.text, "name")
        if not is_valid:
            bot.send_message(chat_id, f"❌ {error_msg}\nПопробуйте еще раз:")
            bot.register_next_step_handler(message, process_parent_name)
            return
            
        user_data[chat_id]["parent_name"] = message.text.strip()
        user_data[chat_id]["stage"] = "student_name"
        bot.send_message(chat_id, "Введите имя ученика:", reply_markup=get_cancel_button())
        bot.register_next_step_handler(message, process_student_name)

    def process_student_name(message):
        chat_id = message.chat.id
        
        # Проверка безопасности
        security_ok, error_msg = check_user_security(message.from_user.id, "process_student_name")
        if not security_ok:
            bot.send_message(chat_id, f"🚫 {error_msg}")
            return
        
        # Проверяем отмену
        if message.text == "🔙 Отмена":
            handle_cancel_action(bot, message, "регистрация", logger)
            return
            
        if user_data.get(chat_id, {}).get("stage") != "student_name":
            return
        
        # Валидация имени
        is_valid, error_msg = validate_user_input(message.text, "name")
        if not is_valid:
            bot.send_message(chat_id, f"❌ {error_msg}\nПопробуйте еще раз:")
            bot.register_next_step_handler(message, process_student_name)
            return
            
        user_data[chat_id]["student_name"] = message.text.strip()
        user_data[chat_id]["stage"] = "age"
        bot.send_message(chat_id, "Введите возраст ученика:", reply_markup=get_cancel_button())
        bot.register_next_step_handler(message, process_age)

    def process_age(message):
        chat_id = message.chat.id
        
        # Проверка безопасности
        security_ok, error_msg = check_user_security(message.from_user.id, "process_age")
        if not security_ok:
            bot.send_message(chat_id, f"🚫 {error_msg}")
            return
        
        # Проверяем отмену
        if message.text == "🔙 Отмена":
            handle_cancel_action(bot, message, "регистрация", logger)
            return
            
        if user_data.get(chat_id, {}).get("stage") != "age":
            return
        
        # Валидация возраста
        is_valid, error_msg = validate_user_input(message.text, "age")
        if not is_valid:
            bot.send_message(chat_id, f"❌ {error_msg}\nПопробуйте еще раз:")
            bot.register_next_step_handler(message, process_age)
            return
            
        user_data[chat_id]["age"] = message.text.strip()
        user_data[chat_id]["stage"] = "course"

        courses = get_active_courses()
        if not courses:
            bot.send_message(chat_id, "⚠️ Курсы временно недоступны.")
            return

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for course in courses:
            markup.add(course[1])
        markup.add("🔙 Отмена")
        bot.send_message(chat_id, "Выберите курс:", reply_markup=markup)
        bot.register_next_step_handler(message, process_course)

    def process_course(message):
        chat_id = message.chat.id
        
        # Проверка безопасности
        security_ok, error_msg = check_user_security(message.from_user.id, "process_course")
        if not security_ok:
            bot.send_message(chat_id, f"🚫 {error_msg}")
            return
        
        # Проверяем отмену
        if message.text == "🔙 Отмена":
            handle_cancel_action(bot, message, "регистрация", logger)
            return

        if user_data.get(chat_id, {}).get("stage") != "course":
            return

        selected = message.text.strip()
        courses = get_active_courses()
        course_names = [c[1] for c in courses]

        if selected not in course_names:
            bot.send_message(chat_id, "Пожалуйста, выберите курс из списка.")
            return bot.register_next_step_handler(message, process_course)

        user_data[chat_id]["course"] = selected
        user = message.from_user
        user_data[chat_id]["contact"] = f"@{user.username}" if user.username else ""
        user_data[chat_id]["stage"] = "confirmation"
        send_confirmation(bot, chat_id)

    def send_confirmation(bot, chat_id):
        data = user_data.get(chat_id)
        if not data:
            return

        summary = (
            f"Проверьте введённые данные:\n\n"
            f"👤 Родитель: {data.get('parent_name')}\n"
            f"🧒 Ученик: {data.get('student_name')}\n"
            f"🎂 Возраст: {data.get('age')}\n"
            f"📘 Курс: {data.get('course')}\n"
            f"📞 Контакт: {data.get('contact') or 'не указан'}\n\n"
            "Подтвердите:"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_registration"),
            types.InlineKeyboardButton("❌ Отменить", callback_data="cancel_registration")
        )
        bot.send_message(chat_id, summary, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data in ["confirm_registration", "cancel_registration"])
    def handle_confirmation(call):
        chat_id = call.message.chat.id

        # Проверка безопасности
        security_ok, error_msg = check_user_security(call.from_user.id, "confirm_registration")
        if not security_ok:
            bot.answer_callback_query(call.id, f"🚫 {error_msg}")
            return

        if call.data == "cancel_registration":
            handle_cancel_action(bot, call.message, "регистрация", logger)
            return

        if user_data.get(chat_id, {}).get("stage") != "confirmation":
            bot.send_message(chat_id, "⚠️ Подтверждение недоступно. Начните заново.")
            return

        data = user_data[chat_id]
        add_application(
            tg_id=str(chat_id),
            parent_name=data["parent_name"],
            student_name=data["student_name"],
            age=data["age"],
            contact=data["contact"],
            course=data["course"]
        )
        notify_admin_new_application(bot, data)
        bot.send_message(chat_id, "✅ Ваша заявка отправлена!", reply_markup=get_main_menu())
        user_data.pop(chat_id, None)
        logger.info(f"User {chat_id} submitted application")


def register_handlers(bot):
    """Регистрация обработчиков регистрации"""
    logger = setup_logger('registration')
    register(bot, logger)
