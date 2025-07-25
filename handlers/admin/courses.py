from telebot import types
from data.db import get_all_courses, add_course, delete_course, update_course, toggle_course_active
from config import ADMIN_ID
from utils.menu import get_admin_menu, get_cancel_button, handle_cancel_action, get_course_editor_menu, is_admin
from utils.security_logger import security_logger

def register_courses_handlers(bot, logger):
    @bot.message_handler(func=lambda m: m.text == "📚 Редактировать курсы" and is_admin(m.from_user.id))
    def handle_course_menu(message):
        import time
        start_time = time.time()
        
        try:
            bot.send_message(message.chat.id, "🔧 Меню управления курсами", reply_markup=get_course_editor_menu())
            
            # Логирование админских действий
            logger.info(f"🔧 Admin {message.from_user.id} opened course editor menu")
            
            # Логирование производительности
            response_time = time.time() - start_time
            logger.info(f"⏱️ Admin handler response time: {response_time:.3f}s (course editor menu)")
            
            # Бизнес-метрики
            logger.info(f"📊 Admin activity: admin {message.from_user.id} accessed course management")
            
        except Exception as e:
            logger.error(f"Error in handle_course_menu: {e}")

    @bot.message_handler(func=lambda m: m.text == "➕ Добавить курс" and is_admin(m.from_user.id))
    def handle_add_course(message):
        try:
            bot.send_message(message.chat.id, "Введите название нового курса:", reply_markup=get_cancel_button())
            bot.register_next_step_handler(message, lambda m: get_course_name(m, bot))
            logger.info(f"Admin {message.from_user.id} started adding new course")
        except Exception as e:
            logger.error(f"Error in handle_add_course: {e}")

    def get_course_name(message, bot):
        try:
            # Проверяем отмену
            if message.text == "🔙 Отмена":
                handle_cancel_action(bot, message, "курс", logger)
                return
                
            name = message.text.strip()
            bot.send_message(message.chat.id, "Введите описание курса:", reply_markup=get_cancel_button())
            bot.register_next_step_handler(message, lambda m: save_new_course(m, bot, name))
        except Exception as e:
            logger.error(f"Error in get_course_name: {e}")

    def save_new_course(message, bot, name):
        import time
        start_time = time.time()
        
        try:
            # Проверяем отмену
            if message.text == "🔙 Отмена":
                handle_cancel_action(bot, message, "курс", logger)
                return
            desc = message.text.strip()
            try:
                add_course(name, desc)
                bot.send_message(message.chat.id, f"✅ Курс «{name}» добавлен.", reply_markup=get_course_editor_menu())
                
                # Логирование админских действий
                logger.info(f"🔧 Admin {message.from_user.id} added new course: {name}")
                
                # Логирование производительности
                response_time = time.time() - start_time
                logger.info(f"⏱️ Admin handler response time: {response_time:.3f}s (add course)")
                
                # Бизнес-метрики
                logger.info(f"📊 Course management: new course '{name}' added by admin {message.from_user.id}")
                
                # Системные события
                logger.info(f"📊 Course added: '{name}' with description length {len(desc)} characters")
                
            except Exception as e:
                bot.send_message(message.chat.id, "❌ Не удалось добавить курс. Попробуйте позже.")
                logger.error(f"Error adding course: {e}")
        except Exception as e:
            logger.error(f"Error in save_new_course: {e}")

    @bot.message_handler(func=lambda m: m.text == "🗑 Удалить курс" and is_admin(m.from_user.id))
    def handle_delete_course(message):
        try:
            courses = get_all_courses()
            if not courses:
                bot.send_message(message.chat.id, "Нет доступных курсов.")
                return

            markup = types.InlineKeyboardMarkup()
            for c in courses:
                btn = types.InlineKeyboardButton(f"❌ {c[1]}", callback_data=f"delete_course:{c[0]}")
                markup.add(btn)

            bot.send_message(message.chat.id, "Выберите курс для удаления:", reply_markup=markup)
            logger.info(f"Admin {message.from_user.id} viewed courses for deletion")
        except Exception as e:
            logger.error(f"Error in handle_delete_course: {e}")

    @bot.message_handler(func=lambda m: m.text == "❄ Заморозить курс" and is_admin(m.from_user.id))
    def handle_toggle_course(message):
        try:
            courses = get_all_courses()
            if not courses:
                bot.send_message(message.chat.id, "Нет курсов.")
                return

            markup = types.InlineKeyboardMarkup()
            for c in courses:
                status = "✅" if c[3] else "🚫"
                markup.add(types.InlineKeyboardButton(f"{status} {c[1]}", callback_data=f"toggle_course:{c[0]}"))

            bot.send_message(message.chat.id, "Выберите курс для заморозки/разморозки:", reply_markup=markup)
            logger.info(f"Admin {message.from_user.id} viewed courses for toggling")
        except Exception as e:
            logger.error(f"Error in handle_toggle_course: {e}")

    @bot.message_handler(func=lambda m: m.text == "📝 Отредактировать курс" and is_admin(m.from_user.id))
    def handle_edit_course(message):
        try:
            courses = get_all_courses()
            if not courses:
                bot.send_message(message.chat.id, "Нет курсов.")
                return

            markup = types.InlineKeyboardMarkup()
            for c in courses:
                markup.add(types.InlineKeyboardButton(f"✏ {c[1]}", callback_data=f"edit_course:{c[0]}"))

            bot.send_message(message.chat.id, "Выберите курс для редактирования:", reply_markup=markup)
            logger.info(f"Admin {message.from_user.id} viewed courses for editing")
        except Exception as e:
            logger.error(f"Error in handle_edit_course: {e}")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("delete_course:"))
    def confirm_delete_course(call):
        try:
            course_id = int(call.data.split(":")[1])
            try:
                delete_course(course_id)
                bot.edit_message_text("✅ Курс удалён.", call.message.chat.id, call.message.message_id)
                logger.info(f"Admin {call.from_user.id} deleted course {course_id}")
            except Exception as e:
                bot.send_message(call.message.chat.id, "❌ Не удалось удалить курс. Попробуйте позже.")
                logger.error(f"Error deleting course: {e}")
        except Exception as e:
            logger.error(f"Error in confirm_delete_course: {e}")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("toggle_course:"))
    def confirm_toggle_course(call):
        try:
            course_id = int(call.data.split(":")[1])
            toggle_course_active(course_id)
            bot.edit_message_text("🔁 Статус курса обновлён.", call.message.chat.id, call.message.message_id)
            logger.info(f"Admin {call.from_user.id} toggled course {course_id}")
        except Exception as e:
            logger.error(f"Error in confirm_toggle_course: {e}")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("edit_course:"))
    def start_editing(call):
        try:
            course_id = int(call.data.split(":")[1])
            bot.send_message(call.message.chat.id, "Введите новое название курса:", reply_markup=get_cancel_button())
            bot.register_next_step_handler(call.message, lambda m: get_new_name(m, course_id))
            logger.info(f"Admin {call.from_user.id} started editing course {course_id}")
        except Exception as e:
            logger.error(f"Error in start_editing: {e}")

    def get_new_name(message, course_id):
        try:
            # Проверяем отмену
            if message.text == "🔙 Отмена":
                handle_cancel_action(bot, message, "курс", logger)
                return
                
            name = message.text.strip()
            bot.send_message(message.chat.id, "Введите новое описание:", reply_markup=get_cancel_button())
            bot.register_next_step_handler(message, lambda m: apply_edit(m, course_id, name))
        except Exception as e:
            logger.error(f"Error in get_new_name: {e}")

    def apply_edit(message, course_id, name):
        try:
            # Проверяем отмену
            if message.text == "🔙 Отмена":
                handle_cancel_action(bot, message, "курс", logger)
                return
            desc = message.text.strip()
            try:
                update_course(course_id, name, desc)
                bot.send_message(message.chat.id, f"✅ Курс обновлён: {name}", reply_markup=get_course_editor_menu())
                logger.info(f"Admin {message.from_user.id} updated course {course_id} to: {name}")
            except Exception as e:
                bot.send_message(message.chat.id, "❌ Не удалось обновить курс. Попробуйте позже.")
                logger.error(f"Error updating course: {e}")
        except Exception as e:
            logger.error(f"Error in apply_edit: {e}")

    @bot.message_handler(func=lambda m: m.text == "🔙 Назад" and is_admin(m.from_user.id))
    def handle_back_to_admin_panel(message):
        try:
            bot.send_message(message.chat.id, "🔙 Возврат в админ-панель", reply_markup=get_admin_menu())
            logger.info(f"Admin {message.from_user.id} returned to admin panel")
        except Exception as e:
            logger.error(f"Error in handle_back_to_admin_panel: {e}")

    @bot.message_handler(func=lambda m: m.text == "👁 Просмотреть все курсы" and is_admin(m.from_user.id))
    def handle_view_all_courses(message):
        try:
            courses = get_all_courses()
            if not courses:
                bot.send_message(message.chat.id, "Нет курсов в системе.")
                return
            msg = "<b>Все курсы:</b>\n\n"
            for c in courses:
                course_id, name, desc, active = c
                status = "✅ Активен" if active else "🚫 Неактивен"
                msg += f"<b>{name}</b> ({status})\nОписание: {desc}\n\n"
            bot.send_message(message.chat.id, msg, parse_mode="HTML")
            logger.info(f"Admin {message.from_user.id} viewed all courses")
        except Exception as e:
            logger.error(f"Error in handle_view_all_courses: {e}") 