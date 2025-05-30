import telebot
from telebot import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Настройки ===
TOKEN = '7906419182:AAFkvUNgQpbgAka959-gC1oL0WGvq58SPJs'
bot = telebot.TeleBot(TOKEN)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Заявки на обучение").sheet1

user_data = {}

# === Главное меню ===
def main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("\ud83d\udccb Записаться", "\u2139\ufe0f О преподавателе")
    markup.row("\ud83d\udcb0 Цены и форматы", "\u2b50 Отзывы")
    bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)

# === /start ===
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_data.pop(chat_id, None)
    bot.send_message(chat_id, "\ud83d\udc4b Привет! Я — бот для записи на занятия по *Python*.\n"
                              "Нажми кнопку ниже, чтобы начать.", parse_mode="Markdown")
    main_menu(chat_id)

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
@bot.message_handler(func=lambda m: m.text in ["\ud83d\udccb Записаться", "\u2139\ufe0f О преподавателе", "\ud83d\udcb0 Цены и форматы", "\u2b50 Отзывы"])
def menu_handler(message):
    chat_id = message.chat.id
    text = message.text

    if text == "\ud83d\udccb Записаться":
        user_data[chat_id] = {}
        bot.send_message(chat_id, "\u270d\ufe0f Введи, пожалуйста, своё *имя*:", parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
    elif text == "\u2139\ufe0f О преподавателе":
        bot.send_message(chat_id, "\ud83e\uddd1\u200d\ud83d\udcbc Преподаватель: Никита\n"
                                  "\ud83d\udc68\u200d\ud83d\udcbb 3 года опыта в Python\n"
                                  "\ud83c\udf93 Работаю с учениками от 10 до 18 лет\n"
                                  "\ud83d\udcc8 Помогаю понять программирование через практику")
    elif text == "\ud83d\udcb0 Цены и форматы":
        show_price(chat_id)
    elif text == "\u2b50 Отзывы":
        bot.send_message(chat_id, "\ud83d\udce2 Отзывы скоро появятся. Ты можешь быть первым, кто оставит положительный отзыв \ud83d\ude0a")

# === Вывод цены ===
def show_price(chat_id):
    bot.send_message(chat_id,
        "\ud83d\udcb0 *Стоимость занятий:*\n"
        "• Индивидуально — *600\u20bd/занятие*\n"
        "• В группе (до 4 чел) — *400\u20bd/занятие*\n\n"
        "\ud83d\udcc5 *Форматы:*\n"
        "• Онлайн через Zoom / Discord\n"
        "• Домашние задания, мини-проекты\n"
        "• Уровни: с нуля / ЕГЭ / проекты",
        parse_mode='Markdown')

# === Обработка анкеты ===
@bot.message_handler(func=lambda message: True)
def handle_form(message):
    chat_id = message.chat.id
    text = message.text

    if chat_id not in user_data:
        return

    step = user_data[chat_id]

    if "name" not in step:
        step["name"] = text
        bot.send_message(chat_id, "\ud83d\udcda Укажи, пожалуйста, свой *возраст или класс:*", parse_mode="Markdown")
    elif "age" not in step:
        step["age"] = text

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Научиться с нуля", "Подготовка к ЕГЭ")
        markup.add("Создание игр", "Хочу научиться делать сайты")
        bot.send_message(chat_id, "\ud83c\udf1f Выбери цель обучения:", reply_markup=markup)

    elif "goal" not in step:
        step["goal"] = text

        if message.from_user.username:
            step["username"] = f"@{message.from_user.username}"
            step["phone"] = "-"
            save_to_sheet(chat_id)
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            button = types.KeyboardButton("\ud83d\udcde Отправить номер", request_contact=True)
            markup.add(button)
            bot.send_message(chat_id, "У тебя не указан username. Пожалуйста, отправь свой номер телефона для связи:", reply_markup=markup)

# === Обработка номера телефона ===
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    chat_id = message.chat.id
    if chat_id in user_data and "phone" not in user_data[chat_id]:
        phone = message.contact.phone_number
        user_data[chat_id]["phone"] = phone
        user_data[chat_id]["username"] = "-"
        save_to_sheet(chat_id)

# === Сохраняем в таблицу ===
def save_to_sheet(chat_id):
    step = user_data[chat_id]
    name = step["name"]
    age = step["age"]
    goal = step["goal"]
    username = step["username"]
    phone = step["phone"]

    try:
        sheet.append_row([name, age, goal, username, phone])
        bot.send_message(chat_id, "\u2705 Спасибо, заявка записана! Мы свяжемся с тобой в ближайшее время.", reply_markup=types.ReplyKeyboardRemove())
    except Exception as e:
        bot.send_message(chat_id, "\u26a0\ufe0f Ошибка при сохранении данных. Попробуй позже.")
        print(f"Ошибка Google Sheets: {e}")

    user_data.pop(chat_id, None)
    main_menu(chat_id)

# === Запуск ===
print("Бот запущен...")
bot.polling(none_stop=True)
