# === handlers/commands.py ===
from telebot import types
from state.users import get_user_status, chat_contact_map
from state.users import user_data, used_contacts
from utils.menu import get_main_menu

def register(bot):

    @bot.message_handler(commands=['start'])
    def handle_start(message):
        chat_id = message.chat.id
        markup = get_main_menu()
        bot.send_message(chat_id, "Добро пожаловать! Выберите действие:", reply_markup=markup)

    @bot.message_handler(func=lambda m: m.text == "ℹ️ О преподавателе")
    def about_teacher(message):
        bot.send_message(message.chat.id, "🧑‍🏫 Преподаватель: Никита\nОпыт: 3 года в Python\nРаботаю с детьми от 10 до 18 лет")

    @bot.message_handler(func=lambda m: m.text == "💰 Цены и форматы")
    def pricing(message):
        bot.send_message(message.chat.id, "💰 Индивидуально: 600₽\n👥 В группе: 400₽\n📍 Формат: Zoom / Discord")

    @bot.message_handler(func=lambda m: m.text == "📚 Доступные курсы")
    def courses(message):
        bot.send_message(message.chat.id, "📘 Python с нуля (10–14 лет)\n📗 Подготовка к ЕГЭ/ОГЭ\n📙 Проектное программирование")

    @bot.message_handler(func=lambda m: m.text == "📅 Мое занятие")
    def handle_my_lesson(message):
        chat_id = message.chat.id
        contact = chat_contact_map.get(chat_id)
        if not contact and message.from_user.username:
            contact = f"@{message.from_user.username}"
        if not contact:
            bot.send_message(chat_id, "Вы еще не регистрировались.")
            return
        exists, date, course, link = get_user_status(contact)
        if exists and date:
            bot.send_message(chat_id, f"📅 Дата: {date}\n📘 Курс: {course}\n🔗 Ссылка на занятие: {link}", reply_markup=get_main_menu())
        else:
            bot.send_message(chat_id, "Ваш урок еще не назначен. Пожалуйста, ожидайте.", reply_markup=get_main_menu())
