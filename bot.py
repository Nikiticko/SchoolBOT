# === bot.py ===
from telebot import TeleBot
from handlers import commands, registration, admin
from services.monitor import start_monitoring
from config import API_TOKEN
from data.db import init_db
from handlers.course_editor import register_course_editor
bot = TeleBot(API_TOKEN)

# инициализация базы данных
init_db()

# запуск потоков и команд
start_monitoring(bot)
admin.register(bot)
registration.register(bot)
commands.register(bot)
register_course_editor(bot)

try:
    bot.infinity_polling(timeout=30, long_polling_timeout=5)
except Exception as e:
    print(f"[ERROR] polling error: {e}")
