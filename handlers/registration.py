from telebot import types
import re

from state.users import user_data, used_contacts, get_user_status, get_user_status_by_contact
from utils.menu import get_main_menu
from services.sheets_service import finish_registration
from handlers.admin import notify_admin_new_application


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

        exists, date, course, link = get_user_status(chat_id)
        if exists:
            if not date and not link:
                handle_existing_registration(bot, chat_id)
            else:
                markup = get_main_menu()
                bot.send_message(chat_id, f"Вы уже записаны на занятие:\n📅 Дата: {date}\n📘 Курс: {course}\n🔗 Ссылка: {link}", reply_markup=markup)
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
        contact = f"@{user.username}" if user.username else None
        user_data[chat_id]["contact"] = contact if contact else ""

        if contact and contact in used_contacts:
            exists, date, course, link = get_user_status_by_contact(contact)
            if exists:
                handle_existing_registration(bot, chat_id)
                return

        # ➕ Переход к подтверждению
        user_data[chat_id]["stage"] = "confirmation"
        send_confirmation(bot, chat_id)


    def process_phone(message):
        chat_id = message.chat.id
        if user_data.get(chat_id, {}).get("stage") != "phone":
            return

        if message.contact:
            phone = message.contact.phone_number
        else:
            phone = message.text.strip()

        phone = re.sub(r'\D', '', phone)
        if phone.startswith('8'):
            phone = '7' + phone[1:]
        if not phone.startswith('7') or len(phone) != 11:
            bot.send_message(chat_id, "Неверный формат номера. Введите, например: +79991234567")
            return bot.register_next_step_handler(message, process_phone)

        contact = f"+{phone}"
        if contact in used_contacts:
            exists, date, course, link = get_user_status_by_contact(contact)
            if exists:
                handle_existing_registration(bot, chat_id)
                return

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

        notify_admin_new_application(bot, user_data[chat_id])
        finish_registration(bot, chat_id)
        user_data.pop(chat_id, None)
