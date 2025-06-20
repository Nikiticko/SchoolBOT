from telebot import types
from config import ADMIN_ID
from data.db import get_courses, get_pending_applications

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
    def show_admin_panel(chat_id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("📋 Список заявок", "📚 Редактировать курсы")
        bot.send_message(chat_id, "👋 Добро пожаловать в админ-панель!", reply_markup=markup)

    @bot.message_handler(commands=["start"])
    def handle_start(message):
        user_id = message.from_user.id
        if is_admin(user_id):
            show_admin_panel(message.chat.id)
        else:
            bot.send_message(message.chat.id, "👋 Добро пожаловать! Для записи нажмите кнопку в меню.")

    @bot.message_handler(func=lambda m: m.text == "📋 Список заявок" and is_admin(m.from_user.id))
    def handle_pending_applications(message):
        try:
            applications = get_pending_applications()
            if not applications:
                bot.send_message(message.chat.id, "✅ Нет заявок без назначенной даты")
                return

            response_parts = []
            for app in applications:
                app_id, tg_id, parent_name, student_name, age, contact, course, lesson_date, lesson_link, status, created_at = app
                text = (
                    f"🆔 ID: {app_id}\n"
                    f"👤 Родитель: {parent_name}\n"
                    f"🧒 Ученик: {student_name}\n"
                    f"📞 Контакт: {contact or 'не указан'}\n"
                    f"🎂 Возраст: {age}\n"
                    f"📘 Курс: {course}\n"
                    f"📅 Статус: {status}\n"
                    f"🕒 Создано: {created_at}\n"
                    "------------------------"
                )
                response_parts.append(text)

            response = "\n\n".join(response_parts)
            if len(response) > 4000:
                parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
                for part in parts:
                    bot.send_message(message.chat.id, part)
            else:
                bot.send_message(message.chat.id, response)

        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка при получении заявок: {str(e)}")

    @bot.message_handler(func=lambda m: m.text == "📚 Редактировать курсы" and is_admin(m.from_user.id))
    def handle_course_menu(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ Добавить курс", "🗑 Удалить курс")
        markup.add("❄ Заморозить курс", "📝 Отредактировать курс")
        markup.add("🔙 Назад")
        bot.send_message(message.chat.id, "🎓 Меню редактирования курсов:", reply_markup=markup)
