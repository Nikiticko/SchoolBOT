from telebot import types
from utils.security_logger import security_logger
from config import ADMIN_ID
import os
from datetime import datetime
from utils.menu import is_admin

def register_security_handlers(bot, logger):
    @bot.message_handler(commands=["security_report"])
    def handle_security_report(message):
        if not is_admin(message.from_user.id):
            security_logger.log_failed_login(
                message.from_user.id, 
                message.from_user.username or "unknown", 
                "Unauthorized access to admin command security_report"
            )
            logger.warning(f"User {message.from_user.id} tried to access admin command security_report")
            return
        try:
            report = security_logger.get_security_report(hours=24)
            report_text = (
                "🔒 Отчет по безопасности (за последние 24 часа):\n\n"
                f"🚫 Неудачные попытки входа: {report.get('failed_logins', 0)}\n"
                f"⚠️ Подозрительная активность: {report.get('suspicious_activities', 0)}\n"
                f"⏱️ Превышения rate limit: {report.get('rate_limit_exceeded', 0)}\n"
                f"🚫 Заблокированные пользователи: {report.get('user_bans', 0)}\n"
                f"🚪 Несанкционированный доступ: {report.get('unauthorized_access', 0)}\n"
                f"❌ Ошибки валидации: {report.get('input_validation_failed', 0)}\n\n"
                "📊 Общая статистика безопасности:"
            )
            total_events = sum(report.values())
            threat_level = None
            if total_events == 0:
                report_text += "\n✅ Все спокойно, угроз не обнаружено"
                threat_level = "none"
            elif total_events < 10:
                report_text += "\n🟡 Низкий уровень угроз"
                threat_level = "low"
            elif total_events < 50:
                report_text += "\n🟠 Средний уровень угроз"
                threat_level = "medium"
            else:
                report_text += "\n🔴 Высокий уровень угроз!"
                threat_level = "high"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("⬇️ Выгрузить отчет (XLS)", callback_data="export_security_log"))
            bot.send_message(message.chat.id, report_text, reply_markup=markup)
            logger.info(f"Admin {message.from_user.id} requested security report")
            security_logger.log_admin_action(
                message.from_user.id,
                message.from_user.username or "unknown",
                "security_report_requested"
            )
            # Уведомление админу о среднем/высоком уровне угроз
            if threat_level in ("medium", "high"):
                try:
                    bot.send_message(ADMIN_ID, f"⚠️ Внимание! В системе зафиксирован {('средний' if threat_level=='medium' else 'высокий')} уровень угроз безопасности за последние 24 часа.")
                except Exception as notify_err:
                    logger.error(f"Не удалось отправить уведомление админу: {notify_err}")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка при получении отчета безопасности: {str(e)}")
            logger.error(f"Error in security report: {e}")

    @bot.callback_query_handler(func=lambda c: c.data == "export_security_log")
    def handle_export_security_log(call):
        if not is_admin(call.from_user.id):
            security_logger.log_failed_login(
                call.from_user.id,
                call.from_user.username or "unknown",
                "Unauthorized export_security_log"
            )
            bot.answer_callback_query(call.id, "Нет прав")
            return
        try:
            filename = f"security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = os.path.join(os.getcwd(), filename)
            count = security_logger.export_security_log_to_xls(filepath, hours=24)
            if count == 0:
                bot.send_message(call.message.chat.id, "Нет событий для выгрузки за последние 24 часа.")
            else:
                with open(filepath, "rb") as f:
                    caption = f"🔒 Отчет безопасности ({count} событий)\n\n⚠️ <b>Внимание:</b> Файл будет автоматически удален через 24 часа\n💾 Сохраните его, если он вам нужен надолго"
                    bot.send_document(call.message.chat.id, f, caption=caption, parse_mode="HTML")
                os.remove(filepath)
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ Ошибка при выгрузке отчета: {str(e)}") 