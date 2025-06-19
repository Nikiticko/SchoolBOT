# === utils/menu.py ===
from telebot import types
from config import ADMIN_ID

def get_main_menu(user_id=None):
    """Получение главного меню с учетом прав пользователя"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📅 Мое занятие", "📋 Записаться")
    markup.add("ℹ️ О преподавателе", "💰 Цены и форматы")
    markup.add("📚 Доступные курсы")
    
    return markup
