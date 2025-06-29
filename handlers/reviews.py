import threading
import time
from telebot import types
from data.db import (
    add_review, get_reviews_for_publication_with_deleted, get_all_reviews, 
    get_review_stats, has_user_reviewed_application
)
from utils.menu import get_main_menu, get_appropriate_menu
from utils.logger import log_error, log_user_action
from utils.decorators import error_handler, ensure_text_message, ensure_stage

# Словарь для хранения состояния пользователей при оставлении отзывов
review_states = {}

def register(bot, logger):
    """Регистрация обработчиков отзывов"""
    
    def send_review_request(bot, user_tg_id, application_id, course_name):
        """Отправляет запрос на отзыв через 30 секунд после завершения урока"""
        def delayed_request():
            time.sleep(30)  # Ждем 30 секунд
            
            # Проверяем, не оставил ли уже пользователь отзыв
            if has_user_reviewed_application(application_id, user_tg_id):
                return
            
            try:
                msg = (
                    f"🎉 Спасибо за участие в уроке!\n\n"
                    f"📘 Курс: {course_name}\n\n"
                    f"Пожалуйста, поделитесь своими впечатлениями о занятии. "
                    f"Ваш отзыв поможет нам стать лучше! 🌟"
                )
                
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("⭐ Оставить отзыв", callback_data=f"start_review:{application_id}"),
                    types.InlineKeyboardButton("❌ Пропустить", callback_data="skip_review")
                )
                
                bot.send_message(user_tg_id, msg, reply_markup=markup)
                logger.info(f"Review request sent to user {user_tg_id} for application {application_id}")
                
            except Exception as e:
                log_error(logger, e, f"Sending review request to user {user_tg_id}")
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=delayed_request, daemon=True)
        thread.start()
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("start_review:"))
    def handle_start_review(call):
        """Начинает процесс оставления отзывов"""
        try:
            application_id = int(call.data.split(":")[1])
            user_tg_id = str(call.message.chat.id)
            
            # Проверяем, не оставил ли уже отзыв
            if has_user_reviewed_application(application_id, user_tg_id):
                bot.send_message(call.message.chat.id, "Вы уже оставили отзыв на этот урок.", reply_markup=get_appropriate_menu(call.from_user.id))
                return
            
            # Сохраняем состояние
            review_states[user_tg_id] = {
                "application_id": application_id,
                "stage": "rating"
            }
            
            msg = (
                "📊 Оцените, пожалуйста, как прошло занятие по шкале от 1 до 10:\n\n"
                "1️⃣ - Очень плохо\n"
                "5️⃣ - Нормально\n"
                "🔟 - Отлично!\n\n"
                "Выберите оценку:"
            )
            
            markup = types.InlineKeyboardMarkup(row_width=5)
            buttons = []
            for i in range(1, 11):
                buttons.append(types.InlineKeyboardButton(str(i), callback_data=f"rating:{i}"))
            markup.add(*buttons)
            markup.add(types.InlineKeyboardButton("🔙 Отмена", callback_data="cancel_review"))
            
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup)
            log_user_action(logger, call.from_user.id, "started_review", f"application_id: {application_id}")
            
        except Exception as e:
            log_error(logger, e, f"Starting review for user {call.from_user.id}")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("rating:"))
    def handle_rating(call):
        """Обрабатывает выбор рейтинга"""
        try:
            rating = int(call.data.split(":")[1])
            user_tg_id = str(call.message.chat.id)
            
            if user_tg_id not in review_states:
                bot.send_message(call.message.chat.id, "Сессия отзыва истекла. Попробуйте снова.", reply_markup=get_appropriate_menu(call.from_user.id))
                return
            
            review_states[user_tg_id]["rating"] = rating
            review_states[user_tg_id]["stage"] = "feedback"
            
            msg = (
                f"✅ Оценка {rating}/10 сохранена!\n\n"
                "📝 Теперь поделитесь своими впечатлениями о занятии:\n"
                "• Что понравилось?\n"
                "• Что можно улучшить?\n"
                "• Общие впечатления\n\n"
                "Напишите ваш отзыв или нажмите «Пропустить текст»:"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Отмена", callback_data="cancel_review"))
            markup.add(types.InlineKeyboardButton("⏭️ Пропустить текст", callback_data="skip_feedback"))
            
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup)
            
        except Exception as e:
            log_error(logger, e, f"Handling rating for user {call.from_user.id}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "skip_feedback")
    def handle_skip_feedback(call):
        """Обрабатывает пропуск текстового отзыва"""
        try:
            user_tg_id = str(call.message.chat.id)
            
            if user_tg_id not in review_states:
                bot.send_message(call.message.chat.id, "Сессия отзыва истекла. Попробуйте снова.", reply_markup=get_appropriate_menu(call.from_user.id))
                return
            
            # Устанавливаем пустой текст отзыва
            review_states[user_tg_id]["feedback"] = ""
            review_states[user_tg_id]["stage"] = "anonymity"
            
            msg = (
                "📝 Ваш отзыв:\n\n"
                "⭐ Только оценка (без текста)\n\n"
                "🔒 Хотите ли вы, чтобы ваш отзыв был анонимным?\n\n"
                "• Если выберите «Публичный», ваш отзыв может быть показан другим пользователям\n"
                "• Если выберите «Анонимный», отзыв будет виден только администратору"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("🌐 Публичный отзыв", callback_data="anonymity:public"),
                types.InlineKeyboardButton("🔒 Анонимный отзыв", callback_data="anonymity:anonymous")
            )
            markup.add(types.InlineKeyboardButton("🔙 Отмена", callback_data="cancel_review"))
            
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup)
            
        except Exception as e:
            log_error(logger, e, f"Handling skip feedback for user {call.from_user.id}")
    
    @bot.message_handler(func=lambda m: m.text and str(m.chat.id) in review_states and review_states[str(m.chat.id)].get("stage") == "feedback")
    @ensure_text_message
    @ensure_stage(lambda m: review_states.get(str(m.chat.id), {}).get("stage"), "feedback", error_message="Сначала выберите оценку занятия.")
    def handle_feedback_text(message):
        """Обрабатывает текстовый отзыв"""
        try:
            user_tg_id = str(message.chat.id)
            feedback = message.text.strip()
            
            if len(feedback) < 10:
                bot.send_message(message.chat.id, "Пожалуйста, напишите более подробный отзыв (минимум 10 символов).")
                return
            
            review_states[user_tg_id]["feedback"] = feedback
            review_states[user_tg_id]["stage"] = "anonymity"
            
            msg = (
                f"📝 Ваш отзыв:\n\n{feedback}\n\n"
                "🔒 Хотите ли вы, чтобы ваш отзыв был анонимным?\n\n"
                "• Если выберите «Публичный», ваш отзыв может быть показан другим пользователям\n"
                "• Если выберите «Анонимный», отзыв будет виден только администратору"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("🌐 Публичный отзыв", callback_data="anonymity:public"),
                types.InlineKeyboardButton("🔒 Анонимный отзыв", callback_data="anonymity:anonymous")
            )
            markup.add(types.InlineKeyboardButton("🔙 Отмена", callback_data="cancel_review"))
            
            bot.send_message(message.chat.id, msg, reply_markup=markup)
            
        except Exception as e:
            log_error(logger, e, f"Handling feedback text for user {message.from_user.id}")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("anonymity:"))
    def handle_anonymity_choice(call):
        """Обрабатывает выбор анонимности"""
        try:
            anonymity = call.data.split(":")[1]
            user_tg_id = str(call.message.chat.id)
            
            if user_tg_id not in review_states:
                bot.send_message(call.message.chat.id, "Сессия отзыва истекла. Попробуйте снова.", reply_markup=get_appropriate_menu(call.from_user.id))
                return
            
            is_anonymous = (anonymity == "anonymous")
            review_data = review_states[user_tg_id]
            
            # Сохраняем отзыв
            review_id = add_review(
                application_id=review_data["application_id"],
                user_tg_id=user_tg_id,
                rating=review_data["rating"],
                feedback=review_data["feedback"],
                is_anonymous=is_anonymous
            )
            if not review_id:
                bot.send_message(call.message.chat.id, "❌ Не удалось сохранить отзыв. Попробуйте позже.", reply_markup=get_appropriate_menu(call.from_user.id))
                logger.error(f"Failed to add review for user {user_tg_id}, application {review_data['application_id']}")
                return
            
            # Очищаем состояние
            review_states.pop(user_tg_id, None)
            
            msg = (
                "🎉 Спасибо за ваш отзыв!\n\n"
                f"⭐ Оценка: {review_data['rating']}/10\n"
                f"📝 Отзыв: {'Анонимный' if is_anonymous else 'Публичный'}\n\n"
                "Ваше мнение очень важно для нас! 🙏"
            )
            
            bot.send_message(call.message.chat.id, msg, reply_markup=get_appropriate_menu(call.from_user.id))
            log_user_action(logger, call.from_user.id, "submitted_review", f"rating: {review_data['rating']}, anonymous: {is_anonymous}")
            
        except Exception as e:
            log_error(logger, e, f"Handling anonymity choice for user {call.from_user.id}")
    
    @bot.callback_query_handler(func=lambda call: call.data in ["skip_review", "cancel_review"])
    def handle_skip_or_cancel_review(call):
        """Обрабатывает пропуск или отмену отзыва"""
        try:
            user_tg_id = str(call.message.chat.id)
            
            # Очищаем состояние
            review_states.pop(user_tg_id, None)
            
            if call.data == "skip_review":
                msg = "Понятно! Если захотите поделиться впечатлениями позже, просто напишите нам. 😊"
            else:
                msg = "Отзыв отменён. Спасибо за участие в уроке! 🙏"
            
            bot.send_message(call.message.chat.id, msg, reply_markup=get_appropriate_menu(call.from_user.id))
            log_user_action(logger, call.from_user.id, "skipped_review" if call.data == "skip_review" else "cancelled_review")
            
        except Exception as e:
            log_error(logger, e, f"Handling skip/cancel review for user {call.from_user.id}")
    
    @bot.message_handler(func=lambda m: m.text == "⭐ Отзывы")
    def handle_show_reviews(message):
        """Показывает публичные отзывы"""
        try:
            reviews = get_reviews_for_publication_with_deleted(limit=5)
            
            if not reviews:
                bot.send_message(message.chat.id, "Пока нет отзывов. Будьте первым! 😊", reply_markup=get_appropriate_menu(message.from_user.id))
                return
            
            msg = "⭐ Отзывы наших учеников:\n\n"
            
            for i, review in enumerate(reviews, 1):
                rating, feedback, is_anonymous, parent_name, student_name, course, created_at = review
                
                # Форматируем дату
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(created_at)
                    date_str = dt.strftime("%d.%m.%Y")
                except:
                    date_str = "недавно"
                
                stars = "⭐" * rating
                
                # Обрабатываем случай с удаленной заявкой
                if parent_name is None and student_name is None:
                    author = "[Заявка удалена]"
                    course_display = "[Заявка удалена]"
                else:
                    author = f"{parent_name} ({student_name})"
                    course_display = course or "[Курс не указан]"
                
                msg += (
                    f"{i}. {stars} ({rating}/10)\n"
                    f"📘 Курс: {course_display}\n"
                    f"👤 {author}\n"
                    f"📝 {feedback[:100]}{'...' if len(feedback) > 100 else ''}\n"
                    f"📅 {date_str}\n\n"
                )
            
            msg += "💬 Хотите оставить свой отзыв? Напишите нам!"
            
            bot.send_message(message.chat.id, msg, reply_markup=get_appropriate_menu(message.from_user.id))
            log_user_action(logger, message.from_user.id, "viewed_reviews")
            
        except Exception as e:
            log_error(logger, e, f"Showing reviews for user {message.from_user.id}")
    
    return send_review_request 