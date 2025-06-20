# === utils/menu.py ===
from telebot import types
from config import ADMIN_ID

def get_main_menu(user_id=None):
    """Меню для пользователя"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📅 Мое занятие", "📋 Записаться")
    markup.add("ℹ️ О преподавателе", "💰 Цены и форматы")
    markup.add("📚 Доступные курсы")
    return markup

def get_admin_menu():
    """Меню для администратора"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📋 Список заявок", "📚 Редактировать курсы")
    markup.row("✅ Завершить заявку", "❌ Отменить заявку", "🚫 Отменить урок", "🕓 Перенести урок")
    return markup
