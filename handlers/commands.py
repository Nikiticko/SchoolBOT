# === handlers/commands.py ===
from telebot import types
import utils.menu as menu
from data.db import get_application_by_tg_id, format_date_for_display, get_active_courses, get_cancelled_count_by_tg_id, get_finished_count_by_tg_id, get_all_archive, archive_application, is_user_banned, get_last_contact_time, add_contact, get_ban_reason, update_application, delete_application_by_tg_id
from handlers.admin import is_admin
from utils.logger import log_user_action, log_error, setup_logger
from state.users import user_data
from config import ADMIN_ID
from utils.security import check_user_security, validate_user_input, security_manager

def register_handlers(bot):
    """Регистрация обработчиков команд"""
    logger = setup_logger('commands')
    register(bot, logger)

def register(bot, logger):  

    @bot.message_handler(commands=["start"])
    def handle_start(message):
        try:
            # Проверка безопасности
            security_ok, error_msg = check_user_security(message.from_user.id, "start_command")
            if not security_ok:
                bot.send_message(message.chat.id, f"🚫 {error_msg}")
                return
            
            if is_admin(message.from_user.id):
                markup = menu.get_admin_menu()
                welcome = "👋 Добро пожаловать, администратор!\n\nВыберите действие из админ-меню:"
            else:
                markup = menu.get_main_menu()
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
            # Проверка безопасности
            security_ok, error_msg = check_user_security(chat_id, "my_lesson")
            if not security_ok:
                return f"🚫 {error_msg}", show_menu
            
            # Проверка отмен
            if get_cancelled_count_by_tg_id(str(chat_id)) >= 2:
                return "🚫 У вас 2 или более отменённых заявок или уроков. Запись невозможна. Свяжитесь с администратором.", show_menu

            # Проверка завершённых уроков
            if get_finished_count_by_tg_id(str(chat_id)) >= 1:
                # Найти последнюю завершённую заявку в архиве
                archive = get_all_archive()
                for row in archive:
                    if row[1] == str(chat_id) and row[9] == 'Завершено':
                        course = row[6]
                        student_name = row[3]
                        parent_name = row[2]
                        lesson_date = format_date_for_display(row[7])
                        comment = row[12]
                        msg = f"✅ Ваш пробный урок по курсу '{course}' для ученика {student_name} ({parent_name}) на {lesson_date} уже прошёл.\n\nОбратная связь: {comment}"
                        return msg, show_menu
                return "✅ Ваш пробный урок уже прошёл.", show_menu

            app = get_application_by_tg_id(str(chat_id))
            if not app:
                return "Вы ещё не регистрировались. Нажмите «📋 Записаться».", show_menu
            course = app[6]
            date = app[7]
            link = app[8]
            status = app[9]
            if status != "Назначено":
                # Показываем заявку и кнопки
                parent_name = app[2]
                student_name = app[3]
                age = app[4]
                contact = app[5]
                course = app[6]
                msg = (
                    f"Ваша заявка на рассмотрении:\n"
                    f"👤 Родитель: {parent_name}\n"
                    f"🧒 Ученик: {student_name}\n"
                    f"🎂 Возраст: {age}\n"
                    f"📘 Курс: {course}\n"
                    f"📞 Контакт: {contact or 'не указан'}"
                )
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("✏️ Редактировать заявку", callback_data="edit_application"),
                    types.InlineKeyboardButton("❌ Отменить заявку", callback_data="cancel_application")
                )
                bot.send_message(chat_id, msg, reply_markup=markup)
                return
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
            # Проверка безопасности
            security_ok, error_msg = check_user_security(message.from_user.id, "my_lesson_command")
            if not security_ok:
                bot.send_message(message.chat.id, f"🚫 {error_msg}")
                return
            
            msg, _ = _handle_my_lesson_logic(message.chat.id)
            bot.send_message(message.chat.id, msg)
            log_user_action(logger, message.from_user.id, "my_lesson_command")
        except Exception as e:
            log_error(logger, e, f"My lesson command for user {message.from_user.id}")

    @bot.message_handler(commands=["help"])
    def handle_help(message):
        try:
            # Проверка безопасности
            security_ok, error_msg = check_user_security(message.from_user.id, "help_command")
            if not security_ok:
                bot.send_message(message.chat.id, f"🚫 {error_msg}")
                return
            
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
        # Проверка безопасности
        security_ok, error_msg = check_user_security(message.from_user.id, "my_lesson_button")
        if not security_ok:
            bot.send_message(message.chat.id, f"🚫 {error_msg}")
            return
        
        chat_id = message.chat.id
        app = get_application_by_tg_id(str(chat_id))
        if not app:
            bot.send_message(chat_id, "Вы ещё не регистрировались. Нажмите «📋 Записаться».", reply_markup=menu.get_main_menu())
            return
        course, date, link = app[6], app[7], app[8]
        if not date and not link:
            # Показываем заявку и кнопки
            parent_name = app[2]
            student_name = app[3]
            age = app[4]
            contact = app[5]
            course = app[6]
            msg = (
                f"Ваша заявка на рассмотрении:\n"
                f"👤 Родитель: {parent_name}\n"
                f"🧒 Ученик: {student_name}\n"
                f"🎂 Возраст: {age}\n"
                f"📘 Курс: {course}\n"
                f"📞 Контакт: {contact or 'не указан'}"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✏️ Редактировать заявку", callback_data="edit_application"),
                types.InlineKeyboardButton("❌ Отменить заявку", callback_data="cancel_application")
            )
            bot.send_message(chat_id, msg, reply_markup=markup)
            return
        # Если урок назначен, показываем детали и кнопку отмены урока
        if date and link:
            formatted_date = format_date_for_display(date)
            msg = f"📅 Дата: {formatted_date}\n📘 Курс: {course}\n🔗 Ссылка: {link}"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🚫 Отменить урок", callback_data="cancel_lesson_user"))
            bot.send_message(chat_id, msg, reply_markup=markup)
            return

    @bot.callback_query_handler(func=lambda c: c.data == "edit_application")
    def handle_edit_application(call):
        # Проверка безопасности
        security_ok, error_msg = check_user_security(call.from_user.id, "edit_application")
        if not security_ok:
            bot.answer_callback_query(call.id, f"🚫 {error_msg}")
            return
        
        chat_id = call.message.chat.id
        app = get_application_by_tg_id(str(chat_id))
        if not app:
            bot.send_message(chat_id, "Заявка не найдена.")
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
            fields.append(("Контакт (номер телефона)", "contact"))
        markup = types.InlineKeyboardMarkup()
        for label, key in fields:
            markup.add(types.InlineKeyboardButton(label, callback_data=f"edit_field:{key}"))
        bot.send_message(chat_id, "Что вы хотите изменить?", reply_markup=markup)
        user_data[chat_id] = {
            "edit_app": True,
            "app_id": app[0],
            "parent_name": parent_name,
            "student_name": student_name,
            "age": age,
            "contact": contact,
            "course": course
        }

    @bot.callback_query_handler(func=lambda c: c.data.startswith("edit_field:"))
    def handle_edit_field(call):
        # Проверка безопасности
        security_ok, error_msg = check_user_security(call.from_user.id, "edit_field")
        if not security_ok:
            bot.answer_callback_query(call.id, f"🚫 {error_msg}")
            return
        
        chat_id = call.message.chat.id
        field = call.data.split(":")[1]
        prompts = {
            "parent_name": "Введите новое имя родителя:",
            "student_name": "Введите новое имя ученика:",
            "age": "Введите новый возраст:",
            "course": "Выберите новый курс:",
            "contact": "Введите новый номер телефона:"
        }
        
        if field in prompts:
            bot.send_message(chat_id, prompts[field], reply_markup=menu.get_cancel_button())
            user_data[chat_id]["editing_field"] = field
            bot.register_next_step_handler(call.message, process_edit_field)
        else:
            bot.send_message(chat_id, "❌ Неизвестное поле для редактирования")

    def process_edit_field(message):
        # Проверка безопасности
        security_ok, error_msg = check_user_security(message.from_user.id, "process_edit_field")
        if not security_ok:
            bot.send_message(message.chat.id, f"🚫 {error_msg}")
            return
        
        chat_id = message.chat.id
        
        # Проверяем отмену
        if message.text == "🔙 Отмена":
            user_data.pop(chat_id, None)
            bot.send_message(chat_id, "❌ Редактирование отменено", reply_markup=menu.get_main_menu())
            return
        
        if chat_id not in user_data or "editing_field" not in user_data[chat_id]:
            bot.send_message(chat_id, "❌ Ошибка: данные редактирования не найдены")
            return
        
        field = user_data[chat_id]["editing_field"]
        value = message.text.strip()
        
        # Валидация в зависимости от поля
        if field in ["parent_name", "student_name"]:
            is_valid, error_msg = validate_user_input(value, "name")
        elif field == "age":
            is_valid, error_msg = validate_user_input(value, "age")
        elif field == "contact":
            is_valid, error_msg = validate_user_input(value, "phone")
        elif field == "course":
            is_valid, error_msg = validate_user_input(value, "course")
        else:
            is_valid, error_msg = validate_user_input(value, "message")
        
        if not is_valid:
            bot.send_message(chat_id, f"❌ {error_msg}\nПопробуйте еще раз:")
            bot.register_next_step_handler(message, process_edit_field)
            return
        
        # Сохраняем новое значение
        user_data[chat_id][field] = value
        del user_data[chat_id]["editing_field"]
        
        # Показываем подтверждение
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Подтвердить изменения", callback_data="confirm_edit_application"),
            types.InlineKeyboardButton("❌ Отменить", callback_data="cancel_edit_application")
        )
        
        summary = f"Новое значение для поля '{field}': {value}\n\nПодтвердите изменения:"
        bot.send_message(chat_id, summary, reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data == "confirm_edit_application")
    def handle_confirm_edit_application(call):
        chat_id = call.message.chat.id
        app = user_data.get(chat_id)
        if not app:
            bot.send_message(chat_id, "Данные не найдены.")
            return
        # Обновляем заявку в БД
        update_application(
            app["app_id"], 
            app["parent_name"], 
            app["student_name"], 
            app["age"], 
            app["contact"], 
            app["course"]
        )
        # Уведомляем пользователя и админа
        bot.send_message(chat_id, "✅ Заявка успешно обновлена!", reply_markup=menu.get_main_menu())
        from handlers.admin import notify_admin_new_application
        notify_admin_new_application(bot, app)
        user_data.pop(chat_id, None)

    @bot.callback_query_handler(func=lambda c: c.data == "cancel_edit_application")
    def handle_cancel_edit_application(call):
        chat_id = call.message.chat.id
        user_data.pop(chat_id, None)
        bot.send_message(chat_id, "Редактирование отменено.", reply_markup=menu.get_main_menu())

    @bot.callback_query_handler(func=lambda c: c.data == "cancel_application")
    def handle_cancel_application(call):
        chat_id = call.message.chat.id
        # Запрашиваем причину отмены
        bot.send_message(chat_id, "Пожалуйста, укажите причину отмены заявки:", reply_markup=menu.get_cancel_button())
        user_data[chat_id] = user_data.get(chat_id, {})
        user_data[chat_id]["cancel_stage"] = True
        bot.register_next_step_handler(call.message, process_cancel_reason)

    def process_cancel_reason(message):
        chat_id = message.chat.id
        # Проверяем, что это сообщение, а не callback
        if hasattr(message, 'text') and message.text == "🔙 Отмена":
            bot.send_message(chat_id, "Отмена отмены заявки.", reply_markup=menu.get_main_menu())
            user_data.pop(chat_id, None)
            return
        reason = getattr(message, 'text', '').strip()
        # Подтверждение отмены
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_cancel_application"))
        markup.add(types.InlineKeyboardButton("❌ Отменить", callback_data="cancel_cancel_application"))
        user_data[chat_id]["cancel_reason"] = reason
        bot.send_message(chat_id, f"Вы уверены, что хотите отменить заявку?\nПричина: {reason}", reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data == "confirm_cancel_application")
    def handle_confirm_cancel_application(call):
        chat_id = call.message.chat.id
        app = get_application_by_tg_id(str(chat_id))
        reason = user_data.get(chat_id, {}).get("cancel_reason", "")
        if app:
            archive_application(app[0], cancelled_by="user", comment=reason, archived_status="Заявка отменена")
        # Удаляем заявку из БД
        delete_application_by_tg_id(chat_id)
        bot.send_message(chat_id, "Ваша заявка отменена.", reply_markup=menu.get_main_menu())
        # Подробное уведомление админу
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
        user_data.pop(chat_id, None)

    @bot.callback_query_handler(func=lambda c: c.data == "cancel_cancel_application")
    def handle_cancel_cancel_application(call):
        chat_id = call.message.chat.id
        bot.send_message(chat_id, "Отмена отмены заявки.", reply_markup=menu.get_main_menu())
    
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
                bot.send_message(call.message.chat.id, msg, parse_mode="Markdown", reply_markup=menu.get_main_menu(call.message.chat.id))
                log_user_action(logger, call.from_user.id, "course_info_viewed", f"course: {name}")
            else:
                bot.send_message(call.message.chat.id, "⚠️ Курс не найден.", reply_markup=menu.get_main_menu(call.message.chat.id))
                log_user_action(logger, call.from_user.id, "course_not_found", f"course_id: {course_id}")
        except Exception as e:
            log_error(logger, e, f"Course info for user {call.from_user.id}")

    @bot.callback_query_handler(func=lambda c: c.data == "cancel_lesson_user")
    def handle_cancel_lesson_user(call):
        chat_id = call.message.chat.id
        bot.send_message(chat_id, "Пожалуйста, укажите причину отмены урока:", reply_markup=menu.get_cancel_button())
        user_data[chat_id] = user_data.get(chat_id, {})
        user_data[chat_id]["cancel_lesson_stage"] = True
        bot.register_next_step_handler(call.message, process_cancel_lesson_reason)

    def process_cancel_lesson_reason(message):
        chat_id = message.chat.id
        if hasattr(message, 'text') and message.text == "🔙 Отмена":
            bot.send_message(chat_id, "Отмена отмены урока.", reply_markup=menu.get_main_menu())
            user_data.pop(chat_id, None)
            return
        reason = getattr(message, 'text', '').strip()
        # Подтверждение
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_cancel_lesson_user"))
        markup.add(types.InlineKeyboardButton("❌ Отменить", callback_data="cancel_cancel_lesson_user"))
        user_data[chat_id]["cancel_lesson_reason"] = reason
        bot.send_message(chat_id, f"Вы уверены, что хотите отменить урок?\nПричина: {reason}", reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data == "confirm_cancel_lesson_user")
    def handle_confirm_cancel_lesson_user(call):
        chat_id = call.message.chat.id
        app = get_application_by_tg_id(str(chat_id))
        reason = user_data.get(chat_id, {}).get("cancel_lesson_reason", "")
        if app:
            archive_application(app[0], cancelled_by="user", comment=reason, archived_status="Урок отменён")
            # Удаляем заявку из БД
            delete_application_by_tg_id(chat_id)
            bot.send_message(chat_id, "Ваш урок отменён.", reply_markup=menu.get_main_menu())
            # Уведомление админу
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
        user_data.pop(chat_id, None)

    @bot.callback_query_handler(func=lambda c: c.data == "cancel_cancel_lesson_user")
    def handle_cancel_cancel_lesson_user(call):
        chat_id = call.message.chat.id
        bot.send_message(chat_id, "Отмена отмены урока.", reply_markup=menu.get_main_menu())

    @bot.message_handler(func=lambda m: m.text == "🆘 Обратиться к админу")
    def handle_contact_admin(message):
        from data.db import is_user_banned, get_last_contact_time, add_contact
        import datetime
        chat_id = message.chat.id
        user = message.from_user
        if is_user_banned(str(chat_id)):
            reason = get_ban_reason(str(chat_id))
            msg = "🚫 Вы заблокированы и не можете отправлять обращения."
            if reason:
                msg += f"\nПричина: {reason}"
            bot.send_message(chat_id, msg, reply_markup=menu.get_main_menu())
            return
        last_time = get_last_contact_time(str(chat_id))
        if last_time:
            last_dt = datetime.datetime.fromisoformat(last_time)
            if (datetime.datetime.now() - last_dt).total_seconds() < 20*60:
                bot.send_message(chat_id, "⏳ Вы можете отправлять обращения не чаще, чем раз в 20 минут.", reply_markup=menu.get_main_menu())
                return
        bot.send_message(chat_id, "✍️ Опишите ваш вопрос или прикрепите файл (фото, документ, голосовое, видео).\n\nДля отмены нажмите '🔙 Отмена'.", reply_markup=menu.get_cancel_button())
        user_data[chat_id] = {"contact_fsm": True}
        bot.register_next_step_handler(message, process_contact_message)

    def process_contact_message(message):
        from data.db import add_contact
        chat_id = message.chat.id
        user = message.from_user
        if hasattr(message, 'text') and message.text == "🔙 Отмена":
            bot.send_message(chat_id, "Обращение отменено.", reply_markup=menu.get_main_menu())
            user_data.pop(chat_id, None)
            return
        # Определяем контакт
        contact = f"@{user.username}" if user.username else (user_data.get(chat_id, {}).get("phone") or str(chat_id))
        # Определяем вложение
        file_id = None
        file_type = None
        if message.content_type == 'photo':
            file_id = message.photo[-1].file_id
            file_type = 'photo'
        elif message.content_type == 'document':
            file_id = message.document.file_id
            file_type = 'document'
        elif message.content_type == 'voice':
            file_id = message.voice.file_id
            file_type = 'voice'
        elif message.content_type == 'video':
            file_id = message.video.file_id
            file_type = 'video'
        elif message.content_type == 'video_note':
            file_id = message.video_note.file_id
            file_type = 'video_note'
        # Сохраняем обращение
        if file_id:
            msg_text = f"[Вложение: {file_type}, file_id: {file_id}]\n" + (message.caption or "")
        else:
            msg_text = message.text or "(без текста)"
        contact_id = add_contact(str(chat_id), contact, msg_text)
        bot.send_message(chat_id, "✅ Ваше обращение отправлено админу. Ожидайте ответа.", reply_markup=menu.get_main_menu())
        # Уведомление админу
        admin_msg = f"🆘 Новое обращение от пользователя {contact}\nID: {chat_id}\n\nТекст: {msg_text}\n\nДля ответа используйте меню обращений."
        bot.send_message(ADMIN_ID, admin_msg)
        # Пересылаем вложение админу, если есть
        if file_id:
            if file_type == 'photo':
                bot.send_photo(ADMIN_ID, file_id, caption=f"Обращение #{contact_id} от {contact}")
            elif file_type == 'document':
                bot.send_document(ADMIN_ID, file_id, caption=f"Обращение #{contact_id} от {contact}")
            elif file_type == 'voice':
                bot.send_voice(ADMIN_ID, file_id, caption=f"Обращение #{contact_id} от {contact}")
            elif file_type == 'video':
                bot.send_video(ADMIN_ID, file_id, caption=f"Обращение #{contact_id} от {contact}")
            elif file_type == 'video_note':
                bot.send_video_note(ADMIN_ID, file_id)
        user_data.pop(chat_id, None)

    @bot.message_handler(func=lambda m: m.text == "ℹ️ О преподавателе")
    def handle_about_teacher(message):
        text = (
            "👩‍🏫 <b>О преподавателе</b>\n\n"
            "Меня зовут Никита, я профессиональный преподаватель с большим опытом работы.\n"
            "Провожу индивидуальные и групповые занятия для детей и взрослых.\n\n"
            "📚 Использую современные методики и индивидуальный подход к каждому ученику.\n"
            "\nСвязаться со мной: @your_teacher_username"
        )
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=menu.get_main_menu())

    @bot.message_handler(func=lambda m: m.text == "💰 Цены и форматы")
    def handle_prices_formats(message):
        text = (
            "💰 <b>Цены и форматы занятий</b>\n\n"
            "• Индивидуальное занятие: 1000 руб/час\n"
            "• Групповое занятие: 700 руб/час\n"
            "• Пробный урок: бесплатно\n\n"
            "Занятия проходят онлайн и офлайн.\n"
            "\nДля подробностей — обращайтесь в личные сообщения!"
        )
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=menu.get_main_menu())

    @bot.message_handler(func=lambda m: m.text == "📚 Доступные курсы")
    def handle_available_courses(message):
        courses = get_active_courses()
        if not courses:
            bot.send_message(message.chat.id, "⚠️ Сейчас нет активных курсов.", reply_markup=menu.get_main_menu())
            return
        text = "<b>Доступные курсы:</b>\n\n"
        for c in courses:
            text += f"<b>{c[1]}</b>\n{c[2]}\n\n"
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=menu.get_main_menu())
