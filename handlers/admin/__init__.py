# Здесь будут импортироваться и регистрироваться все админские хендлеры после рефакторинга 

from .security import register_security_handlers
from .applications import register_applications_handlers
from .archive import register_archive_handlers
from .courses import register_courses_handlers
from .contacts import register_contacts_handlers
from .reviews import register_reviews_handlers
from .menu import get_admin_menu, create_admin_menu, create_confirm_menu, get_cancel_button
from .export import register_export_handlers

def register_all_admin_handlers(bot, logger):
    register_security_handlers(bot, logger)
    register_applications_handlers(bot, logger)
    register_archive_handlers(bot, logger)
    register_courses_handlers(bot, logger)
    register_contacts_handlers(bot, logger)
    register_reviews_handlers(bot, logger)
    register_export_handlers(bot, logger)
    # Здесь будут регистрироваться остальные админские хендлеры (export, menu) 