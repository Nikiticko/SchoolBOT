from telebot import types
from config import ADMIN_ID
from data.db import (
    get_pending_applications,
    clear_applications,
    update_application_lesson,
    get_application_by_id,
    format_date_for_display,
    validate_date_format,
    get_all_applications,
    get_all_archive
)
from state.users import writing_ids
from data.db import clear_archive
from utils.menu import get_admin_menu, get_cancel_button, handle_cancel_action
import openpyxl
from openpyxl.utils import get_column_letter
import tempfile
import os


def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

def notify_admin_new_application(bot, application_data):
    try:
        notification = (
            "🔔 Новая заявка на обучение!\n\n"
            f"👤 Имя: {application_data.get('parent_name', 'Не указано')}\n"
            f"🧒 Ученик: {application_data.get('student_name', 'Не указано')}\n"
            f"📱 Контакт: {application_data.get('contact', 'Не указан')}\n"
            f"📚 Курс: {application_data.get('course', 'Не указан')}\n"
            f"📅 Возраст: {application_data.get('age', 'Не указан')}"
        )
        bot.send_message(ADMIN_ID, notification)
        print(f"[✅] Уведомление отправлено админу {ADMIN_ID}")
    except Exception as e:
        print(f"[❌] Ошибка при отправке уведомления админу: {str(e)}")


def register(bot, logger):
    @bot.message_handler(commands=["ClearApplications"])
    def handle_clear_command(message):
        if not is_admin(message.from_user.id):
            logger.warning(f"User {message.from_user.id} tried to access admin command ClearApplications")
            return
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Да, очистить", callback_data="confirm_clear"),
            types.InlineKeyboardButton("❌ Нет", callback_data="cancel_clear")
        )
        bot.send_message(message.chat.id, "⚠️ Вы уверены, что хотите удалить все заявки?\nЭто действие необратимо.", reply_markup=markup)
        logger.info(f"Admin {message.from_user.id} initiated ClearApplications")

    @bot.message_handler(commands=["ClearArchive"])
    def handle_clear_archive_command(message):
        if not is_admin(message.from_user.id):
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
            logger.warning(f"User {call.from_user.id} tried to confirm archive clear without admin rights")
            return

        if call.data == "confirm_clear_archive":
            clear_archive()
            bot.send_message(call.message.chat.id, "🧹 Архив успешно очищен.")
            logger.info(f"Admin {call.from_user.id} cleared archive")
        else:
            bot.send_message(call.message.chat.id, "❌ Очистка архива отменена.")
            logger.info(f"Admin {call.from_user.id} cancelled archive clear")

    @bot.callback_query_handler(func=lambda call: call.data in ["confirm_clear", "cancel_clear"])
    def handle_clear_confirm(call):
        chat_id = call.message.chat.id
        if not is_admin(call.from_user.id):
            logger.warning(f"User {call.from_user.id} tried to confirm clear without admin rights")
            return

        if call.data == "confirm_clear":
            clear_applications()
            bot.send_message(chat_id, "✅ Все заявки успешно удалены.")
            logger.info(f"Admin {call.from_user.id} cleared all applications")
        else:
            bot.send_message(chat_id, "❌ Очистка отменена.")
            logger.info(f"Admin {call.from_user.id} cancelled clear")

    @bot.message_handler(func=lambda m: m.text == "📋 Список заявок" and is_admin(m.from_user.id))
    def handle_pending_applications(message):
        try:
            applications = get_pending_applications()
            if not applications:
                bot.send_message(message.chat.id, "✅ Нет заявок без назначенной даты")
                return

            for app in applications:
                app_id, tg_id, parent_name, student_name, age, contact, course, lesson_date, lesson_link, status, created_at = app
                formatted_created = format_date_for_display(created_at)
                text = (
                    f"🆔 Заявка #{app_id}\n"
                    f"👤 Родитель: {parent_name}\n"
                    f"🧒 Ученик: {student_name}\n"
                    f"📞 Контакт: {contact or 'не указан'}\n"
                    f"🎂 Возраст: {age}\n"
                    f"📘 Курс: {course}\n"
                    f"📅 Статус: {status}\n"
                    f"🕒 Создано: {formatted_created}"
                )
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🕒 Назначить", callback_data=f"assign:{app_id}"))
                bot.send_message(message.chat.id, text, reply_markup=markup)
            logger.info(f"Admin {message.from_user.id} viewed pending applications")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка при получении заявок: {str(e)}")
            logger.error(f"Error in handle_pending_applications: {e}")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("assign:"))
    def handle_assign_callback(call):
        app_id = int(call.data.split(":")[1])
        writing_ids.add(call.from_user.id)
        bot.send_message(call.message.chat.id, f"📅 Введите дату и время урока для заявки #{app_id} (например: 22.06 17:00):", reply_markup=get_cancel_button())
        bot.register_next_step_handler(call.message, lambda m: get_link(m, app_id))

    def get_link(message, app_id):
        if message.from_user.id not in writing_ids:
            return
        
        # Проверяем отмену
        if message.text == "🔙 Отмена":
            writing_ids.discard(message.from_user.id)
            handle_cancel_action(bot, message, "урок", logger)
            return
        
        date_text = message.text.strip()
        
        # Валидируем дату
        is_valid, result = validate_date_format(date_text)
        
        if not is_valid:
            bot.send_message(
                message.chat.id, 
                f"❌ {result}\n\n📅 Попробуйте еще раз в формате ДД.ММ ЧЧ:ММ (например: 22.06 17:00):",
                reply_markup=get_cancel_button()
            )
            bot.register_next_step_handler(message, lambda m: get_link(m, app_id))
            return
        
        # Сохраняем валидную дату
        user_data = getattr(message, '_user_data', {})
        user_data['valid_date'] = result
        message._user_data = user_data
        
        bot.send_message(message.chat.id, "🔗 Введите ссылку на урок:", reply_markup=get_cancel_button())
        bot.register_next_step_handler(message, lambda m: finalize_lesson(m, app_id, date_text))

    def finalize_lesson(message, app_id, date_text):
        if message.from_user.id not in writing_ids:
            return
        
        # Проверяем отмену
        if message.text == "🔙 Отмена":
            writing_ids.discard(message.from_user.id)
            handle_cancel_action(bot, message, "урок", logger)
            return
        
        link = message.text.strip()
        
        # Получаем валидированную дату
        user_data = getattr(message, '_user_data', {})
        valid_date = user_data.get('valid_date')
        
        if valid_date:
            # Используем валидированную дату (datetime объект)
            update_application_lesson(app_id, valid_date, link)
            formatted_date = format_date_for_display(valid_date)
        else:
            # Fallback - используем строку и надеемся на лучшее
            update_application_lesson(app_id, date_text, link)
            formatted_date = date_text
        
        bot.send_message(message.chat.id, f"✅ Урок назначен!\n📅 {formatted_date}\n🔗 {link}", reply_markup=get_admin_menu())

        app = get_application_by_id(app_id)
        if app:
            tg_id = app[1]
            course = app[6]
            try:
                bot.send_message(
                    int(tg_id),
                    f"📅 Вам назначен урок!\n📘 Курс: {course}\n🗓 Дата: {formatted_date}\n🔗 Ссылка: {link}"
                )
                logger.info(f"Lesson notification sent to user {tg_id}")
            except Exception as e:
                logger.error(f"Failed to notify user {tg_id}: {e}")

        writing_ids.discard(message.from_user.id)
        logger.info(f"Admin {message.from_user.id} assigned lesson for application {app_id}")

    @bot.message_handler(func=lambda m: m.text == "📚 Редактировать курсы" and is_admin(m.from_user.id))
    def handle_course_menu(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ Добавить курс", "🗑 Удалить курс")
        markup.add("❄ Заморозить курс", "📝 Отредактировать курс")
        markup.add("🔙 Назад")
        bot.send_message(message.chat.id, "🎓 Меню редактирования курсов:", reply_markup=markup)

    @bot.message_handler(func=lambda m: m.text == "⬇️ Выгрузить данные" and is_admin(m.from_user.id))
    def handle_export_data(message):
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("Заявки", callback_data="export_applications"),
            types.InlineKeyboardButton("Архив", callback_data="export_archive")
        )
        bot.send_message(message.chat.id, "Что выгрузить?", reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data in ["export_applications", "export_archive"])
    def handle_export_choice(call):
        if call.data == "export_applications":
            data = get_all_applications()
            filename = "applications_export.xlsx"
            headers = [
                "ID", "TG ID", "Родитель", "Ученик", "Возраст", "Контакт", "Курс",
                "Дата урока", "Ссылка", "Статус", "Создано"
            ]
        else:
            data = get_all_archive()
            filename = "archive_export.xlsx"
            headers = [
                "ID", "TG ID", "Родитель", "Ученик", "Возраст", "Контакт", "Курс",
                "Дата урока", "Ссылка", "Статус", "Создано", "Кем отменено", "Причина отмены"
            ]

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(headers)
        for row in data:
            ws.append(row)
        # Автоширина столбцов
        for col in ws.columns:
            max_length = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            ws.column_dimensions[col_letter].width = max_length + 2
        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            wb.save(tmp.name)
            tmp_path = tmp.name
        with open(tmp_path, "rb") as f:
            bot.send_document(call.message.chat.id, f, visible_file_name=filename)
        os.remove(tmp_path)
        bot.answer_callback_query(call.id, "Выгрузка завершена")
