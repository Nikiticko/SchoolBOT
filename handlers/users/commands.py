# === handlers/commands.py ===
from telebot import types
import utils.menu as menu
from data.db import (
    get_application_by_tg_id, format_date_for_display, get_active_courses, get_cancelled_count_by_tg_id, get_finished_count_by_tg_id, get_all_archive, archive_application, get_last_contact_time, add_contact, update_application, delete_application_by_tg_id, get_reviews_for_publication_with_deleted, can_send_admin_notification, mark_admin_notification_sent
)
from utils.logger import log_user_action, log_error, setup_logger
from state.users import get_user_data, set_user_data, update_user_data, clear_user_data
from config import ADMIN_ID
from utils.security import check_user_security, validate_user_input, security_manager
from utils.decorators import error_handler, ensure_text_message, ensure_stage
from utils.menu import get_appropriate_menu, is_admin

def register_handlers(bot):
    """Регистрация обработчиков команд"""
    logger = setup_logger('commands')
    register(bot, logger)

def register(bot, logger):  

    @bot.message_handler(commands=["help"])
    @error_handler()
    def handle_help(message):
        import time
        start_time = time.time()
        
        # Проверка безопасности
        security_ok, error_msg = check_user_security(message.from_user.id, "help")
        if not security_ok:
            bot.send_message(message.chat.id, f"🚫 {error_msg}")
            return
        
        help_text = (
            "🤖 <b>Что умеет этот бот?</b>\n\n"
            "Этот бот создан лично преподавателем, чтобы упростить запись на пробные занятия по программированию.\n"
            "Вы можете зарегистрироваться, узнать дату занятия, изменить или отменить заявку — всё прямо здесь.\n\n"
            
            "📝 <b>Записаться на занятие</b>\n"
            "• Нажмите кнопку '📝 Записаться на занятие'\n"
            "• Ответьте на несколько простых вопросов\n"
            "• Дождитесь, пока вам напишет преподаватель, чтобы договориться о назначении пробного урока\n\n"

            "📅 <b>Моё занятие</b>\n"
            "• Здесь вы найдёте информацию о своём ближайшем уроке\n"
            "• Если урок уже назначен — появится кнопка отмены\n"
            "• Также через эту кнопку можно изменить или отменить заявку до назначения занятия\n\n"

            "🆘 <b>Обратиться к преподавателю</b>\n"
            "• Напишите любой вопрос или предложение через кнопку '🆘 Обратиться к админу'\n"
            "• Я обязательно отвечу, как только смогу 🙌\n\n"

            "ℹ️ <b>Дополнительные разделы:</b>\n"
            "• 'ℹ️ О преподавателе' — кто я, мой подход и опыт\n"
            "• '💰 Цены и форматы' — вся информация по стоимости\n"
            "• '📚 Доступные курсы' — список направлений, с которыми можно стартовать\n\n"

            "⚠️ <b>Важно:</b>\n"
            "Это первая версия бота, и он всё ещё развивается. Если вы заметили ошибку или у вас есть идея, как сделать лучше —\n"
            "<b>пожалуйста</b>, напишите через кнопку '🆘 Обратиться к админу'. Это очень поможет 🙏\n\n"

            "📌 Если не знаете, с чего начать — просто нажмите '📝 Записаться на занятие'!"
        )
        
        bot.send_message(message.chat.id, help_text, parse_mode="HTML")
        
        # Логирование активности пользователя
        log_user_action(logger, message.from_user.id, "HELP_COMMAND", f"Username: {message.from_user.username}")
        
        # Логирование производительности
        response_time = time.time() - start_time
        logger.info(f"⏱️ Handler response time: {response_time:.3f}s (help command)")

    @bot.message_handler(func=lambda m: m.text == "📅 Мое занятие")
    @error_handler()
    def handle_my_lesson(message):
        import time
        start_time = time.time()
        
        # Проверка безопасности
        security_ok, error_msg = check_user_security(message.from_user.id, "my_lesson")
        if not security_ok:
            bot.send_message(message.chat.id, f"🚫 {error_msg}")
            return
        
        chat_id = message.chat.id
        user = message.from_user
        
        # Проверяем, есть ли заявка у пользователя
        application = get_application_by_tg_id(str(chat_id))
        
        if not application:
            bot.send_message(chat_id, "📝 У вас нет активной заявки. Запишитесь на занятие!", reply_markup=menu.get_appropriate_menu(user.id))
            log_user_action(logger, user.id, "MY_LESSON_NO_APPLICATION", "No active application found")
            return
        
        app_id, tg_id, parent_name, student_name, age, contact, course, lesson_date, lesson_link, status, created_at, reminder_sent = application
        
        # Проверяем статус заявки
        if status == "Ожидает":
            formatted_created = format_date_for_display(created_at)
            application_text = (
                f"📋 <b>Ваша заявка:</b>\n\n"
                f"🆔 <b>Номер:</b> #{app_id}\n"
                f"👤 <b>Родитель:</b> {parent_name}\n"
                f"🧒 <b>Ученик:</b> {student_name}\n"
                f"🎂 <b>Возраст:</b> {age}\n"
                f"📘 <b>Курс:</b> {course}\n"
                f"📞 <b>Контакт:</b> {contact or 'не указан'}\n"
                f"📅 <b>Создано:</b> {formatted_created}\n"
                f"📝 <b>Статус:</b> {status}\n\n"
                f"⏳ <i>Заявка обрабатывается. Ожидайте назначения даты занятия.</i>"
            )
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("✏️ Редактировать", callback_data="edit_application"),
                types.InlineKeyboardButton("❌ Отменить", callback_data="cancel_application")
            )
            from data.db import can_send_admin_notification
            if can_send_admin_notification(app_id):
                markup.add(types.InlineKeyboardButton("🔔 Напомнить админу", callback_data="notify_admin"))
            else:
                markup.add(types.InlineKeyboardButton("⏰ Уведомление отправлено", callback_data="notification_sent"))
            
            bot.send_message(chat_id, application_text, parse_mode="HTML", reply_markup=markup)
            log_user_action(logger, user.id, "MY_LESSON_PENDING_DETAILED", f"Course: {course}, Status: {status}")
            return
        elif status == "Назначено":
            formatted_date = format_date_for_display(lesson_date)
            application_text = (
                f"📋 <b>Ваша заявка:</b>\n\n"
                f"🆔 <b>Номер:</b> #{app_id}\n"
                f"👤 <b>Родитель:</b> {parent_name}\n"
                f"🧒 <b>Ученик:</b> {student_name}\n"
                f"🎂 <b>Возраст:</b> {age}\n"
                f"📘 <b>Курс:</b> {course}\n"
                f"📞 <b>Контакт:</b> {contact or 'не указан'}\n"
                f"📅 <b>Дата урока:</b> {formatted_date}\n"
                f"🔗 <b>Ссылка:</b> {lesson_link or 'не указана'}\n"
                f"📝 <b>Статус:</b> {status}\n\n"
                f"✅ Урок назначен. Ожидайте напоминания."
            )
            bot.send_message(chat_id, application_text, parse_mode="HTML", reply_markup=menu.get_appropriate_menu(user.id))
            return
        else:
            bot.send_message(chat_id, f"❌ Заявка в статусе '{status}' не может быть отредактирована.", reply_markup=menu.get_appropriate_menu(user.id))
            return
        
        # Форматируем дату для отображения
        formatted_date = format_date_for_display(lesson_date)
        
        # Формируем сообщение
        lesson_text = (
            f"📅 <b>Ваше занятие:</b>\n\n"
            f"👤 <b>Ученик:</b> {student_name}\n"
            f"📘 <b>Курс:</b> {course}\n"
            f"📅 <b>Дата:</b> {formatted_date}\n"
            f"🔗 <b>Ссылка:</b> {lesson_link}\n\n"
            f"📝 <b>Статус:</b> {status}"
        )
        
        bot.send_message(chat_id, lesson_text, parse_mode="HTML", reply_markup=menu.get_appropriate_menu(user.id))
        
        # Логирование активности пользователя
        log_user_action(logger, user.id, "MY_LESSON_VIEWED", f"Course: {course}, Date: {formatted_date}")
        
        # Логирование производительности
        response_time = time.time() - start_time
        logger.info(f"⏱️ Handler response time: {response_time:.3f}s (my_lesson command)")
        
        # Бизнес-метрики
        logger.info(f"📊 Lesson viewed: user {user.id} viewed lesson for course {course}")

    @bot.callback_query_handler(func=lambda c: c.data == "edit_application")
    def handle_edit_application(call):
        chat_id = call.message.chat.id
        
        # Проверка безопасности
        security_ok, error_msg = check_user_security(call.from_user.id, "edit_application")
        if not security_ok:
            bot.answer_callback_query(call.id, f"🚫 {error_msg}")
            return
        
        # Проверяем, что заявка существует
        app = get_application_by_tg_id(str(chat_id))
        if not app:
            bot.send_message(chat_id, "❌ Заявка не найдена.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            return
        
        # Проверяем только по статусу
        if app[9] != "Ожидает":
            bot.send_message(chat_id, "❌ Редактировать можно только заявку в статусе 'Ожидает'.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            return
        
        # Проверка на частоту редактирования (раз в 24 часа)
        import time
        user_data = get_user_data(chat_id)
        last_edit = user_data.get("last_edit_time") if user_data else None
        now = time.time()
        if last_edit and now - last_edit < 86400:
            hours = int((86400 - (now - last_edit)) // 3600)
            minutes = int(((86400 - (now - last_edit)) % 3600) // 60)
            bot.send_message(chat_id, f"❌ Редактировать заявку можно не чаще одного раза в 24 часа. До следующей попытки: {hours} ч {minutes} мин.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            return
        
        parent_name = app[2]
        student_name = app[3]
        age = app[4]
        contact = app[5]
        course = app[6]
        user = call.from_user
        fields = [
            ("Имя родителя", "parent_name"),
            ("Имя ученика", "student_name"),
            ("Возраст", "age"),
            ("Курс", "course")
        ]
        # Контакт можно редактировать только если это не username
        if not user.username:
            fields.append(("Контакт", "contact"))
        markup = types.InlineKeyboardMarkup()
        for label, key in fields:
            markup.add(types.InlineKeyboardButton(label, callback_data=f"edit_field:{key}"))
        bot.send_message(chat_id, "Что вы хотите изменить?", reply_markup=markup)
        set_user_data(chat_id, {"edit_app": True, "app_id": app[0], "parent_name": parent_name, "student_name": student_name, "age": age, "contact": contact, "course": course})
        log_user_action(logger, call.from_user.id, "edit_application_started")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("edit_field:"))
    def handle_edit_field(call):
        security_ok, error_msg = check_user_security(call.from_user.id, "edit_field")
        if not security_ok:
            bot.answer_callback_query(call.id, f"🚫 {error_msg}")
            return
        chat_id = call.message.chat.id
        field = call.data.split(":")[1]
        user_data = get_user_data(chat_id)
        if not user_data or not user_data.get("edit_app"):
            app = get_application_by_tg_id(str(chat_id))
            if app and app[9] == "Ожидает":
                set_user_data(chat_id, {"edit_app": True, "app_id": app[0], "parent_name": app[2], "student_name": app[3], "age": app[4], "contact": app[5], "course": app[6]})
                user_data = get_user_data(chat_id)
        if not user_data or not user_data.get("edit_app"):
            bot.send_message(chat_id, "❌ Данные для редактирования не найдены.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            return
        field_names = {
            "parent_name": "имя родителя",
            "student_name": "имя ученика", 
            "age": "возраст",
            "contact": "контакт",
            "course": "курс"
        }
        if field == "course":
            # Показываем список курсов для выбора
            courses = get_active_courses()
            if not courses:
                bot.send_message(chat_id, "⚠️ Курсы временно недоступны.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
                return
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            for c in courses:
                markup.add(c[1])
            markup.add("🔙 Отмена")
            bot.send_message(chat_id, "Выберите новый курс:", reply_markup=markup)
            bot.register_next_step_handler(call.message, process_edit_course_field)
            log_user_action(logger, call.from_user.id, f"edit_field_{field}_choose")
            return
        msg = bot.send_message(chat_id, f"Введите новое {field_names.get(field, field)}:")
        bot.register_next_step_handler(msg, process_edit_field, field)
        log_user_action(logger, call.from_user.id, f"edit_field_{field}")

    def process_edit_field(message, field):
        security_ok, error_msg = check_user_security(message.from_user.id, "process_edit_field")
        if not security_ok:
            bot.send_message(message.chat.id, f"🚫 {error_msg}")
            return
        chat_id = message.chat.id
        user_data = get_user_data(chat_id)
        # Если user_data нет или нет edit_app, пробуем восстановить из БД
        if not user_data or not user_data.get("edit_app"):
            app = get_application_by_tg_id(str(chat_id))
            if app and app[9] == "Ожидает":
                set_user_data(chat_id, {"edit_app": True, "app_id": app[0], "parent_name": app[2], "student_name": app[3], "age": app[4], "contact": app[5], "course": app[6]})
                user_data = get_user_data(chat_id)
        if not user_data or not user_data.get("edit_app"):
            bot.send_message(chat_id, "❌ Данные для редактирования не найдены.", reply_markup=menu.get_appropriate_menu(message.from_user.id))
            return
        try:
            import logging
            logging.warning(f"DEBUG: field type={type(field)}, value={field}, new_value(raw)='{message.text}' (chat_id={chat_id})")
        except Exception:
            pass
        new_value = message.text.strip()
        try:
            import logging
            logging.warning(f"DEBUG: new_value after strip='{new_value}' (chat_id={chat_id})")
        except Exception:
            pass
        if not new_value:
            bot.send_message(chat_id, "❌ Значение не может быть пустым. Попробуйте снова.", reply_markup=menu.get_appropriate_menu(message.from_user.id))
            return
        # Валидация возраста
        if field == "age":
            age_str = new_value
            if not age_str.isdigit() or not (5 <= int(age_str) <= 99):
                from utils.menu import get_cancel_button
                msg = bot.send_message(
                    chat_id,
                    "❌ Ошибка! Введите возраст цифрами, от 5 до 99 лет, без пробелов и лишних символов.\n\nПопробуйте еще раз:",
                    reply_markup=get_cancel_button()
                )
                try:
                    import logging
                    logging.warning(f"AGE VALIDATION FAIL: chat_id={chat_id}, value='{new_value}'")
                except Exception:
                    pass
                bot.register_next_step_handler(msg, process_edit_field, field)
                return
            new_value = str(int(age_str))  # Сохраняем возраст как число-строку без лидирующих нулей и пробелов
        # Валидация имени родителя и ученика
        if field in ("parent_name", "student_name"):
            import re
            name = new_value.strip()
            if not (2 <= len(name) <= 32) or not re.fullmatch(r"[А-Яа-яA-Za-zЁё\-\s]+", name):
                from utils.menu import get_cancel_button
                msg = bot.send_message(
                    chat_id,
                    "❌ Ошибка! Имя должно содержать только буквы, пробелы и дефисы, длина 2-32 символа.\n\nПопробуйте еще раз:",
                    reply_markup=get_cancel_button()
                )
                try:
                    import logging
                    logging.warning(f"NAME VALIDATION FAIL: chat_id={chat_id}, field={field}, value='{new_value}'")
                except Exception:
                    pass
                bot.register_next_step_handler(msg, process_edit_field, field)
                return
            new_value = name
        # Валидация контакта (телефон или username)
        if field == "contact":
            import re
            contact = new_value.strip()
            # Приведение к формату +7XXXXXXXXXX
            phone_clean = re.sub(r"[^\d+]", "", contact)
            if phone_clean.startswith("8") and len(phone_clean) == 11:
                phone_clean = "+7" + phone_clean[1:]
            elif phone_clean.startswith("7") and len(phone_clean) == 11:
                phone_clean = "+7" + phone_clean[1:]
            elif phone_clean.startswith("+7") and len(phone_clean) == 12:
                pass
            elif len(phone_clean) == 10:
                phone_clean = "+7" + phone_clean
            is_phone = re.fullmatch(r"\+7\d{10}", phone_clean)
            is_username = re.fullmatch(r"@\w{5,32}", contact)
            if not (is_phone or is_username):
                from utils.menu import get_cancel_button
                msg = bot.send_message(
                    chat_id,
                    "❌ Ошибка! Введите телефон в формате +7XXXXXXXXXX, 8XXXXXXXXXX, 7XXXXXXXXXX или username через @ (5-32 символа).\n\nПопробуйте еще раз:",
                    reply_markup=get_cancel_button()
                )
                try:
                    import logging
                    logging.warning(f"CONTACT VALIDATION FAIL: chat_id={chat_id}, value='{new_value}'")
                except Exception:
                    pass
                bot.register_next_step_handler(msg, process_edit_field, field)
                return
            new_value = phone_clean if is_phone else contact
        try:
            import logging
            logging.warning(f"DEBUG: update_user_data called with {field}={new_value} (chat_id={chat_id})")
        except Exception:
            pass
        update_user_data(chat_id, **{str(field): new_value})
        try:
            import logging
            logging.warning(f"DEBUG: user_data after update: {get_user_data(chat_id)} (chat_id={chat_id})")
        except Exception:
            pass
        # Получаем актуальные данные до очистки
        updated_data = get_user_data(chat_id).copy()
        clear_user_data(chat_id)
        msg = (
            f"✅ Обновленные данные:\n"
            f"👤 Родитель: {updated_data.get('parent_name', '-') }\n"
            f"🧒 Ученик: {updated_data.get('student_name', '-') }\n"
            f"🎂 Возраст: {updated_data.get('age', '-') }\n"
            f"📘 Курс: {updated_data.get('course', '-') }\n"
            f"📞 Контакт: {updated_data.get('contact', 'не указан')}"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Сохранить", callback_data="save_edit"),
            types.InlineKeyboardButton("❌ Отменить", callback_data="cancel_edit")
        )
        bot.send_message(chat_id, msg, reply_markup=markup)
        # Возвращаем главное меню, чтобы клавиатура не "зависала"
        bot.send_message(chat_id, "Выберите действие из меню:", reply_markup=menu.get_appropriate_menu(message.from_user.id))

    def process_edit_course_field(message):
        chat_id = message.chat.id
        security_ok, error_msg = check_user_security(message.from_user.id, "process_edit_field")
        if not security_ok:
            bot.send_message(chat_id, f"🚫 {error_msg}")
            return
        user_data = get_user_data(chat_id)
        if not user_data or not user_data.get("edit_app"):
            app = get_application_by_tg_id(str(chat_id))
            if app and app[9] == "Ожидает":
                set_user_data(chat_id, {"edit_app": True, "app_id": app[0], "parent_name": app[2], "student_name": app[3], "age": app[4], "contact": app[5], "course": app[6]})
                user_data = get_user_data(chat_id)
        if not user_data or not user_data.get("edit_app"):
            bot.send_message(chat_id, "❌ Данные для редактирования не найдены.", reply_markup=menu.get_appropriate_menu(message.from_user.id))
            return
        if message.text == "🔙 Отмена":
            bot.send_message(chat_id, "Редактирование отменено.", reply_markup=menu.get_appropriate_menu(message.from_user.id))
            clear_user_data(chat_id)
            return
        selected = message.text.strip()
        courses = get_active_courses()
        course_names = [c[1] for c in courses]
        if selected not in course_names:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            for c in courses:
                markup.add(c[1])
            markup.add("🔙 Отмена")
            bot.send_message(chat_id, "Пожалуйста, выберите курс из списка:", reply_markup=markup)
            bot.register_next_step_handler(message, process_edit_course_field)
            return
        update_user_data(chat_id, course=selected)
        updated_data = get_user_data(chat_id).copy()
        clear_user_data(chat_id)
        msg = (
            f"✅ Обновленные данные:\n"
            f"👤 Родитель: {updated_data.get('parent_name', '-') }\n"
            f"🧒 Ученик: {updated_data.get('student_name', '-') }\n"
            f"🎂 Возраст: {updated_data.get('age', '-') }\n"
            f"📘 Курс: {updated_data.get('course', '-') }\n"
            f"📞 Контакт: {updated_data.get('contact', 'не указан')}"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Сохранить", callback_data="save_edit"),
            types.InlineKeyboardButton("❌ Отменить", callback_data="cancel_edit")
        )
        bot.send_message(chat_id, msg, reply_markup=markup)
        # Возвращаем главное меню, чтобы клавиатура не "зависала"
        bot.send_message(chat_id, "Выберите действие из меню:", reply_markup=menu.get_appropriate_menu(message.from_user.id))

    @bot.callback_query_handler(func=lambda c: c.data == "save_edit")
    def handle_save_edit(call):
        security_ok, error_msg = check_user_security(call.from_user.id, "save_edit")
        if not security_ok:
            bot.answer_callback_query(call.id, f"🚫 {error_msg}")
            return
        chat_id = call.message.chat.id
        user_data = get_user_data(chat_id)
        # Если user_data нет или нет edit_app, пробуем восстановить из БД
        if not user_data or not user_data.get("edit_app"):
            app = get_application_by_tg_id(str(chat_id))
            if app and app[9] == "Ожидает":
                set_user_data(chat_id, {"edit_app": True, "app_id": app[0], "parent_name": app[2], "student_name": app[3], "age": app[4], "contact": app[5], "course": app[6]})
                user_data = get_user_data(chat_id)
        if not user_data or not user_data.get("edit_app"):
            bot.send_message(chat_id, "❌ Данные для редактирования не найдены.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            return
        try:
            app_data = get_user_data(chat_id)
            update_application(
                app_data["app_id"],
                app_data["parent_name"],
                app_data["student_name"], 
                app_data["age"],
                app_data.get("contact", ""),
                app_data["course"]
            )
            # Сохраняем время последнего редактирования
            import time
            update_user_data(chat_id, last_edit_time=time.time())
            # Уведомление админу
            from config import ADMIN_ID
            user = call.from_user
            msg_admin = (
                f"✏️ <b>Пользователь отредактировал заявку</b>\n\n"
                f"👤 Родитель: {app_data.get('parent_name', '-') }\n"
                f"🧒 Ученик: {app_data.get('student_name', '-') }\n"
                f"🎂 Возраст: {app_data.get('age', '-') }\n"
                f"📘 Курс: {app_data.get('course', '-') }\n"
                f"📞 Контакт: {app_data.get('contact', 'не указан')}\n"
                f"🆔 User ID: {user.id}\n"
                f"👤 Username: @{user.username if user.username else '-'}"
            )
            bot.send_message(ADMIN_ID, msg_admin, parse_mode="HTML")
            clear_user_data(chat_id)
            bot.send_message(chat_id, "✅ Заявка успешно обновлена!", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            log_user_action(logger, call.from_user.id, "application_updated")
        except Exception as e:
            bot.send_message(chat_id, "❌ Ошибка при обновлении заявки. Попробуйте позже.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            log_error(logger, e, f"Error updating application for user {call.from_user.id}")

    @bot.callback_query_handler(func=lambda c: c.data == "cancel_edit")
    def handle_cancel_edit(call):
        # Проверка безопасности
        security_ok, error_msg = check_user_security(call.from_user.id, "cancel_edit")
        if not security_ok:
            bot.answer_callback_query(call.id, f"🚫 {error_msg}")
            return
        
        chat_id = call.message.chat.id
        
        # Очищаем данные
        clear_user_data(chat_id)
        
        bot.send_message(chat_id, "Редактирование отменено.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
        log_user_action(logger, call.from_user.id, "edit_cancelled")

    @bot.callback_query_handler(func=lambda c: c.data == "cancel_application")
    def handle_cancel_application(call):
        chat_id = call.message.chat.id
        app = get_application_by_tg_id(str(chat_id))
        if not app:
            bot.send_message(chat_id, "❌ Заявка не найдена.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            return
        # Проверяем только по статусу
        if app[9] != "Ожидает":
            bot.send_message(chat_id, "❌ Отменить можно только заявку в статусе 'Ожидает'.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            return
        msg = bot.send_message(chat_id, "Пожалуйста, укажите причину отмены заявки:", reply_markup=menu.get_cancel_button())
        set_user_data(chat_id, {"cancel_app_stage": True})
        bot.register_next_step_handler(msg, process_cancel_reason)

    def process_cancel_reason(message):
        chat_id = message.chat.id
        # Проверяем, что это сообщение, а не callback
        if hasattr(message, 'text') and message.text == "🔙 Отмена":
            bot.send_message(chat_id, "Отмена отмены заявки.", reply_markup=menu.get_appropriate_menu(message.from_user.id))
            clear_user_data(chat_id)
            return
        reason = getattr(message, 'text', '').strip()
        # Подтверждение отмены
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_cancel_application"))
        markup.add(types.InlineKeyboardButton("❌ Отменить", callback_data="cancel_cancel_application"))
        set_user_data(chat_id, {"cancel_reason": reason})
        bot.send_message(chat_id, f"Вы уверены, что хотите отменить заявку?\nПричина: {reason}", reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data == "confirm_cancel_application")
    def handle_confirm_cancel_application(call):
        chat_id = call.message.chat.id
        security_ok, error_msg = check_user_security(call.from_user.id, "confirm_cancel_application")
        if not security_ok:
            bot.answer_callback_query(call.id, f"🚫 {error_msg}")
            return
        app = get_application_by_tg_id(str(chat_id))
        if not app:
            bot.send_message(chat_id, "❌ Заявка не найдена или уже обработана.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            clear_user_data(chat_id)
            return
        # Проверяем только по статусу
        if app[9] != "Ожидает":
            bot.send_message(chat_id, "❌ Отменить можно только заявку в статусе 'Ожидает'.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            clear_user_data(chat_id)
            return
        reason = get_user_data(chat_id).get("cancel_reason", "")
        try:
            archive_application(app[0], cancelled_by="user", comment=reason, archived_status="Заявка отменена")
            delete_application_by_tg_id(chat_id)
            bot.send_message(chat_id, "✅ Ваша заявка отменена.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            parent_name = app[2] if app else '-'
            student_name = app[3] if app else '-'
            course = app[6] if app else '-'
            msg = (
                f"❌ Пользователь отменил заявку\n"
                f"👤 Родитель: {parent_name}\n"
                f"🧒 Ученик: {student_name}\n"
                f"📘 Курс: {course}\n"
                f"Причина: {reason}"
            )
            bot.send_message(ADMIN_ID, msg)
            clear_user_data(chat_id)
            log_user_action(logger, call.from_user.id, "cancelled_application")
        except Exception as e:
            bot.send_message(chat_id, "❌ Ошибка при отмене заявки. Попробуйте позже.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            clear_user_data(chat_id)
            log_error(logger, e, f"Error cancelling application for user {chat_id}")

    @bot.callback_query_handler(func=lambda c: c.data == "cancel_cancel_application")
    def handle_cancel_cancel_application(call):
        chat_id = call.message.chat.id
        clear_user_data(chat_id)  # Очищаем состояние
        bot.send_message(chat_id, "Отмена отмены заявки.", reply_markup=menu.get_appropriate_menu(call.from_user.id))

    @bot.callback_query_handler(func=lambda c: c.data == "notify_admin")
    def handle_notify_admin(call):
        """Обработчик кнопки 'Напомнить админу'"""
        chat_id = call.message.chat.id
        
        # Проверка безопасности
        security_ok, error_msg = check_user_security(call.from_user.id, "notify_admin")
        if not security_ok:
            bot.answer_callback_query(call.id, f"🚫 {error_msg}")
            return
        
        # Получаем данные заявки
        app = get_application_by_tg_id(str(chat_id))
        if not app:
            bot.answer_callback_query(call.id, "❌ Заявка не найдена")
            return
        
        app_id = app[0]
        
        # Проверяем, можно ли отправить уведомление
        if not can_send_admin_notification(app_id):
            bot.answer_callback_query(call.id, "⏰ Уведомление уже отправлено недавно")
            return
        
        try:
            # Отправляем уведомление админу
            admin_msg = (
                f"🔔 <b>Напоминание о заявке!</b>\n\n"
                f"🆔 <b>Заявка:</b> #{app_id}\n"
                f"👤 <b>Родитель:</b> {app[2]}\n"
                f"🧒 <b>Ученик:</b> {app[3]} ({app[4]} лет)\n"
                f"📘 <b>Курс:</b> {app[6]}\n"
                f"📞 <b>Контакт:</b> {app[5] or 'не указан'}\n"
                f"📅 <b>Создано:</b> {format_date_for_display(app[10])}\n\n"
                f"<i>Пользователь просит рассмотреть заявку</i>"
            )
            
            bot.send_message(ADMIN_ID, admin_msg, parse_mode="HTML")
            
            # Отмечаем, что уведомление отправлено
            mark_admin_notification_sent(app_id)
            
            # Обновляем кнопку
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("✏️ Редактировать", callback_data="edit_application"),
                types.InlineKeyboardButton("❌ Отменить", callback_data="cancel_application")
            )
            markup.add(types.InlineKeyboardButton("⏰ Уведомление отправлено", callback_data="notification_sent"))
            
            bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
            
            bot.answer_callback_query(call.id, "✅ Уведомление отправлено админу")
            log_user_action(logger, call.from_user.id, "admin_notification_sent", f"application: {app_id}")
            
        except Exception as e:
            bot.answer_callback_query(call.id, "❌ Ошибка при отправке уведомления")
            log_error(logger, e, f"Error sending admin notification for user {chat_id}")

    @bot.callback_query_handler(func=lambda c: c.data == "notification_sent")
    def handle_notification_sent(call):
        """Обработчик кнопки 'Уведомление отправлено' (информационная)"""
        bot.answer_callback_query(call.id, "⏰ Уведомление уже отправлено. Повторно можно отправить через 24 часа")
    
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
                bot.send_message(call.message.chat.id, msg, parse_mode="Markdown", reply_markup=menu.get_appropriate_menu(call.from_user.id))
                log_user_action(logger, call.from_user.id, "course_info_viewed", f"course: {name}")
            else:
                bot.send_message(call.message.chat.id, "⚠️ Курс не найден.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
                log_user_action(logger, call.from_user.id, "course_not_found", f"course_id: {course_id}")
        except Exception as e:
            log_error(logger, e, f"Course info for user {call.from_user.id}")

    @bot.callback_query_handler(func=lambda c: c.data == "cancel_lesson_user")
    def handle_cancel_lesson_user(call):
        chat_id = call.message.chat.id
        
        msg = bot.send_message(chat_id, "Пожалуйста, укажите причину отмены урока:", reply_markup=menu.get_cancel_button())
        set_user_data(chat_id, {"cancel_lesson_stage": True})
        bot.register_next_step_handler(msg, process_cancel_lesson_reason)

    def process_cancel_lesson_reason(message):
        chat_id = message.chat.id
        if hasattr(message, 'text') and message.text == "🔙 Отмена":
            bot.send_message(chat_id, "Отмена отмены урока.", reply_markup=menu.get_appropriate_menu(message.from_user.id))
            clear_user_data(chat_id)
            return
        reason = getattr(message, 'text', '').strip()
        # Подтверждение
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_cancel_lesson_user"))
        markup.add(types.InlineKeyboardButton("❌ Отменить", callback_data="cancel_cancel_lesson_user"))
        set_user_data(chat_id, {"cancel_lesson_reason": reason})
        bot.send_message(chat_id, f"Вы уверены, что хотите отменить урок?\nПричина: {reason}", reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data == "confirm_cancel_lesson_user")
    def handle_confirm_cancel_lesson_user(call):
        chat_id = call.message.chat.id
        security_ok, error_msg = check_user_security(call.from_user.id, "confirm_cancel_lesson_user")
        if not security_ok:
            bot.answer_callback_query(call.id, f"🚫 {error_msg}")
            return
        app = get_application_by_tg_id(str(chat_id))
        if not app:
            bot.send_message(chat_id, "❌ Заявка не найдена или уже обработана.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            clear_user_data(chat_id)
            return
        # Проверяем только по статусу
        if app[9] != "Назначено":
            bot.send_message(chat_id, "❌ Отменить урок можно только для заявки в статусе 'Назначено'.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            clear_user_data(chat_id)
            return
        reason = get_user_data(chat_id).get("cancel_lesson_reason", "")
        try:
            archive_application(app[0], cancelled_by="user", comment=reason, archived_status="Урок отменён")
            delete_application_by_tg_id(chat_id)
            bot.send_message(chat_id, "✅ Ваш урок отменён.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            parent_name = app[2] if app else '-'
            student_name = app[3] if app else '-'
            course = app[6] if app else '-'
            msg = (
                f"🚫 Пользователь отменил урок\n"
                f"👤 Родитель: {parent_name}\n"
                f"🧒 Ученик: {student_name}\n"
                f"📘 Курс: {course}\n"
                f"Причина: {reason}"
            )
            bot.send_message(ADMIN_ID, msg)
            clear_user_data(chat_id)
            log_user_action(logger, call.from_user.id, "cancelled_lesson")
        except Exception as e:
            bot.send_message(chat_id, "❌ Ошибка при отмене урока. Попробуйте позже.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            clear_user_data(chat_id)
            log_error(logger, e, f"Error cancelling lesson for user {chat_id}")

    @bot.callback_query_handler(func=lambda c: c.data == "cancel_cancel_lesson_user")
    def handle_cancel_cancel_lesson_user(call):
        chat_id = call.message.chat.id
        clear_user_data(chat_id)  # Очищаем состояние
        bot.send_message(chat_id, "Отмена отмены урока.", reply_markup=menu.get_appropriate_menu(call.from_user.id))

    @bot.message_handler(func=lambda m: m.text == "🆘 Обратиться к админу")
    def handle_contact_admin(message):
        from data.db import get_last_contact_time, add_contact
        import datetime
        chat_id = message.chat.id
        user = message.from_user
        
        # Проверка безопасности (единая система)
        security_ok, error_msg = check_user_security(message.from_user.id, "contact_admin")
        if not security_ok:
            bot.send_message(message.chat.id, f"🚫 {error_msg}")
            return
        last_time = get_last_contact_time(str(chat_id))
        if last_time:
            last_dt = datetime.datetime.fromisoformat(last_time)
            if (datetime.datetime.now() - last_dt).total_seconds() < 20*60:
                bot.send_message(chat_id, "⏳ Вы можете отправлять обращения не чаще, чем раз в 20 минут.", reply_markup=menu.get_appropriate_menu(message.from_user.id))
                return
        bot.send_message(chat_id, "✍️ Опишите ваш вопрос или прикрепите файл (фото, документ, голосовое, видео).\n\nДля отмены нажмите '🔙 Отмена'.", reply_markup=menu.get_cancel_button())
        set_user_data(chat_id, {"contact_fsm": True})
        bot.register_next_step_handler(message, process_contact_message)

    def process_contact_message(message):
        from data.db import add_contact
        chat_id = message.chat.id
        user = message.from_user
        if hasattr(message, 'text') and message.text == "🔙 Отмена":
            bot.send_message(chat_id, "Обращение отменено.", reply_markup=menu.get_appropriate_menu(message.from_user.id))
            clear_user_data(chat_id)
            return
        contact = f"@{user.username}" if user.username else (get_user_data(chat_id).get("phone") or str(chat_id))
        allowed_types = ["photo", "document", "audio", "voice", "video_note", "sticker"]
        forbidden_types = ["video", "animation"]
        # Проверка на media_group (альбом)
        if hasattr(message, 'media_group_id') and message.media_group_id:
            bot.send_message(chat_id, "🚫 Можно прикрепить только одно вложение. Пожалуйста, отправьте только один файл или фото.", reply_markup=menu.get_appropriate_menu(message.from_user.id))
            clear_user_data(chat_id)
            return
        # Проверка: сколько типов вложений присутствует
        present_types = 0
        file_id = None
        file_type = None
        if message.content_type == 'photo':
            file_id = message.photo[-1].file_id
            file_type = 'photo'
            present_types += 1
        if message.content_type == 'document':
            file_id = message.document.file_id
            file_type = 'document'
            present_types += 1
        if message.content_type == 'voice':
            file_id = message.voice.file_id
            file_type = 'voice'
            present_types += 1
        if message.content_type == 'audio':
            file_id = message.audio.file_id
            file_type = 'audio'
            present_types += 1
        if message.content_type == 'video_note':
            file_id = message.video_note.file_id
            file_type = 'video_note'
            present_types += 1
        if message.content_type == 'sticker':
            file_id = message.sticker.file_id
            file_type = 'sticker'
            present_types += 1
        if message.content_type in forbidden_types:
            bot.send_message(chat_id, "🚫 Видео и GIF (анимированные изображения) запрещены. Прикрепите другой тип файла.", reply_markup=menu.get_appropriate_menu(message.from_user.id))
            clear_user_data(chat_id)
            return
        # Если больше одного типа вложения — отказ
        if present_types > 1:
            bot.send_message(chat_id, "🚫 Можно прикрепить только одно вложение. Пожалуйста, отправьте только один файл или фото.", reply_markup=menu.get_appropriate_menu(message.from_user.id))
            clear_user_data(chat_id)
            return
        msg_text = ""
        if file_id:
            msg_text += f"[Вложение: {file_type}, file_id: {file_id}]\n"
        if hasattr(message, 'caption') and message.caption:
            msg_text += message.caption
        elif hasattr(message, 'text') and message.text and message.content_type == 'text':
            msg_text += message.text
        if not msg_text.strip():
            bot.send_message(chat_id, "Пожалуйста, опишите ваш вопрос или прикрепите файл.", reply_markup=menu.get_appropriate_menu(message.from_user.id))
            return
        contact_id = add_contact(str(chat_id), contact, msg_text)
        bot.send_message(chat_id, "✅ Ваше обращение отправлено админу. Ожидайте ответа.", reply_markup=menu.get_appropriate_menu(message.from_user.id))
        # Формируем admin_msg с четким разделением вложения и текста
        if file_id:
            admin_msg = (
                f"🆘 Новое обращение от пользователя {contact}\nID: {chat_id}\n\n"
                f"Вложение: [{file_type}, file_id: {file_id}]\n"
            )
            text_only = msg_text.replace(f"[Вложение: {file_type}, file_id: {file_id}]\n", "").strip()
            if text_only:
                admin_msg += f"\nТекст обращения:\n{text_only}\n"
        else:
            admin_msg = (
                f"🆘 Новое обращение от пользователя {contact}\nID: {chat_id}\n\n"
                f"Текст обращения:\n{msg_text.strip()}\n"
            )
        admin_msg += "\nДля ответа используйте меню обращений."
        bot.send_message(ADMIN_ID, admin_msg)
        if file_id:
            if file_type == 'photo':
                bot.send_photo(ADMIN_ID, file_id, caption=f"Обращение #{contact_id} от {contact}")
            elif file_type == 'document':
                bot.send_document(ADMIN_ID, file_id, caption=f"Обращение #{contact_id} от {contact}")
            elif file_type == 'voice':
                bot.send_voice(ADMIN_ID, file_id, caption=f"Обращение #{contact_id} от {contact}")
            elif file_type == 'audio':
                bot.send_audio(ADMIN_ID, file_id, caption=f"Обращение #{contact_id} от {contact}")
            elif file_type == 'video_note':
                bot.send_video_note(ADMIN_ID, file_id)
                bot.send_message(ADMIN_ID, f"Обращение #{contact_id} от {contact}")
            elif file_type == 'sticker':
                bot.send_sticker(ADMIN_ID, file_id)
                bot.send_message(ADMIN_ID, f"Обращение #{contact_id} от {contact}")
        clear_user_data(chat_id)

    @bot.message_handler(func=lambda m: m.text == "ℹ️ О преподавателе")
    def handle_about_teacher(message):
        text = (
            "👨‍🏫 <b>О преподавателе</b>\n\n"
            "Привет! Меня зовут Никита, мне 19 лет. Я преподаватель с опытом работы более года\n"
            "в крупной онлайн-школе и студент 4 курса по специальности «Прикладная информатика».\n\n"
            "👨‍💻 Помимо преподавания, разрабатываю собственные проекты — один из них это бот, в котором вы сейчас находитесь.\n"
            "👦 Я легко нахожу общий язык с детьми, стараюсь быть не просто учителем, а наставником и другом.\n"
            "🧠 Занятия проходят в дружелюбной и комфортной атмосфере, без скучных лекций — учим через практику и интерес.\n\n"
        )
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=menu.get_appropriate_menu(message.from_user.id))

    @bot.message_handler(func=lambda m: m.text == "💰 Цены и форматы")
    def handle_prices_formats(message):
        text = (
            "💰 <b>Формат и стоимость занятий</b>\n\n"
            "• Индивидуальное занятие: 800 руб / 55 минут\n"
            "• Формат: онлайн (Google Meet)\n"
            "Занятия проходят в удобное для вас время.\n"
            "По желанию можно обсудить другой формат или платформу.\n\n"
            "📩 Для записи и уточнений — пишите в личные сообщения!"
        )
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=menu.get_appropriate_menu(message.from_user.id))

    @bot.message_handler(func=lambda m: m.text == "📚 Доступные курсы")
    def handle_available_courses(message):
        courses = get_active_courses()
        if not courses:
            bot.send_message(message.chat.id, "⚠️ Сейчас нет активных курсов.", reply_markup=menu.get_appropriate_menu(message.from_user.id))
            return
        text = "<b>Доступные курсы:</b>\n\n"
        for c in courses:
            text += f"<b>{c[1]}</b>\n{c[2]}\n\n"
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=menu.get_appropriate_menu(message.from_user.id))

    @bot.message_handler(func=lambda m: m.text == "⭐ Отзывы")
    @error_handler()
    def handle_show_reviews_user(message):
        try:
            reviews = get_reviews_for_publication_with_deleted(limit=5)
            if not reviews or not isinstance(reviews, list):
                bot.send_message(message.chat.id, "Пока нет отзывов. Будьте первым! 😉", reply_markup=get_appropriate_menu(message.from_user.id))
                return
            msg = "⭐ Отзывы наших учеников:\n\n"
            for i, review in enumerate(reviews, 1):
                rating, feedback, is_anonymous, parent_name, student_name, course, created_at = review
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(created_at)
                    date_str = dt.strftime("%d.%m.%Y")
                except:
                    date_str = "недавно"
                stars = "⭐" * rating
                if parent_name is None and student_name is None:
                    author = "[Заявка удалена]"
                    course_display = "[Заявка удалена]"
                else:
                    author = f"{parent_name} ({student_name})"
                    course_display = course or "[Курс не указан]"
                msg += (
                    f"{i}. {stars} ({rating}/10)\n"
                    f"📘 Курс: {course_display}\n"
                    f"👤 {author}\n"
                    f"📝 {feedback[:100]}{'...' if len(feedback) > 100 else ''}\n"
                    f"📅 {date_str}\n\n"
                )
            msg += "💬 Хотите оставить свой отзыв? Напишите нам!"
            bot.send_message(message.chat.id, msg, reply_markup=get_appropriate_menu(message.from_user.id))
        except Exception as e:
            bot.send_message(message.chat.id, "⚠️ Произошла ошибка. Попробуйте позже.")

    @bot.message_handler(commands=["start"])
    @error_handler()
    def handle_start(message):
        import time
        start_time = time.time()
        
        security_ok, error_msg = check_user_security(message.from_user.id, "start")
        if not security_ok:
            bot.send_message(message.chat.id, f"🚫 {error_msg}")
            return
        
        bot.send_message(
            message.chat.id,
            "👋 <b>Добро пожаловать!</b>\n\n"
            "Я — бот, созданный лично преподавателем Никитой для записи на пробные занятия по программированию.\n"
            "Здесь вы можете оставить заявку, выбрать удобное время и задать вопросы.\n\n"
            "📌 Используйте меню ниже для навигации.\n"
            "ℹ️ Чтобы узнать подробнее, что я умею — отправьте команду /help.",
            reply_markup=menu.get_appropriate_menu(message.from_user.id)
        )
        
        # Логирование активности пользователя
        log_user_action(logger, message.from_user.id, "START_COMMAND", f"Username: {message.from_user.username}")
        
        # Логирование производительности
        response_time = time.time() - start_time
        logger.info(f"⏱️ Handler response time: {response_time:.3f}s (start command)")
        
        # Бизнес-метрики
        logger.info(f"📊 User activity: new user {message.from_user.id} started bot")
