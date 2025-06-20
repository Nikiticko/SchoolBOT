from telebot import types
from data.db import (
    get_assigned_applications,
    get_pending_applications,
    update_application_status,
    cancel_assigned_lesson,
    update_application_lesson,
    get_application_by_id
)
from state.users import writing_ids
from handlers.admin import is_admin

def register_admin_actions(bot):

    @bot.message_handler(func=lambda m: m.text == "✅ Завершить заявку" and is_admin(m.from_user.id))
    def handle_finish_request(message):
        apps = get_assigned_applications()
        if not apps:
            bot.send_message(message.chat.id, "✅ Нет заявок со статусом 'Назначено'")
            return

        for app in apps:
            app_id, _, parent_name, student_name, _, _, course, date, link, _, _ = app
            text = (
                f"🆔 Заявка #{app_id}\n"
                f"👤 Родитель: {parent_name}\n"
                f"🧒 Ученик: {student_name}\n"
                f"📘 Курс: {course}\n"
                f"📅 Дата: {date}\n"
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
        update_application_status(app_id, "Отменено")
        bot.edit_message_text("❌ Заявка отменена.", call.message.chat.id, call.message.message_id)

    @bot.message_handler(func=lambda m: m.text == "🚫 Отменить урок" and is_admin(m.from_user.id))
    def handle_cancel_lesson_request(message):
        apps = get_assigned_applications()
        if not apps:
            bot.send_message(message.chat.id, "✅ Нет назначенных уроков")
            return

        for app in apps:
            app_id, tg_id, parent_name, student_name, _, _, course, date, link, _, _ = app
            text = (
                f"🆔 Заявка #{app_id}\n"
                f"👤 Родитель: {parent_name}\n"
                f"🧒 Ученик: {student_name}\n"
                f"📘 Курс: {course}\n"
                f"📅 Дата: {date}\n"
                f"🔗 Ссылка: {link}"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🚫 Отменить урок", callback_data=f"cancel_lesson:{app_id}"))
            bot.send_message(message.chat.id, text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("cancel_lesson:"))
    def handle_cancel_lesson(call):
        app_id = int(call.data.split(":")[1])
        cancel_assigned_lesson(app_id)
        bot.edit_message_text("🚫 Урок отменён.", call.message.chat.id, call.message.message_id)

        app = get_application_by_id(app_id)
        if app:
            tg_id = app[1]
            try:
                bot.send_message(int(tg_id), "⚠️ Ваш урок был отменён администратором. Мы свяжемся с вами для переназначения.")
            except Exception as e:
                print(f"[❗] Ошибка уведомления: {e}")

    @bot.message_handler(func=lambda m: m.text == "🕓 Перенести урок" and is_admin(m.from_user.id))
    def handle_reschedule_lesson(message):
        apps = get_assigned_applications()
        if not apps:
            bot.send_message(message.chat.id, "✅ Нет назначенных уроков")
            return

        for app in apps:
            app_id, tg_id, parent_name, student_name, _, _, course, date, link, _, _ = app
            text = (
                f"🆔 Заявка #{app_id}\n"
                f"👤 Родитель: {parent_name}\n"
                f"🧒 Ученик: {student_name}\n"
                f"📘 Курс: {course}\n"
                f"📅 Текущая дата: {date}\n"
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
        bot.send_message(message.chat.id, "🔗 Введите новую ссылку на урок:")
        bot.register_next_step_handler(message, lambda m: apply_reschedule(m, app_id, date_text))

    def apply_reschedule(message, app_id, date_text):
        if message.from_user.id not in writing_ids:
            return
        link = message.text.strip()
        update_application_lesson(app_id, date_text, link)
        bot.send_message(message.chat.id, f"✅ Урок перенесён на:\n📅 {date_text}\n🔗 {link}")

        app = get_application_by_id(app_id)
        if app:
            tg_id = app[1]
            course = app[6]
            try:
                bot.send_message(
                    int(tg_id),
                    f"🔄 Ваш урок был перенесён!\n📘 Курс: {course}\n🗓 Новая дата: {date_text}\n🔗 Ссылка: {link}"
                )
            except Exception as e:
                print(f"[❗] Не удалось уведомить ученика {tg_id}: {e}")

        writing_ids.discard(message.from_user.id)
