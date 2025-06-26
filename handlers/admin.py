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
    get_all_archive,
    get_open_contacts,
    reply_to_contact,
    get_contact_by_id,
    ban_user_by_contact
)
from state.users import writing_ids
from data.db import clear_archive
from utils.menu import get_admin_menu, get_cancel_button, handle_cancel_action
import openpyxl
from openpyxl.utils import get_column_letter
import tempfile
import os
import re


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
                # Статус заявки
                if status == "Назначено":
                    status_str = "Назначено"
                else:
                    status_str = "Ожидает"
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
        markup.add("👁 Просмотреть все курсы")
        markup.add("📨 Обращения пользователей")
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
            # Формируем строки с вычисленным статусом
            rows = []
            for row in data:
                app_id, tg_id, parent_name, student_name, age, contact, course, lesson_date, lesson_link, status, created_at = row
                if status == "Назначено":
                    status_str = "Назначено"
                else:
                    status_str = "Ожидает"
                rows.append([
                    app_id, tg_id, parent_name, student_name, age, contact, course,
                    lesson_date, lesson_link, status_str, created_at
                ])
        else:
            data = get_all_archive()
            filename = "archive_export.xlsx"
            headers = [
                "ID", "TG ID", "Родитель", "Ученик", "Возраст", "Контакт", "Курс",
                "Дата урока", "Ссылка", "Статус", "Создано", "Кем отменено", "Комментарий"
            ]
            rows = data
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(headers)
        for row in rows:
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

    @bot.message_handler(func=lambda m: m.text == "📨 Обращения пользователей" and is_admin(m.from_user.id))
    def handle_contacts_menu(message):
        contacts = get_open_contacts()
        if not contacts:
            bot.send_message(message.chat.id, "✅ Нет новых обращений.", reply_markup=get_admin_menu())
            return
        for c in contacts:
            contact_id, user_tg_id, user_contact, msg, admin_reply, status, created_at, reply_at, banned = c
            # Проверяем, есть ли вложение
            file_match = re.match(r"\[Вложение: (\w+), file_id: ([\w\-_]+)\](.*)", msg, re.DOTALL)
            if file_match:
                file_type, file_id, caption = file_match.groups()
                caption = caption.strip() or None
                if file_type == 'photo':
                    bot.send_photo(message.chat.id, file_id, caption=f"Обращение #{contact_id} от {user_contact}\n{caption or ''}")
                elif file_type == 'document':
                    bot.send_document(message.chat.id, file_id, caption=f"Обращение #{contact_id} от {user_contact}\n{caption or ''}")
                elif file_type == 'voice':
                    bot.send_voice(message.chat.id, file_id)
                elif file_type == 'video':
                    bot.send_video(message.chat.id, file_id, caption=f"Обращение #{contact_id} от {user_contact}\n{caption or ''}")
                elif file_type == 'video_note':
                    bot.send_video_note(message.chat.id, file_id)
                # Текстовое описание
                text = (
                    f"🆘 Обращение #{contact_id}\n"
                    f"👤 Пользователь: {user_contact} (ID: {user_tg_id})\n"
                    f"⏰ Время: {created_at}\n"
                    f"Статус: {status}\n"
                    f"\nТекст: (см. вложение выше)"
                )
            else:
                text = (
                    f"🆘 Обращение #{contact_id}\n"
                    f"👤 Пользователь: {user_contact} (ID: {user_tg_id})\n"
                    f"⏰ Время: {created_at}\n"
                    f"Статус: {status}\n"
                    f"\nТекст: {msg}"
                )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✉️ Ответить", callback_data=f"reply_contact:{contact_id}"))
            markup.add(types.InlineKeyboardButton("🚫 Забанить", callback_data=f"ban_contact:{user_tg_id}"))
            bot.send_message(message.chat.id, text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("reply_contact:"))
    def handle_reply_contact(call):
        contact_id = int(call.data.split(":")[1])
        bot.send_message(call.message.chat.id, "✍️ Введите ответ пользователю:", reply_markup=get_cancel_button())
        bot.register_next_step_handler(call.message, lambda m: process_admin_reply(m, contact_id))

    def process_admin_reply(message, contact_id):
        if message.text == "🔙 Отмена":
            bot.send_message(message.chat.id, "Ответ отменён.", reply_markup=get_admin_menu())
            return
        reply_to_contact(contact_id, message.text)
        contact = get_contact_by_id(contact_id)
        user_tg_id = contact[1]
        bot.send_message(message.chat.id, "✅ Ответ отправлен пользователю.", reply_markup=get_admin_menu())
        bot.send_message(int(user_tg_id), f"📨 Ответ от администратора:\n\n{message.text}")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("ban_contact:"))
    def handle_ban_contact(call):
        user_tg_id = call.data.split(":")[1]
        ban_user_by_contact(user_tg_id)
        bot.send_message(call.message.chat.id, f"Пользователь {user_tg_id} заблокирован для обращений.", reply_markup=get_admin_menu())

    @bot.message_handler(commands=["ClearContacts"])
    def handle_clear_contacts(message):
        if not is_admin(message.from_user.id):
            logger.warning(f"User {message.from_user.id} tried to access admin command ClearContacts")
            return
        from data.db import clear_contacts
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Да, очистить обращения", callback_data="confirm_clear_contacts"),
            types.InlineKeyboardButton("❌ Нет", callback_data="cancel_clear_contacts")
        )
        bot.send_message(message.chat.id, "⚠️ Вы уверены, что хотите удалить все обращения пользователей? Это действие необратимо.", reply_markup=markup)
        logger.info(f"Admin {message.from_user.id} initiated ClearContacts")

    @bot.callback_query_handler(func=lambda c: c.data in ["confirm_clear_contacts", "cancel_clear_contacts"])
    def handle_clear_contacts_confirm(call):
        if not is_admin(call.from_user.id):
            logger.warning(f"User {call.from_user.id} tried to confirm clear contacts without admin rights")
            return
        from data.db import clear_contacts
        if call.data == "confirm_clear_contacts":
            clear_contacts()
            bot.send_message(call.message.chat.id, "🧹 Все обращения пользователей успешно удалены.")
            logger.info(f"Admin {call.from_user.id} cleared all contacts")
        else:
            bot.send_message(call.message.chat.id, "❌ Очистка обращений отменена.")
            logger.info(f"Admin {call.from_user.id} cancelled clear contacts")
