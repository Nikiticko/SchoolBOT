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
    
    # Обработчик для /start только для админа
    @bot.message_handler(commands=['start'], func=lambda m: str(m.from_user.id) == str(ADMIN_ID))
    def handle_start_command(message):
        import time
        start_time = time.time()
        
        logger.info(f"Start command received from user {message.from_user.id} (admin check: {is_admin(message.from_user.id)})")
        bot.send_message(message.chat.id, "🔧 Добро пожаловать в панель администратора!", reply_markup=get_admin_menu())
        
        # Логирование админских действий
        logger.info(f"🔧 Admin {message.from_user.id} started bot successfully")
        
        # Логирование производительности
        response_time = time.time() - start_time
        logger.info(f"⏱️ Admin handler response time: {response_time:.3f}s (admin start)")
        
        # Бизнес-метрики
        logger.info(f"📊 Admin activity: admin {message.from_user.id} started bot")
    
    # Регистрируем все остальные админские обработчики
    register_security_handlers(bot, logger)
    register_applications_handlers(bot, logger)
    register_archive_handlers(bot, logger)
    register_courses_handlers(bot, logger)
    register_contacts_handlers(bot, logger)
    register_reviews_handlers(bot, logger)
    register_export_handlers(bot, logger)
    # Здесь будут регистрироваться остальные админские хендлеры (export, menu) 