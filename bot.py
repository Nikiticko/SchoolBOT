# === bot.py ===
from telebot import TeleBot
from handlers import commands, registration, admin
from services.monitor import start_monitoring

from config import API_TOKEN

bot = TeleBot(API_TOKEN)

# запуск потоков и команд
start_monitoring(bot)
admin.register(bot)  # Регистрация админ-обработчиков
registration.register(bot)
commands.register(bot)

try:
    bot.infinity_polling(timeout=30, long_polling_timeout=5)
except Exception as e:
    print(f"[ERROR] polling error: {e}")
