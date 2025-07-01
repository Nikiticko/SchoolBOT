from telebot import types
from data.db import get_all_archive, clear_archive, format_date_for_display
from config import ADMIN_ID
from utils.security_logger import security_logger
from utils.menu import is_admin

def register_archive_handlers(bot, logger):
    @bot.message_handler(commands=["ClearArchive"])
    def handle_clear_archive_command(message):
        if not is_admin(message.from_user.id):
            security_logger.log_failed_login(
                message.from_user.id, 
                message.from_user.username or "unknown", 
                "Unauthorized access to admin command ClearArchive"
            )
            logger.warning(f"User {message.from_user.id} tried to access admin command ClearArchive")
            return
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Да, очистить архив", callback_data="confirm_clear_archive"),
            types.InlineKeyboardButton("❌ Нет", callback_data="cancel_clear_archive")
        )
        bot.send_message(
            message.chat.id,
            "⚠️ Вы уверены, что хотите удалить все архивные заявки?\nЭто действие необратимо.",
            reply_markup=markup
        )
        logger.info(f"Admin {message.from_user.id} initiated ClearArchive")

    @bot.callback_query_handler(func=lambda c: c.data in ["confirm_clear_archive", "cancel_clear_archive"])
    def handle_clear_archive_confirm(call):
        if not is_admin(call.from_user.id):
            security_logger.log_unauthorized_access(
                call.from_user.id,
                call.from_user.username or "unknown",
                "admin_archive_clear",
                call.data
            )
            logger.warning(f"User {call.from_user.id} tried to confirm archive clear without admin rights")
            return
        if call.data == "confirm_clear_archive":
            try:
                clear_archive()
                bot.send_message(call.message.chat.id, "🧹 Архив успешно очищен.")
                logger.info(f"Admin {call.from_user.id} cleared archive")
            except Exception as e:
                bot.send_message(call.message.chat.id, "❌ Ошибка при очистке архива. Попробуйте позже.")
                logger.error(f"Error clearing archive: {e}")
        else:
            bot.send_message(call.message.chat.id, "❌ Очистка архива отменена.")
            logger.info(f"Admin {call.from_user.id} cancelled archive clear") 