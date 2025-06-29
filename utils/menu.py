# === utils/menu.py ===
from telebot import types
from config import ADMIN_ID

def get_main_menu(user_id=None):
    """Меню для пользователя"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📅 Мое занятие", "📋 Записаться")
    markup.add("ℹ️ О преподавателе", "💰 Цены и форматы")
    markup.add("📚 Доступные курсы", "⭐ Отзывы")
    markup.add("🆘 Обратиться к админу")
    return markup

def get_admin_menu(): 
    """Меню для администратора"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📋 Список заявок", "📚 Редактировать курсы")
    markup.row("📝 Управление уроками")
    markup.add("📨 Обращения пользователей", "⭐ Отзывы")
    markup.add("⬇️ Выгрузить данные")
    return markup

def get_appropriate_menu(user_id):
    """Возвращает подходящее меню в зависимости от роли пользователя"""
    if str(user_id) == str(ADMIN_ID):
        return get_admin_menu()
    else:
        return get_main_menu()

def is_admin(user_id):
    """Проверяет, является ли пользователь администратором"""
    return str(user_id) == str(ADMIN_ID)

def create_admin_menu():
    """Инлайн-меню для администратора с новыми опциями БД"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # Основные разделы
    markup.add(
        types.InlineKeyboardButton("📝 Заявки", callback_data="admin_applications"),
        types.InlineKeyboardButton("🗄️ Архив", callback_data="admin_archive")
    )
    markup.add(
        types.InlineKeyboardButton("📚 Курсы", callback_data="admin_courses"),
        types.InlineKeyboardButton("📞 Обращения", callback_data="admin_contacts")
    )
    markup.add(
        types.InlineKeyboardButton("⭐ Отзывы", callback_data="admin_reviews"),
        types.InlineKeyboardButton("📊 Статистика БД", callback_data="admin_db_stats")
    )
    
    # Очистка данных
    markup.add(
        types.InlineKeyboardButton("🗑️ Очистить заявки", callback_data="admin_clear_applications"),
        types.InlineKeyboardButton("🗑️ Очистить архив", callback_data="admin_clear_archive")
    )
    markup.add(
        types.InlineKeyboardButton("🗑️ Очистить курсы", callback_data="admin_clear_courses"),
        types.InlineKeyboardButton("🗑️ Очистить обращения", callback_data="admin_clear_contacts")
    )
    markup.add(
        types.InlineKeyboardButton("🗑️ Очистить отзывы", callback_data="admin_clear_reviews")
    )
    
    # Миграция БД
    markup.add(
        types.InlineKeyboardButton("🔧 Миграция БД", callback_data="admin_migrate_db")
    )
    
    return markup

def get_lesson_management_menu():
    """Меню управления уроками (на месте клавиатуры)"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📅 Посмотреть запланированные уроки")
    markup.row("✅ Завершить заявку", "❌ Отменить заявку")
    markup.row("🚫 Отменить урок", "🕓 Перенести урок")
    markup.add("🔙 Назад в админ-меню")
    return markup

def create_confirm_menu(action_type):
    """Меню подтверждения для опасных операций"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("✅ Да, подтверждаю", callback_data=f"confirm_{action_type}"),
        types.InlineKeyboardButton("❌ Отмена", callback_data="cancel_action")
    )
    
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
    
    # ИСПРАВЛЕНО: Используем новый StateManager для очистки данных
    from state.users import clear_user_data
    clear_user_data(chat_id)
    
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
        bot.send_message(chat_id, "❌ Регистрация отменена", reply_markup=get_appropriate_menu(user_id))
    
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
