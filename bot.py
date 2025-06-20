# === bot.py ===
from telebot import TeleBot
from config import API_TOKEN
from data.db import init_db
from services.monitor import start_monitoring

# Регистрация хендлеров
from handlers import commands, registration, admin
from handlers.course_editor import register_course_editor
from handlers.admin_actions import register_admin_actions

# Инициализация бота и БД
bot = TeleBot(API_TOKEN)
init_db()

# Запуск мониторинга заявок
start_monitoring(bot)

# Регистрация всех обработчиков
commands.register(bot)               # пользовательские команды
registration.register(bot)          # регистрация заявки
admin.register(bot)                 # меню админа + список заявок
register_course_editor(bot)        # редактор курсов
register_admin_actions(bot)        # действия с заявками

# Запуск бота
try:
    bot.infinity_polling(timeout=30, long_polling_timeout=5)
except Exception as e:
    print(f"[ERROR] polling error: {e}")
