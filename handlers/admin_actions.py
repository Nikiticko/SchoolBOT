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
from state.state_manager import state_manager
from config import ADMIN_ID
import utils.menu as menu
from utils.menu import is_admin

# Глобальная переменная для функции отправки отзывов
send_review_request_func = None

# Глобальные буферы для обработки отмен и завершений
cancel_reasons_buffer = {}
finish_feedback_buffer = {}

def set_review_request_function(func):
    """Устанавливает функцию для отправки запросов на отзывы"""
    global send_review_request_func
    send_review_request_func = func

def register_admin_actions(bot, logger):

    @bot.message_handler(func=lambda m: m.text == "📝 Управление уроками" and is_admin(m.from_user.id))
    def handle_lesson_management(message):
        try:
            markup = menu.get_lesson_management_menu()
            bot.send_message(message.chat.id, "📝 Выберите действие для управления уроками:", reply_markup=markup)
            logger.info(f"Admin {message.from_user.id} opened lesson management menu")
        except Exception as e:
            logger.error(f"Error in handle_lesson_management: {e}")

    @bot.message_handler(func=lambda m: m.text == "🔙 Назад в админ-меню" and is_admin(m.from_user.id))
    def handle_back_to_main_menu(message):
        try:
            markup = menu.get_admin_menu()
            bot.send_message(message.chat.id, "🔙 Возврат в главное меню администратора", reply_markup=markup)
            logger.info(f"Admin {message.from_user.id} returned to main menu")
        except Exception as e:
            logger.error(f"Error in handle_back_to_main_menu: {e}")

    @bot.message_handler(func=lambda m: m.text == "📅 Посмотреть запланированные уроки" and is_admin(m.from_user.id))
    def handle_view_scheduled_lessons(message):
        try:
            apps = get_assigned_applications()
            if not apps:
                bot.send_message(message.chat.id, "✅ Нет запланированных уроков")
                return

            bot.send_message(message.chat.id, f"📅 Запланированные уроки ({len(apps)}):")
            
            for app in apps:
                app_id, tg_id, parent_name, student_name, age, contact, course, date, link, status, created_at, reminder_sent = app
                formatted_date = format_date_for_display(date)
                formatted_created = format_date_for_display(created_at)
                
                text = (
                    f"🆔 Заявка #{app_id}\n"
                    f"👤 Родитель: {parent_name}\n"
                    f"🧒 Ученик: {student_name} ({age} лет)\n"
                    f"📞 Контакт: {contact or 'не указан'}\n"
                    f"📘 Курс: {course}\n"
                    f"📅 Дата урока: {formatted_date}\n"
                    f"🔗 Ссылка: {link or 'не указана'}\n"
                    f"📝 Создано: {formatted_created}\n"
                    f"🔔 Напоминание: {'✅ Отправлено' if reminder_sent else '❌ Не отправлено'}"
                )
                bot.send_message(message.chat.id, text)
            
            logger.info(f"Admin {message.from_user.id} viewed {len(apps)} scheduled lessons")
        except Exception as e:
            logger.error(f"Error in handle_view_scheduled_lessons: {e}")

    @bot.message_handler(func=lambda m: m.text == "✅ Завершить заявку" and is_admin(m.from_user.id))
    def handle_lesson_finish_menu(message):
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
            logger.error(f"Error in handle_lesson_finish_menu: {e}")

    @bot.message_handler(func=lambda m: m.text == "❌ Отменить заявку" and is_admin(m.from_user.id))
    def handle_lesson_cancel_menu(message):
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
            logger.error(f"Error in handle_lesson_cancel_menu: {e}")

    @bot.message_handler(func=lambda m: m.text == "🚫 Отменить урок" and is_admin(m.from_user.id))
    def handle_lesson_cancel_lesson_menu(message):
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
            logger.error(f"Error in handle_lesson_cancel_lesson_menu: {e}")

    @bot.message_handler(func=lambda m: m.text == "🕓 Перенести урок" and is_admin(m.from_user.id))
    def handle_lesson_reschedule_menu(message):
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
            logger.error(f"Error in handle_lesson_reschedule_menu: {e}")

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
            # Проверяем только по статусу
            if app[9] != "Назначено":
                bot.send_message(chat_id, "❌ Завершить можно только заявку в статусе 'Назначено'.")
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
            # Проверяем только по статусу
            if app[9] != "Ожидает":
                bot.send_message(chat_id, "❌ Отменить можно только заявку в статусе 'Ожидает'.")
                return

            success = archive_application(app_id, cancelled_by="admin", comment=reason, archived_status="Заявка отменена")

            if success:
                bot.edit_message_text("✅ Заявка отменена и архивирована.", chat_id, msg_id)
                bot.send_message(chat_id, "✅ Заявка отменена.", reply_markup=menu.get_admin_menu())
                # Уведомление пользователю
                tg_id = app[1]
                try:
                    bot.send_message(int(tg_id), f"⚠️ Ваша заявка была отменена администратором.\nПричина: {reason}\nВы можете подать новую заявку, если хотите.")
                    logger.info(f"Notification sent to user {tg_id} about application cancellation by admin")
                except Exception as e:
                    logger.error(f"Failed to notify user {tg_id} about application cancellation: {e}")
                logger.info(f"Admin {user_id} cancelled application {app_id} with reason: {reason}")
            else:
                bot.send_message(chat_id, "❌ Не удалось архивировать заявку. Попробуйте позже.")
                logger.error(f"Failed to archive application {app_id} (cancel) for user {user_id}")
        except Exception as e:
            logger.error(f"Error in receive_cancel_reason: {e}")

    lesson_cancel_buffer = {}  # Временно храним app_id для отмены урока

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
            # Проверяем только по статусу
            if app[9] != "Назначено":
                bot.send_message(chat_id, "❌ Отменить урок можно только для заявки в статусе 'Назначено'.")
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

    @bot.callback_query_handler(func=lambda c: c.data.startswith("reschedule:"))
    def handle_reschedule_callback(call):
        app_id = int(call.data.split(":")[1])
        state_manager.add_writing_id(call.from_user.id)
        bot.send_message(call.message.chat.id, f"🕓 Введите новую дату и время для заявки #{app_id} (например: 22.06 17:30):", reply_markup=menu.get_cancel_button())
        bot.register_next_step_handler(call.message, lambda m: get_new_date(m, app_id))

    def get_new_date(message, app_id):
        if not state_manager.is_writing_id(message.from_user.id):
            return
        
        # Проверяем отмену
        if message.text == "🔙 Отмена":
            state_manager.remove_writing_id(message.from_user.id)
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
        if not state_manager.is_writing_id(message.from_user.id):
            return
        
        # Проверяем отмену
        if message.text == "🔙 Отмена":
            state_manager.remove_writing_id(message.from_user.id)
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

        state_manager.remove_writing_id(message.from_user.id)
        logger.info(f"Admin {message.from_user.id} rescheduled lesson for application {app_id}")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("assign:"))
    def handle_assign_lesson(call):
        try:
            app_id = int(call.data.split(":")[1])
            app = get_application_by_id(app_id)
            if not app:
                bot.answer_callback_query(call.id, "Заявка не найдена")
                return
            chat_id = call.message.chat.id
            msg = (
                f"🕒 Назначение урока для заявки #{app_id}\n"
                f"👤 Родитель: {app[2]}\n"
                f"🧒 Ученик: {app[3]}\n"
                f"📘 Курс: {app[6]}\n\n"
                f"Введите дату и время урока в формате: 22.06 17:30"
            )
            # Сохраняем app_id в user_data для последующего шага
            from state.users import user_data
            user_data[chat_id] = {"assign_app_id": app_id}
            bot.send_message(chat_id, msg, reply_markup=menu.get_cancel_button())
            bot.register_next_step_handler(call.message, process_assign_date)
            logger.info(f"Admin {call.from_user.id} started assigning lesson for application {app_id}")
        except Exception as e:
            logger.error(f"Error in handle_assign_lesson: {e}")

    def process_assign_date(message):
        from state.users import user_data
        chat_id = message.chat.id
        app_id = user_data.get(chat_id, {}).get("assign_app_id")
        if not app_id:
            bot.send_message(chat_id, "❌ Не найдена заявка для назначения.")
            return
        
        # Проверяем отмену
        if message.text == "🔙 Отмена":
            user_data.pop(chat_id, None)
            menu.handle_cancel_action(bot, message, "урок", logger)
            return
        
        date_text = message.text.strip()
        # Валидация даты - ИСПРАВЛЕНО
        is_valid, result = validate_date_format(date_text)
        if not is_valid:
            bot.send_message(chat_id, f"❌ {result}\n\n📅 Попробуйте еще раз в формате ДД.ММ ЧЧ:ММ (например: 22.06 17:30):", reply_markup=menu.get_cancel_button())
            bot.register_next_step_handler(message, process_assign_date)
            return
        user_data[chat_id]["assign_date"] = date_text
        bot.send_message(chat_id, "Введите ссылку на урок (или - если нет):", reply_markup=menu.get_cancel_button())
        bot.register_next_step_handler(message, process_assign_link)

    def process_assign_link(message):
        from state.users import user_data
        chat_id = message.chat.id
        app_id = user_data.get(chat_id, {}).get("assign_app_id")
        date_text = user_data.get(chat_id, {}).get("assign_date")
        if not app_id or not date_text:
            bot.send_message(chat_id, "❌ Не найдена заявка или дата для назначения.")
            return
        
        # Проверяем отмену
        if message.text == "🔙 Отмена":
            user_data.pop(chat_id, None)
            menu.handle_cancel_action(bot, message, "урок", logger)
            return
        
        link = message.text.strip()
        try:
            update_application_lesson(app_id, date_text, link)
            bot.send_message(chat_id, f"✅ Урок назначен!\nДата: {date_text}\nСсылка: {link}", reply_markup=menu.get_admin_menu())
            # Уведомляем пользователя
            app = get_application_by_id(app_id)
            if app:
                tg_id = app[1]
                parent_name = app[2]
                student_name = app[3]
                course = app[6]
                bot.send_message(
                    int(tg_id),
                    f"✅ Ваш урок назначен!\n\nКурс: {course}\nУченик: {student_name}\nДата: {date_text}\nСсылка: {link}"
                )
            user_data.pop(chat_id, None)
            logger.info(f"Admin {message.from_user.id} assigned lesson for application {app_id}")
        except Exception as e:
            bot.send_message(chat_id, "❌ Ошибка при назначении урока. Попробуйте позже.")
            logger.error(f"Error in process_assign_link: {e}")

