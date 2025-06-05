import telebot
from telebot import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Настройки ===
TOKEN = '7906419182:AAFkvUNgQpbgAka959-gC1oL0WGvq58SPJs'
bot = telebot.TeleBot(TOKEN)

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Заявки на обучение").sheet1

user_data = {}
user_contacts = {}

# === Вспомогательные функции ===
def normalize_phone(phone: str) -> str:
    digits = ''.join(filter(str.isdigit, phone))
    if len(digits) == 11 and digits[0] == '8':
        digits = '7' + digits[1:]
    return digits

def is_contact_registered(contact_value: str) -> bool:
    contact_value = contact_value.strip()
    all_contacts = [str(row.get("Контакты", "")).strip() for row in sheet.get_all_records()]
    for existing in all_contacts:
        existing = existing.strip()
        if existing.startswith('@') and contact_value.startswith('@'):
            if existing.lower() == contact_value.lower():
                return True
        elif not any(c.isalpha() for c in existing):
            if normalize_phone(existing) == normalize_phone(contact_value):
                return True
    return False

def save_application(name: str, age: str, goal: str, contact: str):
    sheet.append_row([name, age, goal, contact, "-"])

# === Главное меню ===
def main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    contact_value = user_contacts.get(chat_id, "")
    found = False
    has_lesson = False

    for row in sheet.get_all_records():
        if contact_value == row.get("Контакты", ""):
            found = True
            if row.get("Дата занятия", "") not in ["", "-"]:
                has_lesson = True
            break

    if found:
        if has_lesson:
            markup.row("📅 Мой урок", "📚 Доступные курсы")
        else:
            markup.row("📚 Доступные курсы")
    else:
        markup.row("📋 Записаться", "ℹ️ О преподавателе")
        markup.row("💰 Цены и форматы", "⭐ Отзывы")
        markup.row("📚 Доступные курсы")

    bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)

# === /start ===
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_data.pop(chat_id, None)
    username = message.from_user.username
    contact_value = f"@{username}" if username else str(chat_id)
    user_contacts[chat_id] = contact_value
    if is_contact_registered(contact_value):
        bot.send_message(chat_id, "📝 Вы уже оставляли заявку. Мы свяжемся с вами в ближайшее время.", reply_markup=types.ReplyKeyboardRemove())
    else:
        greeting = ("👋 Привет! Я — бот для записи на занятия по Python.\n"
                    "Нажми кнопку ниже, чтобы начать.")
        bot.send_message(chat_id, greeting, parse_mode="Markdown")
        main_menu(chat_id)

# === Шаги регистрации ===
@bot.message_handler(content_types=['text', 'contact'])
def registration_steps(msg):
    chat_id = msg.chat.id

    # Инициализируем, если нужно
    if chat_id not in user_data:
        return

    step_data = user_data[chat_id]

    if 'name' not in step_data and msg.content_type == 'text':
        step_data['name'] = msg.text.strip()
        bot.send_message(chat_id, "📅 Сколько тебе лет?")
        return

    if 'age' not in step_data and msg.content_type == 'text':
        step_data['age'] = msg.text.strip()
        bot.send_message(chat_id, "🎯 Какая цель занятий? (например: подготовка к ОГЭ/ЕГЭ, научиться программировать)")
        return

    if 'goal' not in step_data and msg.content_type == 'text':
        step_data['goal'] = msg.text.strip()
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        button = types.KeyboardButton("📱 Отправить номер телефона", request_contact=True)
        markup.add(button)
        bot.send_message(chat_id, "📞 Пожалуйста, отправь свой номер телефона.", reply_markup=markup)
        return

    if 'goal' in step_data and 'phone' not in step_data and msg.content_type == 'contact':
        contact = msg.contact
        if contact.user_id != msg.from_user.id:
            bot.send_message(chat_id, "❗ Пожалуйста, отправь СВОЙ номер телефона через кнопку.")
            return
        phone_number = contact.phone_number
        if phone_number:
            step_data['phone'] = normalize_phone(phone_number)
            save_application(step_data['name'], step_data['age'], step_data['goal'], step_data['phone'])
            bot.send_message(chat_id, f"✅ Спасибо, {step_data['name']}! Мы свяжемся с вами в ближайшее время.", reply_markup=types.ReplyKeyboardRemove())
            user_data.pop(chat_id, None)
            main_menu(chat_id)
        else:
            bot.send_message(chat_id, "❗ Не удалось получить номер телефона. Попробуй ещё раз.")

# === /help ===
@bot.message_handler(commands=['help'])
def help_message(message):
    bot.send_message(message.chat.id,
                     "🤖 Команды:\n"
                     "/start — главное меню\n"
                     "/help — помощь\n"
                     "/price — цены\n")

# === /price ===
@bot.message_handler(commands=['price'])
def price(message):
    show_price(message.chat.id)

# === Ответ на кнопки меню ===
@bot.message_handler(func=lambda m: m.text in ["📋 Записаться", "ℹ️ О преподавателе", "💰 Цены и форматы", "⭐ Отзывы", "📚 Доступные курсы", "📅 Мой урок"])
def menu_handler(message):
    chat_id = message.chat.id
    text = message.text

    if text == "📋 Записаться":
        contact_value = user_contacts.get(chat_id, f"@{message.from_user.username}" if message.from_user.username else str(chat_id))
        if is_contact_registered(contact_value):
            bot.send_message(chat_id, "📝 Вы уже оставляли заявку. Мы свяжемся с вами в ближайшее время.")
        else:
            user_data[chat_id] = {}
            bot.send_message(chat_id, "✍️ Введи, пожалуйста, своё *имя*:", parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())

    elif text == "ℹ️ О преподавателе":
        bot.send_message(chat_id, "🧑‍💼 Преподаватель: Никита\n"
                                  "👨‍💻 3 года опыта в Python\n"
                                  "🎓 Работаю с учениками от 10 до 18 лет\n"
                                  "📈 Помогаю понять программирование через практику")

    elif text == "💰 Цены и форматы":
        show_price(chat_id)

    elif text == "⭐ Отзывы":
        bot.send_message(chat_id, "📢 Отзывы скоро появятся. Ты можешь быть первым, кто оставит положительный отзыв 😊")

    elif text == "📚 Доступные курсы":
        bot.send_message(chat_id,
                         "📘 *Курсы:*\n"
                         "• Python с нуля (10–14 лет)\n"
                         "• Школьная информатика (подготовка к ЕГЭ/ОГЭ)\n\n"
                         "Каждый курс подбирается индивидуально. Запишитесь и получите бесплатную консультацию!",
                         parse_mode="Markdown")

    elif text == "📅 Мой урок":
        contact_value = user_contacts.get(chat_id)
        for row in sheet.get_all_records():
            if contact_value == row.get("Контакты", ""):
                date = row.get("Дата занятия", "не назначена")
                bot.send_message(chat_id, f"📅 Ваша запись: {date}")
                return
        bot.send_message(chat_id, "🔍 Запись не найдена. Пожалуйста, сначала зарегистрируйтесь через \"📋 Записаться\".")

# === Показать цены ===
def show_price(chat_id):
    bot.send_message(chat_id,
                     "💰 Стоимость занятий:\n"
                     "• Индивидуально — 600₽/занятие\n"
                     "• В группе (до 4 чел) — 400₽/занятие\n\n"
                     "📅 Форматы:\n"
                     "• Онлайн через Zoom / Discord\n"
                     "• Домашние задания, мини-проекты\n"
                     "• Уровни: с нуля / ЕГЭ / проекты",
                     parse_mode='Markdown')

print("Бот запущен...")
bot.polling(none_stop=True)
