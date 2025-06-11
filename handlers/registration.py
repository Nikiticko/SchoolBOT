# === handlers/registration.py ===
from telebot import types
import re

from state.users import user_data, chat_contact_map, used_contacts, pending, get_user_status
from utils.menu import get_main_menu
from services.sheets_service import worksheet, finish_registration
from handlers.admin import notify_admin_new_application

def handle_existing_registration(bot, chat_id):
    markup = get_main_menu()
    bot.send_message(chat_id, "📝 Вы уже оставляли заявку. Ожидайте назначения урока.", reply_markup=markup)

def register(bot):
    @bot.message_handler(func=lambda m: m.text == "📋 Записаться")
    def handle_signup(message):
        chat_id = message.chat.id
        exists, date, course, link = get_user_status(chat_id)
        if exists:
            if not date and not link:
                handle_existing_registration(bot, chat_id)
            else:
                markup = get_main_menu()
                bot.send_message(chat_id, f"Вы уже записаны на занятие:\n📅 Дата: {date}\n📘 Курс: {course}\n🔗 Ссылка: {link}", reply_markup=markup)
            return
        user_data[chat_id] = {}
        bot.send_message(chat_id, "Введите имя ученика:", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, process_name)

    def process_name(message):
        user_data[message.chat.id]['name'] = message.text.strip()
        bot.send_message(message.chat.id, "Введите возраст ученика:")
        bot.register_next_step_handler(message, process_age)

    def process_age(message):
        user_data[message.chat.id]['age'] = message.text.strip()
        bot.send_message(message.chat.id, "Какова цель занятий?")
        bot.register_next_step_handler(message, process_goal)

    def process_goal(message):
        chat_id = message.chat.id
        user_data[chat_id]['goal'] = message.text.strip()
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Python")
        bot.send_message(chat_id, "Выберите курс обучения:", reply_markup=markup)
        bot.register_next_step_handler(message, process_course)

    def process_course(message):
        course = message.text.strip()
        if course.lower() != "python":
            bot.send_message(message.chat.id, "Пожалуйста, выберите доступный курс, нажав на кнопку.")
            return bot.register_next_step_handler(message, process_course)

        user_data[message.chat.id]['course'] = course
        user = message.from_user

        if user.username:
            user_data[message.chat.id]['contact'] = f"@{user.username}"
            # Отправляем уведомление админу перед завершением регистрации
            notify_admin_new_application(bot, user_data[message.chat.id])
            finish_registration(bot, message.chat.id)
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            markup.add(types.KeyboardButton("📱 Отправить номер телефона", request_contact=True))
            bot.send_message(
                message.chat.id,
                "Пожалуйста, отправьте свой номер телефона или введите его вручную в формате +79991234567:",
                reply_markup=markup
            )
            bot.register_next_step_handler(message, process_phone)

    def process_phone(message):
        chat_id = message.chat.id

        if message.contact:  # контакт с кнопки
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
            exists, date, course, link = get_user_status(contact)
            if exists:
                user_data.pop(chat_id, None)
                if not date and not link:
                    handle_existing_registration(bot, chat_id)
                else:
                    markup = get_main_menu()
                    bot.send_message(chat_id, f"Вы уже записаны на занятие:\n📅 Дата: {date}\n📘 Курс: {course}\n🔗 Ссылка: {link}", reply_markup=markup)
                return

        user_data[chat_id]['contact'] = contact
        # Отправляем уведомление админу перед завершением регистрации
        notify_admin_new_application(bot, user_data[chat_id])
        finish_registration(bot, chat_id)
