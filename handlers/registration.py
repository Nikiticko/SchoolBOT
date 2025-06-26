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
from utils.logger import log_user_action, log_error


def handle_existing_registration(bot, chat_id):
    markup = get_main_menu()
    bot.send_message(chat_id, "📝 Вы уже оставляли заявку. Ожидайте назначения урока.", reply_markup=markup)


def register(bot, logger):
    @bot.message_handler(func=lambda m: m.text == "📋 Записаться")
    def handle_signup(message):
        try:
            chat_id = message.chat.id

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
                course, date, link = app[6], app[7], app[8]
                if not date and not link:
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
        
        # Проверяем отмену
        if message.text == "🔙 Отмена":
            handle_cancel_action(bot, message, "регистрация", logger)
            return
            
        if user_data.get(chat_id, {}).get("stage") != "parent_name":
            return
            
        user_data[chat_id]["parent_name"] = message.text.strip()
        user_data[chat_id]["stage"] = "student_name"
        bot.send_message(chat_id, "Введите имя ученика:", reply_markup=get_cancel_button())
        bot.register_next_step_handler(message, process_student_name)

    def process_student_name(message):
        chat_id = message.chat.id
        
        # Проверяем отмену
        if message.text == "🔙 Отмена":
            handle_cancel_action(bot, message, "регистрация", logger)
            return
            
        if user_data.get(chat_id, {}).get("stage") != "student_name":
            return
            
        user_data[chat_id]["student_name"] = message.text.strip()
        user_data[chat_id]["stage"] = "age"
        bot.send_message(chat_id, "Введите возраст ученика:", reply_markup=get_cancel_button())
        bot.register_next_step_handler(message, process_age)

    def process_age(message):
        chat_id = message.chat.id
        
        # Проверяем отмену
        if message.text == "🔙 Отмена":
            handle_cancel_action(bot, message, "регистрация", logger)
            return
            
        if user_data.get(chat_id, {}).get("stage") != "age":
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
        # Сохраняем в user_data FSM
        from state.users import user_data
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
        from state.users import user_data
        user_data[chat_id]["edit_field"] = field
        bot.register_next_step_handler(call.message, process_edit_field)

    def process_edit_field(message):
        chat_id = message.chat.id
        from state.users import user_data
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
        from state.users import user_data
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
        notify_admin_new_application(bot, app)
        user_data.pop(chat_id, None)

    @bot.callback_query_handler(func=lambda c: c.data == "cancel_edit_application")
    def handle_cancel_edit_application(call):
        chat_id = call.message.chat.id
        from state.users import user_data
        user_data.pop(chat_id, None)
        bot.send_message(chat_id, "Редактирование отменено.", reply_markup=get_main_menu())

    @bot.callback_query_handler(func=lambda c: c.data == "cancel_application")
    def handle_cancel_application(call):
        chat_id = call.message.chat.id
        # Подтверждение отмены
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_cancel_application"))
        markup.add(types.InlineKeyboardButton("❌ Отменить", callback_data="cancel_cancel_application"))
        bot.send_message(chat_id, "Вы уверены, что хотите отменить заявку?", reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data == "confirm_cancel_application")
    def handle_confirm_cancel_application(call):
        chat_id = call.message.chat.id
        # Удаляем заявку из БД
        import sqlite3
        conn = sqlite3.connect("data/database.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM applications WHERE tg_id = ?", (str(chat_id),))
        conn.commit()
        conn.close()
        bot.send_message(chat_id, "Ваша заявка отменена.", reply_markup=get_main_menu())
        # Можно уведомить админа
        notify_admin_new_application(bot, {"tg_id": chat_id, "action": "cancelled"})

    @bot.callback_query_handler(func=lambda c: c.data == "cancel_cancel_application")
    def handle_cancel_cancel_application(call):
        chat_id = call.message.chat.id
        bot.send_message(chat_id, "Отмена отмены заявки.", reply_markup=get_main_menu())
