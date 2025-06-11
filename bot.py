# === bot.py ===
from telebot import TeleBot
from handlers import commands, registration, admin
from services.monitor import start_monitoring

from config import API_TOKEN

bot = TeleBot(API_TOKEN)

# запуск потоков и команд
start_monitoring(bot)
commands.register(bot)
registration.register(bot)
admin.register(bot)  # Регистрация админ-обработчиков

bot.infinity_polling()
