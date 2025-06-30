from telebot import types
import time

from state.users import (
    user_data, start_registration, is_registration_in_progress, 
    get_registration_stage, update_registration_stage, 
    get_registration_start_time, cleanup_expired_registrations, clear_user_data
)
from utils.menu import get_main_menu, get_admin_menu, get_cancel_button, handle_cancel_action, get_appropriate_menu
from data.db import (
    add_application,
    get_application_by_tg_id,
    get_active_courses,
    get_archive_count_by_tg_id,
    format_date_for_display,
    get_cancelled_count_by_tg_id,
    get_finished_count_by_tg_id,
    is_user_banned,
    get_ban_reason
)
from utils.logger import log_user_action, log_error, setup_logger
from utils.security import check_user_security, validate_user_input, security_manager
from utils.decorators import error_handler, ensure_text_message, ensure_stage
from config import ADMIN_ID


def handle_existing_registration(bot, chat_id):
    markup = get_appropriate_menu(chat_id)
    bot.send_message(chat_id, "📝 Вы уже оставляли заявку. Ожидайте назначения урока.", reply_markup=markup)


def register(bot, logger):
    @bot.message_handler(func=lambda m: m.text == "📋 Записаться")
    @error_handler()
    def handle_signup(message):
        chat_id = message.chat.id
        
        # Проверка безопасности
        security_ok, error_msg = check_user_security(message.from_user.id, "signup")
        if not security_ok:
            bot.send_message(chat_id, f"🚫 {error_msg}")
            return
        # ИСПРАВЛЕНО: Проверка на существующие активные заявки
        existing_app = get_application_by_tg_id(str(chat_id))
        if existing_app:
            status = existing_app[9]  # status
            if status == "Ожидает":
                bot.send_message(chat_id, "⚠️ У вас уже есть активная заявка на рассмотрении. Дождитесь ответа администратора или отмените текущую заявку.")
                return
            elif status == "Назначено":
                course, date, link = existing_app[6], existing_app[7], existing_app[8]
                formatted_date = format_date_for_display(date)
                bot.send_message(chat_id, f"✅ У вас уже назначен урок:\n📅 {formatted_date}\n📘 {course}\n🔗 {link}", reply_markup=get_appropriate_menu(chat_id))
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
        # 5. ИСПРАВЛЕНО: Проверка незавершенной регистрации
        if is_registration_in_progress(chat_id):
            # Проверяем таймаут регистрации
            start_time = get_registration_start_time(chat_id)
            if time.time() - start_time > 30 * 60:  # 30 минут
                # Очищаем просроченную регистрацию
                clear_user_data(chat_id)
                bot.send_message(chat_id, "⏰ Предыдущая регистрация истекла. Начинаем заново.")
            else:
                # Показываем возможность продолжить регистрацию
                current_stage = get_registration_stage(chat_id)
                stage_messages = {
                    "parent_name": "Введите ваше имя (имя родителя):",
                    "student_name": "Введите имя ученика:",
                    "age": "Введите возраст ученика:",
                    "contact": "Введите контактный номер:",
                    "course": "Выберите курс:"
                }
                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.add(
                    types.InlineKeyboardButton("🔄 Продолжить", callback_data="continue_registration"),
                    types.InlineKeyboardButton("🔄 Начать заново", callback_data="restart_registration")
                )
                current_message = stage_messages.get(current_stage, "Продолжите регистрацию:")
                msg = bot.send_message(chat_id, f"⏳ У вас есть незавершенная регистрация.\n\n{current_message}", reply_markup=markup)
                bot.register_next_step_handler(msg, process_parent_name)
                return
        # Начало новой регистрации
        start_registration(chat_id)
        msg = bot.send_message(chat_id, "Введите ваше имя (имя родителя):", reply_markup=get_cancel_button())
        bot.register_next_step_handler(msg, process_parent_name)
        logger.info(f"User {chat_id} started registration")

    @ensure_text_message
    @ensure_stage(lambda m: get_registration_stage(m.chat.id), "parent_name", error_message="Сначала введите имя родителя.")
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
            
        # Проверяем таймаут
        start_time = get_registration_start_time(chat_id)
        if time.time() - start_time > 30 * 60:  # 30 минут
            clear_user_data(chat_id)
            bot.send_message(chat_id, "⏰ Время регистрации истекло. Начните заново.", reply_markup=get_appropriate_menu(chat_id))
            return
        
        # Валидация имени
        is_valid, error_msg = validate_user_input(message.text, "name")
        if not is_valid:
            msg = bot.send_message(chat_id, f"❌ {error_msg}\nПопробуйте еще раз:", reply_markup=get_cancel_button())
            bot.register_next_step_handler(msg, process_parent_name)
            return
            
        # ИСПРАВЛЕНО: Используем StateManager
        from state.users import update_user_data
        update_user_data(chat_id, parent_name=message.text.strip())
        update_registration_stage(chat_id, "student_name")
        msg = bot.send_message(chat_id, "Введите имя ученика:", reply_markup=get_cancel_button())
        bot.register_next_step_handler(msg, process_student_name)

    @ensure_text_message
    @ensure_stage(lambda m: get_registration_stage(m.chat.id), "student_name", error_message="Сначала введите имя ученика.")
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
            
        # Проверяем таймаут
        start_time = get_registration_start_time(chat_id)
        if time.time() - start_time > 30 * 60:  # 30 минут
            clear_user_data(chat_id)
            bot.send_message(chat_id, "⏰ Время регистрации истекло. Начните заново.", reply_markup=get_appropriate_menu(chat_id))
            return
        
        # Валидация имени
        is_valid, error_msg = validate_user_input(message.text, "name")
        if not is_valid:
            msg = bot.send_message(chat_id, f"❌ {error_msg}\nПопробуйте еще раз:", reply_markup=get_cancel_button())
            bot.register_next_step_handler(msg, process_student_name)
            return
            
        # ИСПРАВЛЕНО: Используем StateManager
        from state.users import update_user_data
        update_user_data(chat_id, student_name=message.text.strip())
        update_registration_stage(chat_id, "age")
        msg = bot.send_message(chat_id, "Введите возраст ученика:", reply_markup=get_cancel_button())
        bot.register_next_step_handler(msg, process_age)

    @ensure_text_message
    @ensure_stage(lambda m: get_registration_stage(m.chat.id), "age", error_message="Сначала введите возраст ученика.")
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
            
        # Проверяем таймаут
        start_time = get_registration_start_time(chat_id)
        if time.time() - start_time > 30 * 60:  # 30 минут
            clear_user_data(chat_id)
            bot.send_message(chat_id, "⏰ Время регистрации истекло. Начните заново.", reply_markup=get_appropriate_menu(chat_id))
            return
        
        # Валидация возраста
        is_valid, error_msg = validate_user_input(message.text, "age")
        if not is_valid:
            msg = bot.send_message(chat_id, f"❌ {error_msg}\nПопробуйте еще раз:", reply_markup=get_cancel_button())
            bot.register_next_step_handler(msg, process_age)
            return
            
        # ИСПРАВЛЕНО: Используем StateManager
        from state.users import update_user_data
        update_user_data(chat_id, age=message.text.strip())
        update_registration_stage(chat_id, "course")

        courses = get_active_courses()
        if not courses:
            bot.send_message(chat_id, "⚠️ Курсы временно недоступны.")
            return

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for course in courses:
            markup.add(course[1])
        markup.add("🔙 Отмена")
        msg = bot.send_message(chat_id, "Выберите курс:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_course)

    @ensure_text_message
    @ensure_stage(lambda m: get_registration_stage(m.chat.id), "course", error_message="Сначала выберите курс.")
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
        selected = message.text.strip()
        courses = get_active_courses()
        course_names = [c[1] for c in courses]
        if selected not in course_names:
            msg = bot.send_message(chat_id, "Пожалуйста, выберите курс из списка.", reply_markup=get_appropriate_menu(chat_id))
            bot.register_next_step_handler(msg, process_course)
            return
        from state.users import update_user_data
        update_user_data(chat_id, course=selected)
        user = message.from_user
        # Новый этап: сначала пробуем username, если нет — просим телефон
        if user.username:
            update_user_data(chat_id, contact=f"@{user.username}")
            update_registration_stage(chat_id, "confirmation")
            send_confirmation(bot, chat_id)
        else:
            update_registration_stage(chat_id, "contact")
            ask_for_phone(bot, chat_id)

    def ask_for_phone(bot, chat_id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        button = types.KeyboardButton("📱 Отправить номер телефона", request_contact=True)
        markup.add(button)
        markup.add("🔙 Отмена")
        msg = bot.send_message(chat_id, "У вас не установлен username в Telegram. Пожалуйста, отправьте номер телефона, привязанный к Telegram, используя кнопку ниже или введите его вручную:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_contact)

    @bot.message_handler(content_types=["contact", "text"])
    def process_contact(message):
        chat_id = message.chat.id
        # Проверка этапа
        from state.users import get_registration_stage, update_user_data, update_registration_stage, clear_user_data
        if get_registration_stage(chat_id) != "contact":
            return  # Не на этом этапе
        # Проверяем отмену
        if message.text == "🔙 Отмена":
            handle_cancel_action(bot, message, "регистрация", logger)
            return
        phone = None
        if message.contact and message.contact.phone_number:
            phone = message.contact.phone_number
        elif message.text:
            phone = message.text.strip()
        # Валидация номера
        import re
        phone_clean = re.sub(r"[^\d+]", "", phone or "")
        if phone_clean.startswith("8"):
            phone_clean = "+7" + phone_clean[1:]
        elif phone_clean.startswith("7") and not phone_clean.startswith("+7"):
            phone_clean = "+7" + phone_clean[1:]
        elif not phone_clean.startswith("+7"):
            phone_clean = "+7" + phone_clean[-10:] if len(phone_clean) >= 10 else phone_clean
        # Проверка формата
        if not re.fullmatch(r"\+7\d{10}", phone_clean):
            msg = bot.send_message(chat_id, "❌ Некорректный номер. Введите номер в формате +7XXXXXXXXXX или используйте кнопку для отправки номера.", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(types.KeyboardButton("📱 Отправить номер телефона", request_contact=True), "🔙 Отмена"))
            bot.register_next_step_handler(msg, process_contact)
            return
        # Сохраняем контакт
        update_user_data(chat_id, contact=phone_clean)
        update_registration_stage(chat_id, "confirmation")
        # Убираем клавиатуру
        bot.send_message(chat_id, "Спасибо! Ваш номер сохранён.", reply_markup=types.ReplyKeyboardRemove())
        send_confirmation(bot, chat_id)

    def send_confirmation(bot, chat_id):
        # ИСПРАВЛЕНО: Используем StateManager
        from state.users import get_user_data
        data = get_user_data(chat_id)
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

        # ИСПРАВЛЕНО: Проверяем правильный этап и таймаут
        if get_registration_stage(chat_id) != "confirmation":
            bot.send_message(chat_id, "⚠️ Подтверждение недоступно. Начните заново.", reply_markup=get_appropriate_menu(chat_id))
            return
        
        # Проверяем таймаут
        start_time = get_registration_start_time(chat_id)
        if time.time() - start_time > 30 * 60:  # 30 минут
            clear_user_data(chat_id)
            bot.send_message(chat_id, "⏰ Время регистрации истекло. Начните заново.", reply_markup=get_appropriate_menu(chat_id))
            return

        # ИСПРАВЛЕНО: Используем StateManager и добавляем обработку ошибок
        from state.users import get_user_data
        data = get_user_data(chat_id)
        
        try:
            add_application(
                tg_id=str(chat_id),
                parent_name=data["parent_name"],
                student_name=data["student_name"],
                age=data["age"],
                contact=data["contact"],
                course=data["course"]
            )
            bot.send_message(chat_id, "✅ Ваша заявка отправлена!", reply_markup=get_appropriate_menu(chat_id))
            clear_user_data(chat_id)
            logger.info(f"User {chat_id} submitted application")
            
        except ValueError as e:
            # Обработка ошибки дублирования заявки
            bot.send_message(chat_id, f"⚠️ {str(e)}", reply_markup=get_appropriate_menu(chat_id))
            clear_user_data(chat_id)
            logger.warning(f"User {chat_id} tried to create duplicate application: {e}")
            
        except Exception as e:
            # Обработка других ошибок
            bot.send_message(chat_id, "❌ Произошла ошибка при сохранении заявки. Попробуйте позже.", reply_markup=get_appropriate_menu(chat_id))
            clear_user_data(chat_id)
            log_error(logger, e, f"Error saving application for user {chat_id}")

    @bot.callback_query_handler(func=lambda call: call.data in ["continue_registration", "restart_registration"])
    def handle_registration_actions(call):
        """Обрабатывает действия с незавершенной регистрацией"""
        chat_id = call.message.chat.id
        
        # Проверка безопасности
        security_ok, error_msg = check_user_security(call.from_user.id, "registration_action")
        if not security_ok:
            bot.answer_callback_query(call.id, f"🚫 {error_msg}")
            return
        
        if call.data == "restart_registration":
            # Начинаем регистрацию заново
            clear_user_data(chat_id)
            start_registration(chat_id)
            msg = bot.send_message(chat_id, "🔄 Регистрация начата заново.\n\nВведите ваше имя (имя родителя):", reply_markup=get_cancel_button())
            bot.register_next_step_handler(msg, process_parent_name)
            logger.info(f"User {chat_id} restarted registration")
            
        elif call.data == "continue_registration":
            # Продолжаем с текущего этапа
            current_stage = get_registration_stage(chat_id)
            
            # Проверяем таймаут
            start_time = get_registration_start_time(chat_id)
            if time.time() - start_time > 30 * 60:  # 30 минут
                clear_user_data(chat_id)
                bot.edit_message_text(
                    "⏰ Время регистрации истекло. Начните заново.",
                    chat_id, call.message.message_id
                )
                bot.send_message(chat_id, "⏰ Время регистрации истекло. Начните заново.", reply_markup=get_appropriate_menu(chat_id))
                return
            
            # Определяем следующий шаг на основе текущего этапа
            if current_stage == "parent_name":
                bot.edit_message_text(
                    "🔄 Продолжаем регистрацию.\n\nВведите ваше имя (имя родителя):",
                    chat_id, call.message.message_id
                )
                msg = bot.send_message(chat_id, "Введите ваше имя (имя родителя):", reply_markup=get_cancel_button())
                bot.register_next_step_handler(msg, process_parent_name)
                
            elif current_stage == "student_name":
                bot.edit_message_text(
                    "🔄 Продолжаем регистрацию.\n\nВведите имя ученика:",
                    chat_id, call.message.message_id
                )
                msg = bot.send_message(chat_id, "Введите имя ученика:", reply_markup=get_cancel_button())
                bot.register_next_step_handler(msg, process_student_name)
                
            elif current_stage == "age":
                bot.edit_message_text(
                    "🔄 Продолжаем регистрацию.\n\nВведите возраст ученика:",
                    chat_id, call.message.message_id
                )
                msg = bot.send_message(chat_id, "Введите возраст ученика:", reply_markup=get_cancel_button())
                bot.register_next_step_handler(msg, process_age)
                
            elif current_stage == "course":
                courses = get_active_courses()
                if not courses:
                    bot.edit_message_text(
                        "⚠️ Курсы временно недоступны.",
                        chat_id, call.message.message_id
                    )
                    return
                
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                for course in courses:
                    markup.add(course[1])
                markup.add("🔙 Отмена")
                
                bot.edit_message_text(
                    "🔄 Продолжаем регистрацию.\n\nВыберите курс:",
                    chat_id, call.message.message_id
                )
                msg = bot.send_message(chat_id, "Выберите курс:", reply_markup=markup)
                bot.register_next_step_handler(msg, process_course)
                
            elif current_stage == "confirmation":
                bot.edit_message_text(
                    "🔄 Продолжаем регистрацию.\n\nПодтвердите данные:",
                    chat_id, call.message.message_id
                )
                send_confirmation(bot, chat_id)
            
            logger.info(f"User {chat_id} continued registration from stage: {current_stage}")


def register_handlers(bot):
    """Регистрация обработчиков регистрации"""
    logger = setup_logger('registration')
    register(bot, logger)


def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)
