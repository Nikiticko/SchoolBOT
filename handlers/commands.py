# === handlers/commands.py ===
from telebot import types
import utils.menu as menu
from data.db import (
    get_application_by_tg_id, format_date_for_display, get_active_courses, get_cancelled_count_by_tg_id, get_finished_count_by_tg_id, get_all_archive, archive_application, is_user_banned, get_last_contact_time, add_contact, get_ban_reason, update_application, delete_application_by_tg_id
)
from utils.logger import log_user_action, log_error, setup_logger
from state.users import user_data
from config import ADMIN_ID
from utils.security import check_user_security, validate_user_input, security_manager
from utils.decorators import error_handler, ensure_text_message, ensure_stage

def register_handlers(bot):
    """Регистрация обработчиков команд"""
    logger = setup_logger('commands')
    register(bot, logger)

def register(bot, logger):  

    @bot.message_handler(commands=["start"])
    @error_handler()
    def handle_start(message):
        # Проверка безопасности
        security_ok, error_msg = check_user_security(message.from_user.id, "start")
        if not security_ok:
            bot.send_message(message.chat.id, f"🚫 {error_msg}")
            return
        
        chat_id = message.chat.id
        user = message.from_user
        
        # Проверяем, есть ли уже заявка у пользователя
        existing_app = get_application_by_tg_id(str(chat_id))
        
        if existing_app:
            # У пользователя уже есть заявка
            app_id, tg_id, parent_name, student_name, age, contact, course, lesson_date, lesson_link, status, created_at, reminder_sent = existing_app
            
            if status == "Ожидает":
                msg = (
                    f"👋 Привет, {parent_name}!\n\n"
                    f"✅ У вас уже есть активная заявка:\n"
                    f"🧒 Ученик: {student_name}\n"
                    f"🎂 Возраст: {age}\n"
                    f"📘 Курс: {course}\n"
                    f"📊 Статус: Ожидает назначения даты\n\n"
                    f"⏳ Мы скоро свяжемся с вами для назначения занятия!"
                )
            elif status == "Назначено":
                formatted_date = lesson_date if isinstance(lesson_date, str) else lesson_date.strftime("%d.%m %H:%M")
                msg = (
                    f"👋 Привет, {parent_name}!\n\n"
                    f"✅ У вас назначено занятие:\n"
                    f"🧒 Ученик: {student_name}\n"
                    f"�� Курс: {course}\n"
                    f"📅 Дата: {formatted_date}\n"
                    f"🔗 Ссылка: {lesson_link}\n\n"
                    f"🎯 Готовьтесь к занятию!"
                )
            
            bot.send_message(chat_id, msg, reply_markup=menu.get_appropriate_menu(user.id))
        else:
            # У пользователя нет заявки
            msg = (
                f"👋 Привет, {user.first_name}!\n\n"
                f"🎓 Добро пожаловать в бот для записи на занятия!\n\n"
                f"📝 Для записи на занятие нажмите кнопку '📝 Записаться на занятие'\n\n"
                f"ℹ️ Для получения дополнительной информации используйте меню ниже"
            )
            bot.send_message(chat_id, msg, reply_markup=menu.get_appropriate_menu(user.id))
        
        log_user_action(logger, user.id, "start")

    def _handle_my_lesson_logic(chat_id, show_menu=False):
        """Логика для получения информации о занятии"""
        app = get_application_by_tg_id(str(chat_id))
        
        if not app:
            msg = "❌ У вас нет активной заявки на занятие.\n\n📝 Для записи нажмите '📝 Записаться на занятие'"
            return msg, show_menu, None
        
        app_id, tg_id, parent_name, student_name, age, contact, course, lesson_date, lesson_link, status, created_at, reminder_sent = app
        
        if status == "Ожидает":
            msg = (
                f"📋 Ваша заявка:\n\n"
                f"👤 Родитель: {parent_name}\n"
                f"🧒 Ученик: {student_name}\n"
                f"🎂 Возраст: {age}\n"
                f"📘 Курс: {course}\n"
                f"📊 Статус: Ожидает назначения даты\n\n"
                f"⏳ Мы скоро свяжемся с вами для назначения занятия!"
            )
            return msg, show_menu, None
        
        elif status == "Назначено":
            formatted_date = lesson_date if isinstance(lesson_date, str) else lesson_date.strftime("%d.%m %H:%M")
            msg = (
                f"�� Ваше занятие:\n\n"
                f"👤 Родитель: {parent_name}\n"
                f"🧒 Ученик: {student_name}\n"
                f"📘 Курс: {course}\n"
                f"📅 Дата: {formatted_date}\n"
                f"🔗 Ссылка: {lesson_link}\n\n"
                f"🎯 Готовьтесь к занятию!"
            )
            
            if show_menu:
                return msg, True, None
            else:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("❌ Отменить занятие", callback_data="cancel_lesson_user"))
                return msg, False, markup
        
        return "❌ Неизвестный статус заявки", show_menu, None

    @bot.message_handler(commands=["my_lesson"])
    @error_handler()
    def handle_my_lesson_command(message):
        # Проверка безопасности
        security_ok, error_msg = check_user_security(message.from_user.id, "my_lesson_command")
        if not security_ok:
            bot.send_message(message.chat.id, f"🚫 {error_msg}")
            return
        
        chat_id = message.chat.id
        msg, show_menu, markup = _handle_my_lesson_logic(chat_id, show_menu=True)
        
        if show_menu:
            bot.send_message(chat_id, msg, reply_markup=menu.get_appropriate_menu(message.from_user.id))
        else:
            bot.send_message(chat_id, msg, reply_markup=markup)
        
        log_user_action(logger, message.from_user.id, "my_lesson_command")

    @bot.message_handler(commands=["help"])
    @error_handler()
    def handle_help(message):
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
        
        bot.send_message(message.chat.id, help_text, parse_mode="HTML", reply_markup=menu.get_appropriate_menu(message.from_user.id))
        log_user_action(logger, message.from_user.id, "help")

    @bot.message_handler(func=lambda m: m.text == "📅 Мое занятие")
    @error_handler()
    def handle_my_lesson(message):
        chat_id = message.chat.id
        
        # Проверка безопасности
        security_ok, error_msg = check_user_security(message.from_user.id, "my_lesson")
        if not security_ok:
            bot.send_message(chat_id, f"🚫 {error_msg}")
            return
        
        msg, show_menu, markup = _handle_my_lesson_logic(chat_id, show_menu=True)
        
        if show_menu:
            bot.send_message(chat_id, msg, reply_markup=menu.get_appropriate_menu(message.from_user.id))
        else:
            bot.send_message(chat_id, msg, reply_markup=markup)
        
        log_user_action(logger, message.from_user.id, "my_lesson")

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
        user_data[chat_id] = {
            "edit_app": True,
            "app_id": app[0],
            "parent_name": parent_name,
            "student_name": student_name,
            "age": age,
            "contact": contact,
            "course": course
        }
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
        
        if chat_id not in user_data or not user_data[chat_id].get("edit_app"):
            bot.send_message(chat_id, "❌ Данные для редактирования не найдены.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            return
        
        user_data[chat_id]["editing_field"] = field
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
        
        if chat_id not in user_data or not user_data[chat_id].get("edit_app"):
            bot.send_message(chat_id, "❌ Данные для редактирования не найдены.", reply_markup=menu.get_appropriate_menu(message.from_user.id))
            return
        
        field = user_data[chat_id].get("editing_field")
        new_value = message.text.strip()
        
        if not new_value:
            bot.send_message(chat_id, "❌ Значение не может быть пустым. Попробуйте снова.", reply_markup=menu.get_appropriate_menu(message.from_user.id))
            return
        
        # Обновляем значение
        user_data[chat_id][field] = new_value
        del user_data[chat_id]["editing_field"]
        
        # Показываем обновленные данные
        app_data = user_data[chat_id]
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
        
        if chat_id not in user_data or not user_data[chat_id].get("edit_app"):
            bot.send_message(chat_id, "❌ Данные для редактирования не найдены.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            return
        
        try:
            app_data = user_data[chat_id]
            update_application(
                app_data["app_id"],
                app_data["parent_name"],
                app_data["student_name"], 
                app_data["age"],
                app_data.get("contact", ""),
                app_data["course"]
            )
            
            # Очищаем данные
            del user_data[chat_id]
            
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
        if chat_id in user_data:
            del user_data[chat_id]
        
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
        user_data[chat_id] = user_data.get(chat_id, {})
        user_data[chat_id]["cancel_app_stage"] = True
        bot.register_next_step_handler(msg, process_cancel_reason)

    def process_cancel_reason(message):
        chat_id = message.chat.id
        # Проверяем, что это сообщение, а не callback
        if hasattr(message, 'text') and message.text == "🔙 Отмена":
            bot.send_message(chat_id, "Отмена отмены заявки.", reply_markup=menu.get_appropriate_menu(message.from_user.id))
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
        
        # Проверка безопасности
        security_ok, error_msg = check_user_security(call.from_user.id, "confirm_cancel_application")
        if not security_ok:
            bot.answer_callback_query(call.id, f"🚫 {error_msg}")
            return
        
        # Проверяем, что заявка все еще существует
        app = get_application_by_tg_id(str(chat_id))
        if not app:
            bot.send_message(chat_id, "❌ Заявка не найдена или уже обработана.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            user_data.pop(chat_id, None)
            return
        
        # Проверяем, что заявка не назначена
        if app[9] == "Назначено":
            bot.send_message(chat_id, "❌ Нельзя отменить назначенную заявку. Обратитесь к администратору.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            user_data.pop(chat_id, None)
            return
        
        reason = user_data.get(chat_id, {}).get("cancel_reason", "")
        
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
            user_data.pop(chat_id, None)
            log_user_action(logger, call.from_user.id, "cancelled_application")
            
        except Exception as e:
            bot.send_message(chat_id, "❌ Ошибка при отмене заявки. Попробуйте позже.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            user_data.pop(chat_id, None)
            log_error(logger, e, f"Error cancelling application for user {chat_id}")

    @bot.callback_query_handler(func=lambda c: c.data == "cancel_cancel_application")
    def handle_cancel_cancel_application(call):
        chat_id = call.message.chat.id
        user_data.pop(chat_id, None)  # Очищаем состояние
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
        user_data[chat_id] = user_data.get(chat_id, {})
        user_data[chat_id]["cancel_lesson_stage"] = True
        bot.register_next_step_handler(msg, process_cancel_lesson_reason)

    def process_cancel_lesson_reason(message):
        chat_id = message.chat.id
        if hasattr(message, 'text') and message.text == "🔙 Отмена":
            bot.send_message(chat_id, "Отмена отмены урока.", reply_markup=menu.get_appropriate_menu(message.from_user.id))
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
        
        # Проверка безопасности
        security_ok, error_msg = check_user_security(call.from_user.id, "confirm_cancel_lesson_user")
        if not security_ok:
            bot.answer_callback_query(call.id, f"🚫 {error_msg}")
            return
        
        # Проверяем, что заявка все еще существует
        app = get_application_by_tg_id(str(chat_id))
        if not app:
            bot.send_message(chat_id, "❌ Заявка не найдена или уже обработана.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            user_data.pop(chat_id, None)
            return
        
        # Проверяем, что заявка назначена
        if app[9] != "Назначено":
            bot.send_message(chat_id, "❌ Нельзя отменить неназначенный урок.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            user_data.pop(chat_id, None)
            return
        
        reason = user_data.get(chat_id, {}).get("cancel_lesson_reason", "")
        
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
            user_data.pop(chat_id, None)
            log_user_action(logger, call.from_user.id, "cancelled_lesson")
            
        except Exception as e:
            bot.send_message(chat_id, "❌ Ошибка при отмене урока. Попробуйте позже.", reply_markup=menu.get_appropriate_menu(call.from_user.id))
            user_data.pop(chat_id, None)
            log_error(logger, e, f"Error cancelling lesson for user {chat_id}")

    @bot.callback_query_handler(func=lambda c: c.data == "cancel_cancel_lesson_user")
    def handle_cancel_cancel_lesson_user(call):
        chat_id = call.message.chat.id
        user_data.pop(chat_id, None)  # Очищаем состояние
        bot.send_message(chat_id, "Отмена отмены урока.", reply_markup=menu.get_appropriate_menu(call.from_user.id))

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
            bot.send_message(chat_id, msg, reply_markup=menu.get_appropriate_menu(message.from_user.id))
            return
        last_time = get_last_contact_time(str(chat_id))
        if last_time:
            last_dt = datetime.datetime.fromisoformat(last_time)
            if (datetime.datetime.now() - last_dt).total_seconds() < 20*60:
                bot.send_message(chat_id, "⏳ Вы можете отправлять обращения не чаще, чем раз в 20 минут.", reply_markup=menu.get_appropriate_menu(message.from_user.id))
                return
        bot.send_message(chat_id, "✍️ Опишите ваш вопрос или прикрепите файл (фото, документ, голосовое, видео).\n\nДля отмены нажмите '🔙 Отмена'.", reply_markup=menu.get_cancel_button())
        user_data[chat_id] = {"contact_fsm": True}
        bot.register_next_step_handler(message, process_contact_message)

    def process_contact_message(message):
        from data.db import add_contact
        chat_id = message.chat.id
        user = message.from_user
        if hasattr(message, 'text') and message.text == "🔙 Отмена":
            bot.send_message(chat_id, "Обращение отменено.", reply_markup=menu.get_appropriate_menu(message.from_user.id))
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
        bot.send_message(chat_id, "✅ Ваше обращение отправлено админу. Ожидайте ответа.", reply_markup=menu.get_appropriate_menu(message.from_user.id))
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

def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)
