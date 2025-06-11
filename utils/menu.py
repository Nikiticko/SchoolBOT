# === utils/menu.py ===
from telebot import types
from config import ADMIN_ID

def get_main_menu(user_id=None):
    """Получение главного меню с учетом прав пользователя"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📅 Мое занятие", "📋 Записаться")
    markup.add("ℹ️ О преподавателе", "💰 Цены и форматы")
    markup.add("📚 Доступные курсы")
    
    # Добавляем кнопку админ-панели только для администратора
    if user_id and str(user_id) == str(ADMIN_ID):
        markup.add("👨‍💼 Админ-панель")
    
    return markup
