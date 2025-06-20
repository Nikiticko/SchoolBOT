from telebot import types
from data.db import get_all_courses, add_course, delete_course, update_course, toggle_course_active
from handlers.admin import is_admin
from utils.menu import get_admin_menu

def register_course_editor(bot):
    @bot.message_handler(func=lambda m: m.text == "➕ Добавить курс" and is_admin(m.from_user.id))
    def handle_add_course(message):
        bot.send_message(message.chat.id, "Введите название нового курса:")
        bot.register_next_step_handler(message, lambda m: get_course_name(m, bot))

    def get_course_name(message, bot):
        name = message.text.strip()
        bot.send_message(message.chat.id, "Введите описание курса:")
        bot.register_next_step_handler(message, lambda m: save_new_course(m, bot, name))

    def save_new_course(message, bot, name):
        desc = message.text.strip()
        add_course(name, desc)
        bot.send_message(message.chat.id, f"✅ Курс «{name}» добавлен.")


    @bot.message_handler(func=lambda m: m.text == "🗑 Удалить курс" and is_admin(m.from_user.id))
    def handle_delete_course(message):
        courses = get_all_courses()
        if not courses:
            bot.send_message(message.chat.id, "Нет доступных курсов.")
            return

        markup = types.InlineKeyboardMarkup()
        for c in courses:
            btn = types.InlineKeyboardButton(f"❌ {c[1]}", callback_data=f"delete_course:{c[0]}")
            markup.add(btn)

        bot.send_message(message.chat.id, "Выберите курс для удаления:", reply_markup=markup)

    @bot.message_handler(func=lambda m: m.text == "❄ Заморозить курс" and is_admin(m.from_user.id))
    def handle_toggle_course(message):
        courses = get_all_courses()
        if not courses:
            bot.send_message(message.chat.id, "Нет курсов.")
            return

        markup = types.InlineKeyboardMarkup()
        for c in courses:
            status = "✅" if c[3] else "🚫"
            markup.add(types.InlineKeyboardButton(f"{status} {c[1]}", callback_data=f"toggle_course:{c[0]}"))

        bot.send_message(message.chat.id, "Выберите курс для заморозки/разморозки:", reply_markup=markup)

    @bot.message_handler(func=lambda m: m.text == "📝 Отредактировать курс" and is_admin(m.from_user.id))
    def handle_edit_course(message):
        courses = get_all_courses()
        if not courses:
            bot.send_message(message.chat.id, "Нет курсов.")
            return

        markup = types.InlineKeyboardMarkup()
        for c in courses:
            markup.add(types.InlineKeyboardButton(f"✏ {c[1]}", callback_data=f"edit_course:{c[0]}"))

        bot.send_message(message.chat.id, "Выберите курс для редактирования:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("delete_course:"))
    def confirm_delete_course(call):
        course_id = int(call.data.split(":")[1])
        delete_course(course_id)
        bot.edit_message_text("✅ Курс удалён.", call.message.chat.id, call.message.message_id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("toggle_course:"))
    def confirm_toggle_course(call):
        course_id = int(call.data.split(":")[1])
        toggle_course_active(course_id)
        bot.edit_message_text("🔁 Статус курса обновлён.", call.message.chat.id, call.message.message_id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("edit_course:"))
    def start_editing(call):
        course_id = int(call.data.split(":")[1])
        bot.send_message(call.message.chat.id, "Введите новое название курса:")
        bot.register_next_step_handler(call.message, lambda m: get_new_name(m, course_id))

    def get_new_name(message, course_id):
        name = message.text.strip()
        bot.send_message(message.chat.id, "Введите новое описание:")
        bot.register_next_step_handler(message, lambda m: apply_edit(m, course_id, name))

    def apply_edit(message, course_id, name):
        desc = message.text.strip()
        update_course(course_id, name, desc)
        bot.send_message(message.chat.id, f"✅ Курс обновлён: {name}")
    @bot.message_handler(func=lambda m: m.text == "🔙 Назад" and is_admin(m.from_user.id))
    def handle_back_to_admin_panel(message):
        bot.send_message(message.chat.id, "🔙 Возврат в админ-панель", reply_markup=get_admin_menu())
