from telebot import types
from data.db import get_all_reviews, clear_reviews, get_review_stats
from config import ADMIN_ID
from utils.security_logger import security_logger

def register_reviews_handlers(bot, logger):
    def is_admin(user_id):
        return str(user_id) == str(ADMIN_ID)

    @bot.message_handler(func=lambda m: m.text == "📊 Статистика отзывов" and str(m.from_user.id) == str(ADMIN_ID))
    def handle_admin_reviews(message):
        stats = get_review_stats()
        if isinstance(stats, dict):
            total = stats.get('total', 0)
            public = stats.get('public', 0)
            anonymous = stats.get('anonymous', 0)
        else:
            # Ожидаем кортеж (total, public, anonymous)
            total, public, anonymous = stats if stats and len(stats) == 3 else (0, 0, 0)

        msg = (
            f"⭐ <b>Статистика отзывов</b>\n\n"
            f"Всего отзывов: <b>{total}</b>\n"
            f"Публичных: <b>{public}</b>\n"
            f"Анонимных: <b>{anonymous}</b>\n\n"
            f"Для очистки отзывов используйте команду /ClearReviews"
        )
        bot.send_message(message.chat.id, msg, parse_mode="HTML")

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

    @bot.message_handler(func=lambda m: m.text == "⭐ Отзывы" and str(m.from_user.id) == str(ADMIN_ID))
    def handle_admin_all_reviews(message):
        reviews = get_all_reviews()
        if not reviews:
            bot.send_message(message.chat.id, "Пока нет отзывов.", parse_mode="HTML")
            return
        msg = "<b>Все отзывы:</b>\n\n"
        for i, review in enumerate(reviews, 1):
            _, rating, feedback, is_anonymous, parent_name, student_name, course, created_at, user_tg_id = review
            author = f"{parent_name} ({student_name})" if parent_name and student_name else "[Заявка удалена]"
            course_display = course or "[Курс не указан]"
            anonymity = "Анонимно" if is_anonymous else "Публично"
            msg += (
                f"{i}. ⭐ {rating}/10 | {anonymity}\n"
                f"Курс: {course_display}\n"
                f"Автор: {author}\n"
                f"Текст: {feedback[:100]}{'...' if len(feedback) > 100 else ''}\n"
                f"Дата: {created_at}\n\n"
            )
        bot.send_message(message.chat.id, msg, parse_mode="HTML")

 