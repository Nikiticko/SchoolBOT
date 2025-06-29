from telebot import types
from data.db import get_all_reviews, clear_reviews, get_review_stats
from config import ADMIN_ID
from utils.security_logger import security_logger

def register_reviews_handlers(bot, logger):
    def is_admin(user_id):
        return str(user_id) == str(ADMIN_ID)

    @bot.message_handler(commands=["ClearReviews"])
    def handle_clear_reviews_command(message):
        if not is_admin(message.from_user.id):
            security_logger.log_failed_login(
                message.from_user.id, 
                message.from_user.username or "unknown", 
                "Unauthorized access to admin command ClearReviews"
            )
            logger.warning(f"User {message.from_user.id} tried to access admin command ClearReviews")
            return
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Да, очистить отзывы", callback_data="confirm_clear_reviews"),
            types.InlineKeyboardButton("❌ Нет", callback_data="cancel_clear_reviews")
        )
        bot.send_message(message.chat.id, "⚠️ Вы уверены, что хотите удалить все отзывы?\nЭто действие необратимо.", reply_markup=markup)
        logger.info(f"Admin {message.from_user.id} initiated ClearReviews")

    @bot.callback_query_handler(func=lambda c: c.data in ["confirm_clear_reviews", "cancel_clear_reviews"])
    def handle_clear_reviews_confirm(call):
        if not is_admin(call.from_user.id):
            security_logger.log_unauthorized_access(
                call.from_user.id,
                call.from_user.username or "unknown",
                "admin_reviews_clear",
                call.data
            )
            logger.warning(f"User {call.from_user.id} tried to confirm reviews clear without admin rights")
            return
        if call.data == "confirm_clear_reviews":
            try:
                clear_reviews()
                bot.send_message(call.message.chat.id, "🧹 Отзывы успешно очищены.")
                logger.info(f"Admin {call.from_user.id} cleared reviews")
            except Exception as e:
                bot.send_message(call.message.chat.id, "❌ Ошибка при очистке отзывов. Попробуйте позже.")
                logger.error(f"Error clearing reviews: {e}")
        else:
            bot.send_message(call.message.chat.id, "❌ Очистка отзывов отменена.")
            logger.info(f"Admin {call.from_user.id} cancelled reviews clear") 