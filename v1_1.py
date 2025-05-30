import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Настройки Telegram бота ===
TOKEN = '7906419182:AAFkvUNgQpbgAka959-gC1oL0WGvq58SPJs'
bot = telebot.TeleBot(TOKEN)

# === Настройки Google Sheets ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Заявки на обучение").sheet1  # название таблицы

# === Временное хранилище данных пользователей ===
user_data = {}

@bot.message_handler(commands=['start'])
def welcome(message):
    chat_id = message.chat.id
    user_data[chat_id] = {}
    bot.send_message(chat_id, "👋 Привет! Я помогу тебе записаться на урок по Python.\n\nНапиши, пожалуйста, своё имя:")

# === Обработка всех входящих сообщений ===
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text

    if chat_id not in user_data:
        user_data[chat_id] = {}

    if "name" not in user_data[chat_id]:
        user_data[chat_id]["name"] = text
        bot.send_message(chat_id, "Отлично! А теперь укажи, пожалуйста, свой возраст или класс:")
    elif "age" not in user_data[chat_id]:
        user_data[chat_id]["age"] = text
        bot.send_message(chat_id, "Последний шаг: напиши, какая у тебя цель обучения (например: 'научиться с нуля', 'подготовка к ЕГЭ', 'создание игр'):")
    elif "goal" not in user_data[chat_id]:
        user_data[chat_id]["goal"] = text

        # Получаем все данные
        name = user_data[chat_id]["name"]
        age = user_data[chat_id]["age"]
        goal = user_data[chat_id]["goal"]
        username = f"@{message.from_user.username}" if message.from_user.username else "не указано"

        # Записываем в Google Таблицу
        try:
            sheet.append_row([name, age, goal, username])
            bot.send_message(chat_id, "✅ Спасибо за информацию! Мы свяжемся с тобой в ближайшее время.")
        except Exception as e:
            bot.send_message(chat_id, "⚠️ Произошла ошибка при сохранении данных. Попробуй позже.")
            print(f"Ошибка Google Sheets: {e}")

        # Удаляем из user_data
        del user_data[chat_id]

# === Запуск бота ===
print("Бот запущен...")
bot.polling(none_stop=True)
