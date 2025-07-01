# Здесь будут импортироваться и регистрироваться все админские хендлеры после рефакторинга 

from .security import register_security_handlers
from .applications import register_applications_handlers
from .archive import register_archive_handlers
from .courses import register_courses_handlers
from .contacts import register_contacts_handlers
from .reviews import register_reviews_handlers
from utils.menu import get_admin_menu, create_confirm_menu, get_cancel_button, is_admin
from .export import register_export_handlers
from config import ADMIN_ID

def register_all_admin_handlers(bot, logger):
    """Регистрирует все админские обработчики"""
    
    # Обработчик для команды /admin
    @bot.message_handler(commands=['admin'])
    def handle_admin_command(message):
        if not is_admin(message.from_user.id):
            logger.warning(f"User {message.from_user.id} tried to access admin command")
            return
        bot.send_message(message.chat.id, "🔧 Панель администратора", reply_markup=get_admin_menu())
        logger.info(f"Admin {message.from_user.id} accessed admin panel")
    
    # Обработчик для /start только для админа
    @bot.message_handler(commands=['start'], func=lambda m: str(m.from_user.id) == str(ADMIN_ID))
    def handle_start_command(message):
        logger.info(f"Start command received from user {message.from_user.id} (admin check: {is_admin(message.from_user.id)})")
        bot.send_message(message.chat.id, "🔧 Добро пожаловать в панель администратора!", reply_markup=get_admin_menu())
        logger.info(f"Admin {message.from_user.id} started bot successfully")
    
    # Регистрируем все остальные админские обработчики
    register_security_handlers(bot, logger)
    register_applications_handlers(bot, logger)
    register_archive_handlers(bot, logger)
    register_courses_handlers(bot, logger)
    register_contacts_handlers(bot, logger)
    register_reviews_handlers(bot, logger)
    register_export_handlers(bot, logger)
    # Здесь будут регистрироваться остальные админские хендлеры (export, menu) 