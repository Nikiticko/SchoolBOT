from telebot import types
from config import ADMIN_ID
from data.db import (
    get_pending_applications,
    clear_applications,
    update_application_lesson,
    get_application_by_id
)
from state.users import writing_ids
from data.db import clear_archive


def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

def notify_admin_new_application(bot, application_data):
    try:
        notification = (
            "🔔 Новая заявка на обучение!\n\n"
            f"👤 Имя: {application_data.get('parent_name', 'Не указано')}\n"
            f"🧒 Ученик: {application_data.get('student_name', 'Не указано')}\n"
            f"📱 Контакт: {application_data.get('contact', 'Не указан')}\n"
            f"📚 Курс: {application_data.get('course', 'Не указан')}\n"
            f"📅 Возраст: {application_data.get('age', 'Не указан')}"
        )
        bot.send_message(ADMIN_ID, notification)
        print(f"[✅] Уведомление отправлено админу {ADMIN_ID}")
    except Exception as e:
        print(f"[❌] Ошибка при отправке уведомления админу: {str(e)}")


def register(bot):
    @bot.message_handler(commands=["ClearApplications"])
    def handle_clear_command(message):
        if not is_admin(message.from_user.id):
            return
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Да, очистить", callback_data="confirm_clear"),
            types.InlineKeyboardButton("❌ Нет", callback_data="cancel_clear")
        )
        bot.send_message(message.chat.id, "⚠️ Вы уверены, что хотите удалить все заявки?\nЭто действие необратимо.", reply_markup=markup)
    
    
    
    @bot.message_handler(commands=["ClearArchive"])
    def handle_clear_archive_command(message):
        if not is_admin(message.from_user.id):
            return

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Да, очистить архив", callback_data="confirm_clear_archive"),
            types.InlineKeyboardButton("❌ Нет", callback_data="cancel_clear_archive")
        )
        bot.send_message(
            message.chat.id,
            "⚠️ Вы уверены, что хотите удалить все архивные заявки?\nЭто действие необратимо.",
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda c: c.data in ["confirm_clear_archive", "cancel_clear_archive"])
    def handle_clear_archive_confirm(call):
        if not is_admin(call.from_user.id):
            return

        if call.data == "confirm_clear_archive":
            clear_archive()
            bot.send_message(call.message.chat.id, "🧹 Архив успешно очищен.")
        else:
            bot.send_message(call.message.chat.id, "❌ Очистка архива отменена.")

    @bot.callback_query_handler(func=lambda call: call.data in ["confirm_clear", "cancel_clear"])
    def handle_clear_confirm(call):
        chat_id = call.message.chat.id
        if not is_admin(call.from_user.id):
            return

        if call.data == "confirm_clear":
            clear_applications()
            bot.send_message(chat_id, "✅ Все заявки успешно удалены.")
        else:
            bot.send_message(chat_id, "❌ Очистка отменена.")

    @bot.message_handler(func=lambda m: m.text == "📋 Список заявок" and is_admin(m.from_user.id))
    def handle_pending_applications(message):
        try:
            applications = get_pending_applications()
            if not applications:
                bot.send_message(message.chat.id, "✅ Нет заявок без назначенной даты")
                return

            for app in applications:
                app_id, tg_id, parent_name, student_name, age, contact, course, lesson_date, lesson_link, status, created_at = app
                text = (
                    f"🆔 Заявка #{app_id}\n"
                    f"👤 Родитель: {parent_name}\n"
                    f"🧒 Ученик: {student_name}\n"
                    f"📞 Контакт: {contact or 'не указан'}\n"
                    f"🎂 Возраст: {age}\n"
                    f"📘 Курс: {course}\n"
                    f"📅 Статус: {status}\n"
                    f"🕒 Создано: {created_at}"
                )
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🕒 Назначить", callback_data=f"assign:{app_id}"))
                bot.send_message(message.chat.id, text, reply_markup=markup)

        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка при получении заявок: {str(e)}")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("assign:"))
    def handle_assign_callback(call):
        app_id = int(call.data.split(":")[1])
        writing_ids.add(call.from_user.id)
        bot.send_message(call.message.chat.id, f"📅 Введите дату и время урока для заявки #{app_id} (например: 22.06 17:00):")
        bot.register_next_step_handler(call.message, lambda m: get_link(m, app_id))

    def get_link(message, app_id):
        if message.from_user.id not in writing_ids:
            return
        date = message.text.strip()
        bot.send_message(message.chat.id, "🔗 Введите ссылку на урок:")
        bot.register_next_step_handler(message, lambda m: finalize_lesson(m, app_id, date))

    def finalize_lesson(message, app_id, date):
        if message.from_user.id not in writing_ids:
            return
        link = message.text.strip()
        update_application_lesson(app_id, date, link)
        bot.send_message(message.chat.id, f"✅ Урок назначен!\n📅 {date}\n🔗 {link}")

        app = get_application_by_id(app_id)
        if app:
            tg_id = app[1]
            course = app[6]
            try:
                bot.send_message(
                    int(tg_id),
                    f"📅 Вам назначен урок!\n📘 Курс: {course}\n🗓 Дата: {date}\n🔗 Ссылка: {link}"
                )
            except Exception as e:
                print(f"[❗] Ошибка уведомления ученика {tg_id}: {e}")

        writing_ids.discard(message.from_user.id)

    @bot.message_handler(func=lambda m: m.text == "📚 Редактировать курсы" and is_admin(m.from_user.id))
    def handle_course_menu(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ Добавить курс", "🗑 Удалить курс")
        markup.add("❄ Заморозить курс", "📝 Отредактировать курс")
        markup.add("🔙 Назад")
        bot.send_message(message.chat.id, "🎓 Меню редактирования курсов:", reply_markup=markup)
