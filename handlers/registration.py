from telebot import types
import re

from state.users import user_data
from utils.menu import get_main_menu
from handlers.admin import notify_admin_new_application
from data.db import add_application, get_application_by_tg_id

def handle_existing_registration(bot, chat_id):
    markup = get_main_menu()
    bot.send_message(chat_id, "📝 Вы уже оставляли заявку. Ожидайте назначения урока.", reply_markup=markup)

def register(bot):
    @bot.message_handler(func=lambda m: m.text == "📋 Записаться")
    def handle_signup(message):
        chat_id = message.chat.id

        if user_data.get(chat_id, {}).get("in_progress"):
            bot.send_message(chat_id, "⏳ Пожалуйста, завершите текущую регистрацию.")
            return

        application = get_application_by_tg_id(str(chat_id))
        if application:
            lesson_date = application[7]
            lesson_link = application[8]
            course = application[6]
            if not lesson_date and not lesson_link:
                handle_existing_registration(bot, chat_id)
            else:
                markup = get_main_menu()
                bot.send_message(chat_id, f"Вы уже записаны на занятие:\n📅 Дата: {lesson_date}\n📘 Курс: {course}\n🔗 Ссылка: {lesson_link}", reply_markup=markup)
            return

        user_data[chat_id] = {
            "in_progress": True,
            "stage": "parent_name"
        }

        bot.send_message(chat_id, "Введите ваше имя (имя родителя):", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, process_parent_name)

    def process_parent_name(message):
        chat_id = message.chat.id
        if user_data.get(chat_id, {}).get("stage") != "parent_name":
            return

        user_data[chat_id]["parent_name"] = message.text.strip()
        user_data[chat_id]["stage"] = "student_name"
        bot.send_message(chat_id, "Введите имя ученика:")
        bot.register_next_step_handler(message, process_student_name)

    def process_student_name(message):
        chat_id = message.chat.id
        if user_data.get(chat_id, {}).get("stage") != "student_name":
            return

        user_data[chat_id]["student_name"] = message.text.strip()
        user_data[chat_id]["stage"] = "age"
        bot.send_message(chat_id, "Введите возраст ученика:")
        bot.register_next_step_handler(message, process_age)

    def process_age(message):
        chat_id = message.chat.id
        if user_data.get(chat_id, {}).get("stage") != "age":
            return

        user_data[chat_id]["age"] = message.text.strip()
        user_data[chat_id]["stage"] = "course"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Python")
        bot.send_message(chat_id, "Выберите курс:", reply_markup=markup)
        bot.register_next_step_handler(message, process_course)

    def process_course(message):
        chat_id = message.chat.id
        if user_data.get(chat_id, {}).get("stage") != "course":
            return

        course = message.text.strip()
        if course.lower() != "python":
            bot.send_message(chat_id, "Пожалуйста, выберите доступный курс, нажав на кнопку.")
            return bot.register_next_step_handler(message, process_course)

        user_data[chat_id]["course"] = course
        user = message.from_user
        contact = f"@{user.username}" if user.username else ""
        user_data[chat_id]["contact"] = contact

        user_data[chat_id]["stage"] = "confirmation"
        send_confirmation(bot, chat_id)

    def send_confirmation(bot, chat_id):
        data = user_data.get(chat_id)
        if not data:
            return

        summary = (
            f"Пожалуйста, проверьте введённые данные:\n\n"
            f"👤 Имя родителя: {data.get('parent_name')}\n"
            f"🧒 Имя ученика: {data.get('student_name')}\n"
            f"🎂 Возраст: {data.get('age')}\n"
            f"📘 Курс: {data.get('course')}\n"
            f"📞 Контакт: {data.get('contact') or 'не указан'}\n\n"
            "Подтвердите правильность данных:"
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
            bot.send_message(chat_id, "❌ Заявка отменена. Вы можете начать заново.", reply_markup=get_main_menu())
            user_data.pop(chat_id, None)
            return

        if user_data.get(chat_id, {}).get("stage") != "confirmation":
            bot.send_message(chat_id, "⚠️ Подтверждение недоступно. Попробуйте начать заново.")
            return

        data = user_data[chat_id]
        add_application(
            tg_id=str(chat_id),
            parent_name=data.get("parent_name"),
            student_name=data.get("student_name"),
            age=data.get("age"),
            contact=data.get("contact"),
            course=data.get("course")
        )
        notify_admin_new_application(bot, data)
        bot.send_message(chat_id, "✅ Ваша заявка успешно отправлена!", reply_markup=get_main_menu())
        user_data.pop(chat_id, None)
