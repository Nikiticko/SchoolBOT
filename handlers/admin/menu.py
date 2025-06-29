from telebot import types

# Главное меню администратора

def get_admin_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📋 Список заявок", "📚 Редактировать курсы")
    markup.row("📝 Управление уроками")
    markup.add("📨 Обращения пользователей", "⭐ Отзывы")
    markup.add("⬇️ Выгрузить данные")
    return markup

# Инлайн-меню для администратора

def create_admin_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
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
    markup.add(
        types.InlineKeyboardButton("🔧 Миграция БД", callback_data="admin_migrate_db")
    )
    return markup

# Меню управления уроками (на месте клавиатуры)

def get_lesson_management_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📅 Посмотреть запланированные уроки")
    markup.row("✅ Завершить заявку", "❌ Отменить заявку")
    markup.row("🚫 Отменить урок", "🕓 Перенести урок")
    markup.add("🔙 Назад в админ-меню")
    return markup

# Кнопка подтверждения для опасных операций

def create_confirm_menu(action_type):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Да, подтверждаю", callback_data=f"confirm_{action_type}"),
        types.InlineKeyboardButton("❌ Отмена", callback_data="cancel_action")
    )
    return markup

# Кнопка отмены

def get_cancel_button():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("🔙 Отмена")
    return markup 