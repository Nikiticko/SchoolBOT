import telebot
from telebot import types
import gspread
import threading
import time
import re
import os

API_TOKEN = "7906419182:AAFkvUNgQpbgAka959-gC1oL0WGvq58SPJs"
GOOGLE_SHEET_NAME = "Заявки на обучение"
SERVICE_ACCOUNT_FILE = "creds.json"

bot = telebot.TeleBot(API_TOKEN)

try:
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(f"Файл {SERVICE_ACCOUNT_FILE} не найден. Убедитесь, что он находится рядом со скриптом.")
    gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
    sh = gc.open(GOOGLE_SHEET_NAME)
    worksheet = sh.sheet1
except Exception as e:
    print("Ошибка подключения к Google Sheets:", e)
    raise

user_data = {}
chat_contact_map = {}
used_contacts = set()
pending = {}

try:
    contacts_col = worksheet.col_values(4)
    if contacts_col and contacts_col[0].strip().lower() in ["contact", "контакты"]:
        contacts_col = contacts_col[1:]
    for contact in contacts_col:
        contact = contact.strip()
        if contact:
            used_contacts.add(contact)
except Exception as e:
    print("Error loading contacts from sheet:", e)

def get_user_status(contact):
    try:
        cell = worksheet.find(contact)
    except Exception:
        return False, None, None, None
    if cell:
        row = worksheet.row_values(cell.row)
        course = row[4] if len(row) > 4 else ""
        date = row[5] if len(row) > 5 else ""
        link = row[6] if len(row) > 6 else ""
        return True, date.strip(), course.strip(), link.strip()
    return False, None, None, None

def finish_registration(chat_id):
    if chat_id not in user_data:
        return
    data = user_data[chat_id]
    row = [
        data.get('name', '').strip(),
        data.get('age', '').strip(),
        data.get('goal', '').strip(),
        data.get('contact', '').strip(),
        data.get('course', '').strip(),
        "",  # дата занятия
        ""   # ссылка
    ]
    try:
        worksheet.append_row(row)
    except Exception as e:
        bot.send_message(chat_id, "Произошла ошибка при сохранении данных. Попробуйте позже.")
        return
    used_contacts.add(data['contact'])
    chat_contact_map[chat_id] = data['contact']
    pending[data['contact']] = {"chat_id": chat_id}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📋 Записаться", "ℹ️ О преподавателе")
    markup.row("💰 Цены и форматы", "⭐ Отзывы")
    markup.row("📚 Доступные курсы", "📅 Мое занятие")
    bot.send_message(chat_id, "Спасибо! Ваша заявка принята. Ожидайте расписание своего урока.", reply_markup=markup)
    user_data.pop(chat_id, None)

def monitor_sheet():
    while True:
        try:
            for contact, info in list(pending.items()):
                try:
                    cell = worksheet.find(contact)
                    row = worksheet.row_values(cell.row)
                    course = row[4] if len(row) > 4 else ""
                    date = row[5] if len(row) > 5 else ""
                    link = row[6] if len(row) > 6 else ""
                except:
                    continue
                if date.strip():
                    msg = f"Ваш урок назначен на {date.strip()}\nКурс: {course.strip()}\nСсылка на занятие: {link.strip()}"
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    markup.add("📅 Мое занятие")
                    bot.send_message(info["chat_id"], msg, reply_markup=markup)
                    pending.pop(contact, None)
            time.sleep(30)
        except Exception as e:
            print("Ошибка мониторинга таблицы:", e)
            time.sleep(30)

threading.Thread(target=monitor_sheet, daemon=True).start()

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📋 Записаться", "ℹ️ О преподавателе")
    markup.row("💰 Цены и форматы", "⭐ Отзывы")
    markup.row("📚 Доступные курсы", "📅 Мое занятие")
    bot.send_message(chat_id, "Добро пожаловать! Выберите действие:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📋 Записаться")
def handle_signup(message):
    chat_id = message.chat.id
    username = message.from_user.username
    contact = f"@{username}" if username else None
    if contact and contact in used_contacts:
        exists, date, course, link = get_user_status(contact)
        if exists:
            bot.send_message(chat_id, f"Вы уже записаны на занятие:\n📅 Дата: {date}\n📘 Курс: {course}\n🔗 Ссылка: {link}")
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
        finish_registration(message.chat.id)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton("📱 Отправить номер телефона", request_contact=True))
        bot.send_message(message.chat.id, "Пожалуйста, отправьте свой номер телефона:", reply_markup=markup)
        bot.register_next_step_handler(message, process_phone)

def process_phone(message):
    phone = message.contact.phone_number
    phone = re.sub(r'\D', '', phone)
    if phone.startswith('8'):
        phone = '7' + phone[1:]
    user_data[message.chat.id]['contact'] = f"+{phone}"
    finish_registration(message.chat.id)

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
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📋 Записаться", "ℹ️ О преподавателе")
    markup.row("💰 Цены и форматы", "⭐ Отзывы")
    markup.row("📚 Доступные курсы", "📅 Мое занятие")
    if exists and date:
        bot.send_message(chat_id, f"📅 Дата: {date}\n📘 Курс: {course}\n🔗 Ссылка на занятие: {link}", reply_markup=markup)
    else:
        bot.send_message(chat_id, "Ваш урок еще не назначен. Пожалуйста, ожидайте.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "ℹ️ О преподавателе")
def about_teacher(message):
    bot.send_message(message.chat.id, "🧑‍🏫 Преподаватель: Никита\nОпыт: 3 года в Python\nРаботаю с детьми от 10 до 18 лет")

@bot.message_handler(func=lambda m: m.text == "💰 Цены и форматы")
def pricing(message):
    bot.send_message(message.chat.id, "💰 Индивидуально: 600₽\n👥 В группе: 400₽\n📍 Формат: Zoom / Discord")

@bot.message_handler(func=lambda m: m.text == "⭐ Отзывы")
def reviews(message):
    bot.send_message(message.chat.id, "Пока нет отзывов. Вы можете быть первым!")

@bot.message_handler(func=lambda m: m.text == "📚 Доступные курсы")
def courses(message):
    bot.send_message(message.chat.id, "📘 Python с нуля (10–14 лет)\n📗 Подготовка к ЕГЭ/ОГЭ\n📙 Проектное программирование")

bot.infinity_polling()
