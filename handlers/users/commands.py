# === handlers/commands.py ===
from telebot import types
import utils.menu as menu
from data.db import (
    get_application_by_tg_id, format_date_for_display, get_active_courses, get_cancelled_count_by_tg_id, get_finished_count_by_tg_id, get_all_archive, archive_application, get_last_contact_time, add_contact, update_application, delete_application_by_tg_id, get_reviews_for_publication_with_deleted
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
            "🤖 <b>Справка по боту:</b>\n\n"
            "📝 <b>Запись на занятие:</b>\n"
            "• Нажмите '📝 Записаться на занятие'\n"
            "• Заполните форму регистрации\n"
            "• Дождитесь назначения даты\n\n"
            "📅 <b>Информация о занятии:</b>\n"
            "• Нажмите '📅 Мое занятие'\n"
            "• Узнайте дату и ссылку на занятие\n\n"
            "✏️ <b>Редактирование заявки:</b>\n"
            "• Нажмите '✏️ Редактировать заявку'\n"
            "• Измените нужные данные\n\n"
            "❌ <b>Отмена заявки:</b>\n"
            "• Нажмите '❌ Отменить заявку'\n"
            "• Укажите причину отмены\n\n"
            "🆘 <b>Обращение к админу:</b>\n"
            "• Нажмите '🆘 Обратиться к админу'\n"
            "• Напишите ваш вопрос\n\n"
            "ℹ️ <b>Дополнительная информация:</b>\n"
            "• 'ℹ️ О преподавателе' - информация о преподавателе\n"
            "• '💰 Цены и форматы' - стоимость занятий\n"
            "• '📚 Доступные курсы' - список курсов"
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
        
        if not lesson_date:
            bot.send_message(chat_id, "⏳ Ваша заявка обрабатывается. Ожидайте назначения даты занятия.", reply_markup=menu.get_appropriate_menu(user.id))
            log_user_action(logger, user.id, "MY_LESSON_PENDING", f"Course: {course}, Status: {status}")
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
        
        # Проверяем, что заявка не назначена
        if app[9] == "Назначено":
            bot.send_message(chat_id, "❌ Нельзя редактировать назначенную заявку.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
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
        set_user_data(chat_id, {"edit_app": True, "app_id": app[0], "parent_name": parent_name, "student_name": student_name, "age": age, "contact": contact, "course": course})
        log_user_action(logger, call.from_user.id, "edit_application_started")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("edit_field:"))
    def handle_edit_field(call):
        # Проверка безопасности
        security_ok, error_msg = check_user_security(call.from_user.id, "edit_field")
        if not security_ok:
            bot.answer_callback_query(call.id, f"🚫 {error_msg}")
            return
        
        chat_id = call.message.chat.id
        field = call.data.split(":")[1]
        
        user_data = get_user_data(chat_id)
        if not user_data or not user_data.get("edit_app"):
            bot.send_message(chat_id, "❌ Данные для редактирования не найдены.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            return
        
        set_user_data(chat_id, {"editing_field": field})
        field_names = {
            "parent_name": "имя родителя",
            "student_name": "имя ученика", 
            "age": "возраст",
            "contact": "контакт",
            "course": "курс"
        }
        
        bot.send_message(chat_id, f"Введите новое {field_names.get(field, field)}:")
        bot.register_next_step_handler(call.message, process_edit_field)
        log_user_action(logger, call.from_user.id, f"edit_field_{field}")

    def process_edit_field(message):
        # Проверка безопасности
        security_ok, error_msg = check_user_security(message.from_user.id, "process_edit_field")
        if not security_ok:
            bot.send_message(message.chat.id, f"🚫 {error_msg}")
            return
        
        chat_id = message.chat.id
        
        user_data = get_user_data(chat_id)
        if not user_data or not user_data.get("edit_app"):
            bot.send_message(chat_id, "❌ Данные для редактирования не найдены.", reply_markup=menu.get_appropriate_menu(message.from_user.id))
            return
        
        field = get_user_data(chat_id).get("editing_field")
        new_value = message.text.strip()
        
        if not new_value:
            bot.send_message(chat_id, "❌ Значение не может быть пустым. Попробуйте снова.", reply_markup=menu.get_appropriate_menu(message.from_user.id))
            return
        
        # Обновляем значение
        update_user_data(chat_id, {field: new_value})
        clear_user_data(chat_id, "editing_field")
        
        # Показываем обновленные данные
        app_data = get_user_data(chat_id)
        msg = (
            f"✅ Обновленные данные:\n"
            f"👤 Родитель: {app_data['parent_name']}\n"
            f"🧒 Ученик: {app_data['student_name']}\n"
            f"🎂 Возраст: {app_data['age']}\n"
            f"📘 Курс: {app_data['course']}\n"
            f"📞 Контакт: {app_data.get('contact', 'не указан')}"
        )
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Сохранить", callback_data="save_edit"),
            types.InlineKeyboardButton("❌ Отменить", callback_data="cancel_edit")
        )
        
        bot.send_message(chat_id, msg, reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data == "save_edit")
    def handle_save_edit(call):
        # Проверка безопасности
        security_ok, error_msg = check_user_security(call.from_user.id, "save_edit")
        if not security_ok:
            bot.answer_callback_query(call.id, f"🚫 {error_msg}")
            return
        
        chat_id = call.message.chat.id
        
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
            
            # Очищаем данные
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
        
        # Проверяем, что заявка существует
        app = get_application_by_tg_id(str(chat_id))
        if not app:
            bot.send_message(chat_id, "❌ Заявка не найдена.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            return
        
        # Проверяем, что заявка не назначена
        if app[9] == "Назначено":
            bot.send_message(chat_id, "❌ Нельзя отменить назначенную заявку.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
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
        
        # Проверка безопасности
        security_ok, error_msg = check_user_security(call.from_user.id, "confirm_cancel_application")
        if not security_ok:
            bot.answer_callback_query(call.id, f"🚫 {error_msg}")
            return
        
        # Проверяем, что заявка все еще существует
        app = get_application_by_tg_id(str(chat_id))
        if not app:
            bot.send_message(chat_id, "❌ Заявка не найдена или уже обработана.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            clear_user_data(chat_id)
            return
        
        # Проверяем, что заявка не назначена
        if app[9] == "Назначено":
            bot.send_message(chat_id, "❌ Нельзя отменить назначенную заявку. Обратитесь к администратору.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            clear_user_data(chat_id)
            return
        
        reason = get_user_data(chat_id).get("cancel_reason", "")
        
        try:
            # Архивируем заявку
            archive_application(app[0], cancelled_by="user", comment=reason, archived_status="Заявка отменена")
            # Удаляем заявку из БД
            delete_application_by_tg_id(chat_id)
            bot.send_message(chat_id, "✅ Ваша заявка отменена.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            
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
        
        # Проверка безопасности
        security_ok, error_msg = check_user_security(call.from_user.id, "confirm_cancel_lesson_user")
        if not security_ok:
            bot.answer_callback_query(call.id, f"🚫 {error_msg}")
            return
        
        # Проверяем, что заявка все еще существует
        app = get_application_by_tg_id(str(chat_id))
        if not app:
            bot.send_message(chat_id, "❌ Заявка не найдена или уже обработана.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            clear_user_data(chat_id)
            return
        
        # Проверяем, что заявка назначена
        if app[9] != "Назначено":
            bot.send_message(chat_id, "❌ Нельзя отменить неназначенный урок.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            clear_user_data(chat_id)
            return
        
        reason = get_user_data(chat_id).get("cancel_lesson_reason", "")
        
        try:
            # Архивируем заявку
            archive_application(app[0], cancelled_by="user", comment=reason, archived_status="Урок отменён")
            # Удаляем заявку из БД
            delete_application_by_tg_id(chat_id)
            bot.send_message(chat_id, "✅ Ваш урок отменён.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            
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
            "👩‍ <b>О преподавателе</b>\n\n"
            "Меня зовут Никита, я профессиональный преподаватель с большим опытом работы.\n"
            "Провожу индивидуальные и групповые занятия для детей и взрослых.\n\n"
            "📚 Использую современные методики и индивидуальный подход к каждому ученику.\n"
            "\nСвязаться со мной: @your_teacher_username"
        )
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=menu.get_appropriate_menu(message.from_user.id))

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
                bot.send_message(message.chat.id, "Пока нет отзывов. Будьте первым! 😊", reply_markup=get_appropriate_menu(message.from_user.id))
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
            "👋 Добро пожаловать! Я бот для записи на занятия. Используйте меню для навигации.",
            reply_markup=menu.get_appropriate_menu(message.from_user.id)
        )
        
        # Логирование активности пользователя
        log_user_action(logger, message.from_user.id, "START_COMMAND", f"Username: {message.from_user.username}")
        
        # Логирование производительности
        response_time = time.time() - start_time
        logger.info(f"⏱️ Handler response time: {response_time:.3f}s (start command)")
        
        # Бизнес-метрики
        logger.info(f"📊 User activity: new user {message.from_user.id} started bot")
