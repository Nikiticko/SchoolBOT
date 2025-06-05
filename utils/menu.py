# === utils/menu.py ===
from telebot import types

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📋 Записаться", "ℹ️ О преподавателе")
    markup.row("💰 Цены и форматы")
    markup.row("📚 Доступные курсы", "📅 Мое занятие")
    return markup
