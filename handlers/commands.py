# === handlers/commands.py ===
from telebot import types
from utils.menu import get_main_menu, get_admin_menu, get_cancel_button
from data.db import get_application_by_tg_id, format_date_for_display, get_active_courses, get_cancelled_count_by_tg_id, get_finished_count_by_tg_id, get_all_archive, archive_application
from handlers.admin import is_admin
from utils.logger import log_user_action, log_error
from state.users import user_data
from config import ADMIN_ID


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
        chat_id = message.chat.id
        app = get_application_by_tg_id(str(chat_id))
        if not app:
            bot.send_message(chat_id, "Вы ещё не регистрировались. Нажмите «📋 Записаться».", reply_markup=get_main_menu())
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
        # ... остальная логика (урок назначен или завершён)

    @bot.callback_query_handler(func=lambda c: c.data == "edit_application")
    def handle_edit_application(call):
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
        chat_id = call.message.chat.id
        field = call.data.split(":")[1]
        prompts = {
            "parent_name": "Введите новое имя родителя:",
            "student_name": "Введите новое имя ученика:",
            "age": "Введите новый возраст:",
            "course": "Выберите новый курс:",
            "contact": "Введите новый номер телефона:"
        }
        if field == "course":
            courses = get_active_courses()
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            for c in courses:
                markup.add(c[1])
            markup.add("🔙 Отмена")
            bot.send_message(chat_id, prompts[field], reply_markup=markup)
        else:
            bot.send_message(chat_id, prompts[field], reply_markup=get_cancel_button())
        user_data[chat_id]["edit_field"] = field
        bot.register_next_step_handler(call.message, process_edit_field)

    def process_edit_field(message):
        chat_id = message.chat.id
        if message.text == "🔙 Отмена":
            bot.send_message(chat_id, "Редактирование отменено.", reply_markup=get_main_menu())
            user_data.pop(chat_id, None)
            return
        field = user_data[chat_id].get("edit_field")
        value = message.text.strip()
        # Валидация
        if field == "age":
            if not value.isdigit() or not (3 <= int(value) <= 99):
                bot.send_message(chat_id, "Возраст должен быть числом от 3 до 99.")
                return bot.register_next_step_handler(message, process_edit_field)
        if field == "course":
            courses = [c[1] for c in get_active_courses()]
            if value not in courses:
                bot.send_message(chat_id, "Пожалуйста, выберите курс из списка.")
                return bot.register_next_step_handler(message, process_edit_field)
        if field in ("parent_name", "student_name"):
            if not value or not value.replace(" ", "").isalpha():
                bot.send_message(chat_id, "Имя должно содержать только буквы.")
                return bot.register_next_step_handler(message, process_edit_field)
        if field == "contact":
            import re
            if not re.match(r"^\+?\d{10,15}$", value):
                bot.send_message(chat_id, "Введите корректный номер телефона (10-15 цифр, можно с +)")
                return bot.register_next_step_handler(message, process_edit_field)
        # Сохраняем новое значение
        user_data[chat_id][field] = value
        # Показываем обновлённую заявку и просим подтвердить
        app = user_data[chat_id]
        msg = (
            f"Проверьте обновлённые данные:\n"
            f"👤 Родитель: {app['parent_name']}\n"
            f"🧒 Ученик: {app['student_name']}\n"
            f"🎂 Возраст: {app['age']}\n"
            f"📘 Курс: {app['course']}\n"
            f"📞 Контакт: {app['contact'] or 'не указан'}"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_edit_application"))
        markup.add(types.InlineKeyboardButton("❌ Отменить", callback_data="cancel_edit_application"))
        bot.send_message(chat_id, msg, reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data == "confirm_edit_application")
    def handle_confirm_edit_application(call):
        chat_id = call.message.chat.id
        app = user_data.get(chat_id)
        if not app:
            bot.send_message(chat_id, "Данные не найдены.")
            return
        # Обновляем заявку в БД
        import sqlite3
        conn = sqlite3.connect("data/database.db")
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE applications SET parent_name=?, student_name=?, age=?, contact=?, course=? WHERE id=?
        """, (app["parent_name"], app["student_name"], app["age"], app["contact"], app["course"], app["app_id"]))
        conn.commit()
        conn.close()
        # Уведомляем пользователя и админа
        bot.send_message(chat_id, "✅ Заявка успешно обновлена!", reply_markup=get_main_menu())
        from handlers.admin import notify_admin_new_application
        notify_admin_new_application(bot, app)
        user_data.pop(chat_id, None)

    @bot.callback_query_handler(func=lambda c: c.data == "cancel_edit_application")
    def handle_cancel_edit_application(call):
        chat_id = call.message.chat.id
        user_data.pop(chat_id, None)
        bot.send_message(chat_id, "Редактирование отменено.", reply_markup=get_main_menu())

    @bot.callback_query_handler(func=lambda c: c.data == "cancel_application")
    def handle_cancel_application(call):
        chat_id = call.message.chat.id
        # Запрашиваем причину отмены
        bot.send_message(chat_id, "Пожалуйста, укажите причину отмены заявки:", reply_markup=get_cancel_button())
        user_data[chat_id] = user_data.get(chat_id, {})
        user_data[chat_id]["cancel_stage"] = True
        bot.register_next_step_handler(call.message, process_cancel_reason)

    def process_cancel_reason(message):
        chat_id = message.chat.id
        # Проверяем, что это сообщение, а не callback
        if hasattr(message, 'text') and message.text == "🔙 Отмена":
            bot.send_message(chat_id, "Отмена отмены заявки.", reply_markup=get_main_menu())
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
        from data.db import get_application_by_tg_id, archive_application
        app = get_application_by_tg_id(str(chat_id))
        reason = user_data.get(chat_id, {}).get("cancel_reason", "")
        if app:
            archive_application(app[0], cancelled_by="user", comment=reason, archived_status="Заявка отменена")
        # Удаляем заявку из БД
        import sqlite3
        conn = sqlite3.connect("data/database.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM applications WHERE tg_id = ?", (str(chat_id),))
        conn.commit()
        conn.close()
        bot.send_message(chat_id, "Ваша заявка отменена.", reply_markup=get_main_menu())
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
        bot.send_message(chat_id, "Отмена отмены заявки.", reply_markup=get_main_menu())
    
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
