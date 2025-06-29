from telebot import types
from data.db import (
    get_assigned_applications,
    get_pending_applications,
    update_application_lesson,
    get_application_by_id,
    archive_application,
    format_date_for_display,
    validate_date_format
)
from state.users import writing_ids
from handlers.admin import is_admin
import utils.menu as menu
cancel_reasons_buffer = {}
finish_feedback_buffer = {}

# Глобальная переменная для функции отправки отзывов
send_review_request_func = None

def set_review_request_function(func):
    """Устанавливает функцию для отправки запросов на отзывы"""
    global send_review_request_func
    send_review_request_func = func

def register_admin_actions(bot, logger):

    @bot.message_handler(func=lambda m: m.text == "✅ Завершить заявку" and is_admin(m.from_user.id))
    def handle_finish_request(message):
        try:
            apps = get_assigned_applications()
            if not apps:
                bot.send_message(message.chat.id, "✅ Нет заявок со статусом 'Назначено'")
                return

            for app in apps:
                app_id, _, parent_name, student_name, _, _, course, date, link, _, _, reminder_sent = app
                formatted_date = format_date_for_display(date)
                text = (
                    f"🆔 Заявка #{app_id}\n"
                    f"👤 Родитель: {parent_name}\n"
                    f"🧒 Ученик: {student_name}\n"
                    f"📘 Курс: {course}\n"
                    f"📅 Дата: {formatted_date}\n"
                    f"🔗 Ссылка: {link}"
                )
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("✅ Завершить", callback_data=f"finish:{app_id}"))
                bot.send_message(message.chat.id, text, reply_markup=markup)
            logger.info(f"Admin {message.from_user.id} viewed applications to finish")
        except Exception as e:
            logger.error(f"Error in handle_finish_request: {e}")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("finish:"))
    def handle_finish_status(call):
        try:
            app_id = int(call.data.split(":")[1])
            finish_feedback_buffer[call.from_user.id] = {
                "app_id": app_id,
                "chat_id": call.message.chat.id,
                "msg_id": call.message.message_id
            }
            bot.send_message(call.message.chat.id, "📝 Введите обратную связь по уроку (обязательно):", reply_markup=menu.get_cancel_button())
            bot.register_next_step_handler(call.message, receive_finish_feedback)
            logger.info(f"Admin {call.from_user.id} started finishing application {app_id}")
        except Exception as e:
            logger.error(f"Error in handle_finish_status: {e}")

    def receive_finish_feedback(message):
        try:
            # Проверяем отмену
            if message.text == "🔙 Отмена":
                if message.from_user.id in finish_feedback_buffer:
                    finish_feedback_buffer.pop(message.from_user.id)
                menu.handle_cancel_action(bot, message, "урок", logger)
                return

            user_id = message.from_user.id
            if user_id not in finish_feedback_buffer:
                return

            comment = message.text.strip()
            if not comment:
                bot.send_message(message.chat.id, "❗️ Обратная связь обязательна. Пожалуйста, введите комментарий:")
                bot.register_next_step_handler(message, receive_finish_feedback)
                return

            info = finish_feedback_buffer.pop(user_id)
            app_id = info["app_id"]
            chat_id = info["chat_id"]
            msg_id = info["msg_id"]

            # Получаем данные заявки ДО архивирования
            app = get_application_by_id(app_id)
            if not app:
                bot.send_message(chat_id, "⚠️ Ошибка: заявка не найдена.")
                return

            success = archive_application(app_id, cancelled_by="admin", comment=comment, archived_status="Завершено")

            if success:
                bot.edit_message_text("✅ Заявка завершена и архивирована.", chat_id, msg_id)
                bot.send_message(chat_id, "✅ Обратная связь сохранена и заявка завершена.", reply_markup=menu.get_admin_menu())

                # Отправляем уведомление пользователю
                tg_id = app[1]
                parent_name = app[2]
                student_name = app[3]
                course = app[6]
                lesson_date = format_date_for_display(app[7])
                try:
                    bot.send_message(
                        int(tg_id),
                        f"✅ Ваш урок по курсу '{course}' для ученика {student_name} ({parent_name}) на {lesson_date} прошёл успешно!\n\nОбратная связь: {comment}"
                    )
                    logger.info(f"Notification sent to user {tg_id} about lesson completion")
                    
                    # Отправляем запрос на отзыв через 30 секунд
                    if send_review_request_func:
                        try:
                            send_review_request_func(bot, tg_id, app_id, course)
                            logger.info(f"Review request scheduled for user {tg_id} for application {app_id}")
                        except Exception as e:
                            logger.error(f"Failed to schedule review request for user {tg_id}: {e}")
                    
                except Exception as e:
                    logger.error(f"Failed to notify user {tg_id} about lesson completion: {e}")

                logger.info(f"Admin {user_id} finished application {app_id} with feedback: {comment}")
            else:
                bot.send_message(chat_id, "❌ Не удалось архивировать заявку. Попробуйте позже.")
                logger.error(f"Failed to archive application {app_id} (finish) for user {user_id}")
        except Exception as e:
            logger.error(f"Error in receive_finish_feedback: {e}")

    @bot.message_handler(func=lambda m: m.text == "❌ Отменить заявку" and is_admin(m.from_user.id))
    def handle_cancel_request(message):
        try:
            apps = get_pending_applications()
            if not apps:
                bot.send_message(message.chat.id, "✅ Нет активных заявок")
                return

            for app in apps:
                app_id, _, parent_name, student_name, _, _, course, _, _, _, _, reminder_sent = app
                text = (
                    f"🆔 Заявка #{app_id}\n"
                    f"👤 Родитель: {parent_name}\n"
                    f"🧒 Ученик: {student_name}\n"
                    f"📘 Курс: {course}"
                )
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("❌ Отменить", callback_data=f"cancel:{app_id}"))
                bot.send_message(message.chat.id, text, reply_markup=markup)
            logger.info(f"Admin {message.from_user.id} viewed applications to cancel")
        except Exception as e:
            logger.error(f"Error in handle_cancel_request: {e}")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("cancel:"))
    def handle_cancel_status(call):
        try:
            app_id = int(call.data.split(":")[1])
            cancel_reasons_buffer[call.from_user.id] = {
                "app_id": app_id,
                "chat_id": call.message.chat.id,
                "msg_id": call.message.message_id
            }
            bot.send_message(call.message.chat.id, "❓ Укажите причину отмены заявки:", reply_markup=menu.get_cancel_button())
            bot.register_next_step_handler(call.message, receive_cancel_reason)
            logger.info(f"Admin {call.from_user.id} started canceling application {app_id}")
        except Exception as e:
            logger.error(f"Error in handle_cancel_status: {e}")

    def receive_cancel_reason(message):
        try:
            # Проверяем отмену
            if message.text == "🔙 Отмена":
                if message.from_user.id in cancel_reasons_buffer:
                    cancel_reasons_buffer.pop(message.from_user.id)
                menu.handle_cancel_action(bot, message, "отмена_заявки", logger)
                return
                
            user_id = message.from_user.id
            if user_id not in cancel_reasons_buffer:
                return
                
            reason = message.text.strip()
            info = cancel_reasons_buffer.pop(user_id)

            app_id = info["app_id"]
            chat_id = info["chat_id"]
            msg_id = info["msg_id"]

            # Получаем данные заявки ДО архивирования
            app = get_application_by_id(app_id)
            if not app:
                bot.send_message(chat_id, "⚠️ Ошибка: заявка не найдена.")
                return

            success = archive_application(app_id, cancelled_by="admin", comment=reason, archived_status="Заявка отменена")

            if success:
                bot.edit_message_text("✅ Заявка отменена и архивирована.", chat_id, msg_id)
                bot.send_message(chat_id, "✅ Заявка отменена.", reply_markup=menu.get_admin_menu())
                logger.info(f"Admin {user_id} cancelled application {app_id} with reason: {reason}")
            else:
                bot.send_message(chat_id, "❌ Не удалось архивировать заявку. Попробуйте позже.")
                logger.error(f"Failed to archive application {app_id} (cancel) for user {user_id}")
        except Exception as e:
            logger.error(f"Error in receive_cancel_reason: {e}")

    lesson_cancel_buffer = {}  # Временно храним app_id для отмены урока

    @bot.message_handler(func=lambda m: m.text == "🚫 Отменить урок" and is_admin(m.from_user.id))
    def handle_cancel_lesson_request(message):
        try:
            apps = get_assigned_applications()
            if not apps:
                bot.send_message(message.chat.id, "✅ Нет назначенных уроков")
                return

            for app in apps:
                app_id, tg_id, parent_name, student_name, _, _, course, date, link, _, _, reminder_sent = app
                formatted_date = format_date_for_display(date)
                text = (
                    f"🆔 Заявка #{app_id}\n"
                    f"👤 Родитель: {parent_name}\n"
                    f"🧒 Ученик: {student_name}\n"
                    f"📘 Курс: {course}\n"
                    f"📅 Дата: {formatted_date}\n"
                    f"🔗 Ссылка: {link}"
                )
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🚫 Отменить урок", callback_data=f"cancel_lesson:{app_id}"))
                bot.send_message(message.chat.id, text, reply_markup=markup)
            logger.info(f"Admin {message.from_user.id} viewed lessons to cancel")
        except Exception as e:
            logger.error(f"Error in handle_cancel_lesson_request: {e}")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("cancel_lesson:"))
    def handle_cancel_lesson(call):
        try:
            app_id = int(call.data.split(":")[1])
            lesson_cancel_buffer[call.from_user.id] = {
                "app_id": app_id,
                "chat_id": call.message.chat.id,
                "msg_id": call.message.message_id
            }
            bot.send_message(call.message.chat.id, "❓ Укажите причину отмены урока:", reply_markup=menu.get_cancel_button())
            bot.register_next_step_handler(call.message, receive_lesson_cancel_reason)
            logger.info(f"Admin {call.from_user.id} started canceling lesson for application {app_id}")
        except Exception as e:
            logger.error(f"Error in handle_cancel_lesson: {e}")

    def receive_lesson_cancel_reason(message):
        try:
            # Проверяем отмену
            if message.text == "🔙 Отмена":
                if message.from_user.id in lesson_cancel_buffer:
                    lesson_cancel_buffer.pop(message.from_user.id)
                menu.handle_cancel_action(bot, message, "урок", logger)
                return
                
            user_id = message.from_user.id
            if user_id not in lesson_cancel_buffer:
                return
                
            reason = message.text.strip()
            info = lesson_cancel_buffer.pop(user_id)

            app_id = info["app_id"]
            chat_id = info["chat_id"]
            msg_id = info["msg_id"]

            # Получаем данные заявки ДО архивирования
            app = get_application_by_id(app_id)
            if not app:
                bot.send_message(chat_id, "⚠️ Ошибка: заявка не найдена.")
                return

            success = archive_application(app_id, cancelled_by="admin", comment=reason, archived_status="Урок отменён")

            if success:
                bot.edit_message_text("🚫 Урок отменён и заявка архивирована.", chat_id, msg_id)
                bot.send_message(chat_id, "✅ Причина отмены урока сохранена.", reply_markup=menu.get_admin_menu())

                # Отправляем уведомление пользователю
                tg_id = app[1]
                try:
                    bot.send_message(int(tg_id), f"⚠️ Ваш урок был отменён.\nПричина: {reason}\nВы можете записаться снова.")
                    logger.info(f"Notification sent to user {tg_id} about lesson cancellation")
                except Exception as e:
                    logger.error(f"Failed to notify user {tg_id}: {e}")
                
                logger.info(f"Admin {user_id} cancelled lesson for application {app_id} with reason: {reason}")
            else:
                bot.send_message(chat_id, "⚠️ Ошибка: заявка не найдена.")
        except Exception as e:
            logger.error(f"Error in receive_lesson_cancel_reason: {e}")

    @bot.message_handler(func=lambda m: m.text == "🕓 Перенести урок" and is_admin(m.from_user.id))
    def handle_reschedule_lesson(message):
        try:
            apps = get_assigned_applications()
            if not apps:
                bot.send_message(message.chat.id, "✅ Нет назначенных уроков")
                return

            for app in apps:
                app_id, tg_id, parent_name, student_name, _, _, course, date, link, _, _, reminder_sent = app
                formatted_date = format_date_for_display(date)
                text = (
                    f"🆔 Заявка #{app_id}\n"
                    f"👤 Родитель: {parent_name}\n"
                    f"🧒 Ученик: {student_name}\n"
                    f"📘 Курс: {course}\n"
                    f"📅 Текущая дата: {formatted_date}\n"
                    f"🔗 Ссылка: {link}"
                )
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🕓 Перенести", callback_data=f"reschedule:{app_id}"))
                bot.send_message(message.chat.id, text, reply_markup=markup)
            logger.info(f"Admin {message.from_user.id} viewed applications to reschedule")
        except Exception as e:
            logger.error(f"Error in handle_reschedule_lesson: {e}")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("reschedule:"))
    def handle_reschedule_callback(call):
        app_id = int(call.data.split(":")[1])
        writing_ids.add(call.from_user.id)
        bot.send_message(call.message.chat.id, f"🕓 Введите новую дату и время для заявки #{app_id} (например: 22.06 17:30):", reply_markup=menu.get_cancel_button())
        bot.register_next_step_handler(call.message, lambda m: get_new_date(m, app_id))

    def get_new_date(message, app_id):
        if message.from_user.id not in writing_ids:
            return
        
        # Проверяем отмену
        if message.text == "🔙 Отмена":
            writing_ids.discard(message.from_user.id)
            menu.handle_cancel_action(bot, message, "урок", logger)
            return
        
        date_text = message.text.strip()
        
        # Валидируем дату
        is_valid, result = validate_date_format(date_text)
        
        if not is_valid:
            bot.send_message(
                message.chat.id, 
                f"❌ {result}\n\n📅 Попробуйте еще раз в формате ДД.ММ ЧЧ:ММ (например: 22.06 17:30):",
                reply_markup=menu.get_cancel_button()
            )
            bot.register_next_step_handler(message, lambda m: get_new_date(m, app_id))
            return
        
        # Сохраняем валидную дату
        user_data = getattr(message, '_user_data', {})
        user_data['valid_date'] = result
        message._user_data = user_data
        
        bot.send_message(message.chat.id, "🔗 Введите новую ссылку на урок:", reply_markup=menu.get_cancel_button())
        bot.register_next_step_handler(message, lambda m: apply_reschedule(m, app_id, date_text))

    def apply_reschedule(message, app_id, date_text):
        if message.from_user.id not in writing_ids:
            return
        
        # Проверяем отмену
        if message.text == "🔙 Отмена":
            writing_ids.discard(message.from_user.id)
            menu.handle_cancel_action(bot, message, "урок", logger)
            return
        
        link = message.text.strip()
        
        # Получаем валидированную дату
        user_data = getattr(message, '_user_data', {})
        valid_date = user_data.get('valid_date')
        
        if valid_date:
            # Используем валидированную дату (datetime объект)
            update_application_lesson(app_id, valid_date, link)
            formatted_date = format_date_for_display(valid_date)
        else:
            # Fallback - используем строку и надеемся на лучшее
            update_application_lesson(app_id, date_text, link)
            formatted_date = date_text
        
        bot.send_message(message.chat.id, f"✅ Урок перенесён на:\n📅 {formatted_date}\n🔗 {link}", reply_markup=menu.get_admin_menu())

        app = get_application_by_id(app_id)
        if app:
            tg_id = app[1]
            course = app[6]
            try:
                bot.send_message(
                    int(tg_id),
                    f"🔄 Ваш урок был перенесён!\n📘 Курс: {course}\n🗓 Новая дата: {formatted_date}\n🔗 Ссылка: {link}"
                )
                logger.info(f"Reschedule notification sent to user {tg_id}")
            except Exception as e:
                logger.error(f"Failed to notify user {tg_id} about reschedule: {e}")

        writing_ids.discard(message.from_user.id)
        logger.info(f"Admin {message.from_user.id} rescheduled lesson for application {app_id}")

