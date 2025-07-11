from telebot import types
from data.db import get_pending_applications, clear_applications, update_application_lesson, get_application_by_id, format_date_for_display
from utils.menu import get_admin_menu, is_admin
from config import ADMIN_ID
from utils.security_logger import security_logger
from handlers.admin_actions import register_admin_actions

def register_applications_handlers(bot, logger):
    @bot.message_handler(commands=["ClearApplications"])
    def handle_clear_command(message):
        if not is_admin(message.from_user.id):
            security_logger.log_failed_login(
                message.from_user.id, 
                message.from_user.username or "unknown", 
                "Unauthorized access to admin command ClearApplications"
            )
            logger.warning(f"User {message.from_user.id} tried to access admin command ClearApplications")
            return
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Да, очистить", callback_data="confirm_clear"),
            types.InlineKeyboardButton("❌ Нет", callback_data="cancel_clear")
        )
        bot.send_message(message.chat.id, "⚠️ Вы уверены, что хотите удалить все заявки?\nЭто действие необратимо.", reply_markup=markup)
        logger.info(f"Admin {message.from_user.id} initiated ClearApplications")

    @bot.callback_query_handler(func=lambda call: call.data in ["confirm_clear", "cancel_clear"])
    def handle_clear_confirm(call):
        chat_id = call.message.chat.id
        if not is_admin(call.from_user.id):
            security_logger.log_unauthorized_access(
                call.from_user.id,
                call.from_user.username or "unknown",
                "admin_applications_clear",
                call.data
            )
            logger.warning(f"User {call.from_user.id} tried to confirm clear without admin rights")
            return
        if call.data == "confirm_clear":
            try:
                clear_applications()
                bot.send_message(chat_id, "✅ Все заявки успешно удалены.")
                logger.info(f"Admin {call.from_user.id} cleared all applications")
            except Exception as e:
                bot.send_message(chat_id, "❌ Ошибка при очистке заявок. Попробуйте позже.")
                logger.error(f"Error clearing applications: {e}")
        else:
            bot.send_message(chat_id, "❌ Очистка отменена.")
            logger.info(f"Admin {call.from_user.id} cancelled clear")

    @bot.message_handler(func=lambda m: m.text == "📋 Список заявок" and is_admin(m.from_user.id))
    def handle_pending_applications(message):
        import time
        start_time = time.time()
        
        applications = get_pending_applications()
        if not applications:
            bot.send_message(message.chat.id, "✅ Нет заявок без назначенной даты")
            
            # Логирование админских действий
            logger.info(f"🔧 Admin {message.from_user.id} viewed empty applications list")
            
            # Логирование производительности
            response_time = time.time() - start_time
            logger.info(f"⏱️ Admin handler response time: {response_time:.3f}s (view applications)")
            
            # Бизнес-метрики
            logger.info(f"📊 Admin activity: admin {message.from_user.id} viewed applications (0 pending)")
            return
            
        for app in applications:
            app_id, tg_id, parent_name, student_name, age, contact, course, lesson_date, lesson_link, status, created_at, reminder_sent = app
            formatted_created = format_date_for_display(created_at)
            status_str = "Назначено" if status == "Назначено" else "Ожидает"
            text = (
                f"🆔 Заявка #{app_id}\n"
                f"👤 Родитель: {parent_name}\n"
                f"🧒 Ученик: {student_name}\n"
                f"📞 Контакт: {contact or 'не указан'}\n"
                f"🎂 Возраст: {age}\n"
                f"📘 Курс: {course}\n"
                f"Статус: {status_str}\n"
                f"🕒 Создано: {formatted_created}"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🕒 Назначить", callback_data=f"assign:{app_id}"))
            bot.send_message(message.chat.id, text, reply_markup=markup)
        
        # Логирование админских действий
        logger.info(f"🔧 Admin {message.from_user.id} viewed {len(applications)} pending applications")
        
        # Логирование производительности
        response_time = time.time() - start_time
        logger.info(f"⏱️ Admin handler response time: {response_time:.3f}s (view {len(applications)} applications)")
        
        # Бизнес-метрики
        logger.info(f"📊 Admin activity: admin {message.from_user.id} viewed applications ({len(applications)} pending)")
        
        # Системные события
        logger.info(f"📊 Applications status: {len(applications)} pending applications in system")

    # Регистрируем все хендлеры из admin_actions.py (назначение, завершение, отмена, перенос и т.д.)
    register_admin_actions(bot, logger) 