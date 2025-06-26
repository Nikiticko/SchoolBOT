# === utils/menu.py ===
from telebot import types
from config import ADMIN_ID

def get_main_menu(user_id=None):
    """Меню для пользователя"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📅 Мое занятие", "📋 Записаться")
    markup.add("ℹ️ О преподавателе", "💰 Цены и форматы")
    markup.add("📚 Доступные курсы")
    markup.add("🆘 Обратиться к админу")
    return markup

def get_admin_menu():
    """Меню для администратора"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📋 Список заявок", "📚 Редактировать курсы")
    markup.row("✅ Завершить заявку", "❌ Отменить заявку", "🚫 Отменить урок", "🕓 Перенести урок")
    markup.add("📨 Обращения пользователей")

    markup.add("⬇️ Выгрузить данные")
    return markup

def get_cancel_button():
    """Создает кнопку отмены"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("🔙 Отмена")
    return markup

def handle_cancel_action(bot, message, action_type="регистрация", logger=None):
    """Обрабатывает отмену действия"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # Очищаем данные пользователя
    from state.users import user_data
    user_data.pop(chat_id, None)
    
    # Определяем куда возвращаться
    if action_type == "курс":
        # Для админских действий с курсами - возврат в меню редактора курсов
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ Добавить курс", "🗑 Удалить курс")
        markup.add("❄ Заморозить курс", "📝 Отредактировать курс")
        markup.add("🔙 Назад")
        bot.send_message(chat_id, "❌ Добавление курса отменено", reply_markup=markup)
    elif action_type == "урок":
        # Для назначения уроков - возврат в админ-меню
        bot.send_message(chat_id, "❌ Назначение урока отменено", reply_markup=get_admin_menu())
    elif action_type == "отмена_заявки":
        # Для отмены заявок - возврат в админ-меню
        bot.send_message(chat_id, "❌ Отмена заявки отменена", reply_markup=get_admin_menu())
    else:
        # Для обычной регистрации - возврат в главное меню
        bot.send_message(chat_id, "❌ Регистрация отменена", reply_markup=get_main_menu())
    
    # Логируем отмену
    if logger:
        logger.info(f"User {user_id} cancelled {action_type}")

def get_course_editor_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Добавить курс", "🗑 Удалить курс")
    markup.add("❄ Заморозить курс", "📝 Отредактировать курс")
    markup.add("👁 Просмотреть все курсы")
    markup.add("🔙 Назад")
    return markup
