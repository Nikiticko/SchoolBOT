from telebot import types
from data.db import (
    get_assigned_applications,
    get_pending_applications,
    update_application_status,
    cancel_assigned_lesson,
    update_application_lesson,
    get_application_by_id,
    archive_application,
    format_date_for_display,
    validate_date_format
)
from state.users import writing_ids
from handlers.admin import is_admin
cancel_reasons_buffer = {}


def register_admin_actions(bot):

    @bot.message_handler(func=lambda m: m.text == "✅ Завершить заявку" and is_admin(m.from_user.id))
    def handle_finish_request(message):
        apps = get_assigned_applications()
        if not apps:
            bot.send_message(message.chat.id, "✅ Нет заявок со статусом 'Назначено'")
            return

        for app in apps:
            app_id, _, parent_name, student_name, _, _, course, date, link, _, _ = app
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

    @bot.callback_query_handler(func=lambda c: c.data.startswith("finish:"))
    def handle_finish_status(call):
        app_id = int(call.data.split(":")[1])
        update_application_status(app_id, "Завершено")
        bot.edit_message_text("✅ Заявка завершена.", call.message.chat.id, call.message.message_id)

    @bot.message_handler(func=lambda m: m.text == "❌ Отменить заявку" and is_admin(m.from_user.id))
    def handle_cancel_request(message):
        apps = get_pending_applications()
        if not apps:
            bot.send_message(message.chat.id, "✅ Нет активных заявок")
            return

        for app in apps:
            app_id, _, parent_name, student_name, _, _, course, _, _, _, _ = app
            text = (
                f"🆔 Заявка #{app_id}\n"
                f"👤 Родитель: {parent_name}\n"
                f"🧒 Ученик: {student_name}\n"
                f"📘 Курс: {course}"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("❌ Отменить", callback_data=f"cancel:{app_id}"))
            bot.send_message(message.chat.id, text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("cancel:"))
    def handle_cancel_status(call):
        app_id = int(call.data.split(":")[1])
        cancel_reasons_buffer[call.from_user.id] = {
            "app_id": app_id,
            "chat_id": call.message.chat.id,
            "msg_id": call.message.message_id
        }
        bot.send_message(call.message.chat.id, "❓ Укажите причину отмены заявки:")

    @bot.message_handler(func=lambda m: m.from_user.id in cancel_reasons_buffer)
    def receive_cancel_reason(message):
        user_id = message.from_user.id
        reason = message.text.strip()
        info = cancel_reasons_buffer.pop(user_id)

        app_id = info["app_id"]
        chat_id = info["chat_id"]
        msg_id = info["msg_id"]

        try:
            # Получаем данные заявки ДО архивирования
            app = get_application_by_id(app_id)
            if not app:
                bot.send_message(chat_id, "⚠️ Ошибка: заявка не найдена.")
                return

            success = archive_application(app_id, cancelled_by="admin", cancel_reason=reason, archived_status="Заявка отменена")

            if success:
                bot.edit_message_text("❌ Заявка отменена и архивирована.", chat_id, msg_id)
                bot.send_message(chat_id, "✅ Причина отмены заявки сохранена.")

                # Отправляем уведомление пользователю
                tg_id = app[1]
                try:
                    bot.send_message(int(tg_id), "⚠️ Ваша заявка была отменена. Вы можете подать новую заявку.")
                    print(f"[INFO] Уведомление отправлено: {tg_id}")
                except Exception as e:
                    print(f"[❗] Не удалось уведомить пользователя {tg_id}: {e}")
            else:
                bot.send_message(chat_id, "⚠️ Ошибка: заявка не найдена.")
        except Exception as e:
            bot.send_message(chat_id, f"⚠️ Ошибка при отмене заявки: {e}")

    lesson_cancel_buffer = {}  # Временно храним app_id для отмены урока


    @bot.message_handler(func=lambda m: m.text == "🚫 Отменить урок" and is_admin(m.from_user.id))
    def handle_cancel_lesson_request(message):
        apps = get_assigned_applications()
        if not apps:
            bot.send_message(message.chat.id, "✅ Нет назначенных уроков")
            return

        for app in apps:
            app_id, tg_id, parent_name, student_name, _, _, course, date, link, _, _ = app
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


    @bot.callback_query_handler(func=lambda c: c.data.startswith("cancel_lesson:"))
    def handle_cancel_lesson(call):
        print(f"[DEBUG] cancel_lesson нажата: {call.data}")
        try:
            app_id = int(call.data.split(":")[1])
            lesson_cancel_buffer[call.from_user.id] = {
                "app_id": app_id,
                "chat_id": call.message.chat.id,
                "msg_id": call.message.message_id
            }
            bot.send_message(call.message.chat.id, "❓ Укажите причину отмены урока:")
        except Exception as e:
            print(f"[❌] Ошибка в handle_cancel_lesson: {e}")


    @bot.message_handler(func=lambda m: m.from_user.id in lesson_cancel_buffer)
    def receive_lesson_cancel_reason(message):
        user_id = message.from_user.id
        reason = message.text.strip()
        info = lesson_cancel_buffer.pop(user_id)

        app_id = info["app_id"]
        chat_id = info["chat_id"]
        msg_id = info["msg_id"]

        try:
            # Получаем данные заявки ДО архивирования
            app = get_application_by_id(app_id)
            if not app:
                bot.send_message(chat_id, "⚠️ Ошибка: заявка не найдена.")
                return

            success = archive_application(app_id, cancelled_by="admin", cancel_reason=reason, archived_status="Урок отменён")

            if success:
                bot.edit_message_text("🚫 Урок отменён и заявка архивирована.", chat_id, msg_id)
                bot.send_message(chat_id, "✅ Причина отмены урока сохранена.")

                # Отправляем уведомление пользователю
                tg_id = app[1]
                try:
                    bot.send_message(int(tg_id), "⚠️ Ваш урок был отменён. Вы можете записаться снова.")
                    print(f"[INFO] Уведомление отправлено: {tg_id}")
                except Exception as e:
                    print(f"[❗] Не удалось уведомить ученика {tg_id}: {e}")
            else:
                bot.send_message(chat_id, "⚠️ Ошибка: заявка не найдена.")
        except Exception as e:
            bot.send_message(chat_id, f"⚠️ Ошибка при отмене урока: {e}")


     

    @bot.message_handler(func=lambda m: m.text == "🕓 Перенести урок" and is_admin(m.from_user.id))
    def handle_reschedule_lesson(message):
        apps = get_assigned_applications()
        if not apps:
            bot.send_message(message.chat.id, "✅ Нет назначенных уроков")
            return

        for app in apps:
            app_id, tg_id, parent_name, student_name, _, _, course, date, link, _, _ = app
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

    @bot.callback_query_handler(func=lambda c: c.data.startswith("reschedule:"))
    def handle_reschedule_callback(call):
        app_id = int(call.data.split(":")[1])
        writing_ids.add(call.from_user.id)
        bot.send_message(call.message.chat.id, f"🕓 Введите новую дату и время для заявки #{app_id} (например: 22.06 17:30):")
        bot.register_next_step_handler(call.message, lambda m: get_new_date(m, app_id))

    def get_new_date(message, app_id):
        if message.from_user.id not in writing_ids:
            return
        
        date_text = message.text.strip()
        
        # Валидируем дату
        is_valid, result = validate_date_format(date_text)
        
        if not is_valid:
            bot.send_message(
                message.chat.id, 
                f"❌ {result}\n\n📅 Попробуйте еще раз в формате ДД.ММ ЧЧ:ММ (например: 22.06 17:30):"
            )
            bot.register_next_step_handler(message, lambda m: get_new_date(m, app_id))
            return
        
        # Сохраняем валидную дату
        user_data = getattr(message, '_user_data', {})
        user_data['valid_date'] = result
        message._user_data = user_data
        
        bot.send_message(message.chat.id, "🔗 Введите новую ссылку на урок:")
        bot.register_next_step_handler(message, lambda m: apply_reschedule(m, app_id, date_text))

    def apply_reschedule(message, app_id, date_text):
        if message.from_user.id not in writing_ids:
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
        
        bot.send_message(message.chat.id, f"✅ Урок перенесён на:\n📅 {formatted_date}\n🔗 {link}")

        app = get_application_by_id(app_id)
        if app:
            tg_id = app[1]
            course = app[6]
            try:
                bot.send_message(
                    int(tg_id),
                    f"🔄 Ваш урок был перенесён!\n📘 Курс: {course}\n🗓 Новая дата: {formatted_date}\n🔗 Ссылка: {link}"
                )
            except Exception as e:
                print(f"[❗] Не удалось уведомить ученика {tg_id}: {e}")

        writing_ids.discard(message.from_user.id)

