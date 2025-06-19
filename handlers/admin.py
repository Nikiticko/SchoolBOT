from telebot import types
from services.sheets_init import worksheet
from services.courses_service import get_courses
from config import ADMIN_ID

def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

def notify_admin_new_application(bot, application_data):
    try:
        notification = (
            "🔔 Новая заявка на обучение!\n\n"
            f"👤 Имя: {application_data.get('name', 'Не указано')}\n"
            f"📱 Контакт: {application_data.get('contact', 'Не указан')}\n"
            f"📚 Курс: {application_data.get('course', 'Не указан')}\n"
            f"🎯 Цель: {application_data.get('goal', 'Не указана')}\n"
            f"📅 Возраст: {application_data.get('age', 'Не указан')}"
        )
        bot.send_message(ADMIN_ID, notification)
        print(f"[✅] Уведомление отправлено админу {ADMIN_ID}")
    except Exception as e:
        print(f"[❌] Ошибка при отправке уведомления админу: {str(e)}")

def register(bot):
    def show_admin_panel(chat_id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("📋 Список заявок", "📚 Редактировать курсы")  # ← ключевая строка
        bot.send_message(chat_id, "👋 Добро пожаловать в админ-панель!", reply_markup=markup)


    @bot.message_handler(commands=["start"])
    def handle_start(message):
        user_id = message.from_user.id
        print(f"[DEBUG] /start от ID: {user_id}")
        print(f"[DEBUG] ADMIN_ID = {ADMIN_ID} (type={type(ADMIN_ID)}), user_id = {user_id} (type={type(user_id)})")
        print(f"[DEBUG] /start от {user_id}")
        if is_admin(user_id):
            print("[DEBUG] Это админ — показываем админ-панель")
            show_admin_panel(message.chat.id)
        else:
            bot.send_message(message.chat.id, "👋 Добро пожаловать! Для записи нажмите кнопку в меню.")

    @bot.message_handler(func=lambda m: m.text == "📋 Список заявок" and is_admin(m.from_user.id))
    def handle_pending_applications(message):
        print(f"[DEBUG] Запрос списка заявок от {message.from_user.id}")
        try:
            data = worksheet.get_all_values()
            if len(data) <= 1:
                bot.send_message(message.chat.id, "✅ Нет заявок в таблице")
                return

            headers = data[0]
            try:
                date_col = headers.index('Дата занятия')
                link_col = headers.index('Ссылка на занятие')
                name_col = headers.index('Имя')
                contact_col = headers.index('Контакты')
                course_col = headers.index('Курс')
                goal_col = headers.index('Цель')
                age_col = headers.index('Возраст')
                id_col = headers.index('ID')
            except ValueError as e:
                bot.send_message(message.chat.id, f"❌ Ошибка в структуре таблицы: {str(e)}")
                return

            pending_apps = []

            for row in data[1:]:
                date = str(row[date_col]).strip() if date_col < len(row) else ""
                link = str(row[link_col]).strip() if link_col < len(row) else ""

                if not date and not link:
                    app_info = (
                        f"👤 Имя: {row[name_col] if name_col < len(row) else 'Не указано'}\n"
                        f"📱 Контакт: {row[contact_col] if contact_col < len(row) else 'Не указан'}\n"
                        f"📚 Курс: {row[course_col] if course_col < len(row) else 'Не указан'}\n"
                        f"🎯 Цель: {row[goal_col] if goal_col < len(row) else 'Не указана'}\n"
                        f"📅 Возраст: {row[age_col] if age_col < len(row) else 'Не указан'}\n"
                        f"🆔 ID в таблице: {row[id_col] if id_col < len(row) else 'Не указан'}\n"
                        f"-------------------"
                    )
                    pending_apps.append(app_info)

            if pending_apps:
                response = "📋 Список заявок без назначенной даты:\n\n" + "\n\n".join(pending_apps)
                if len(response) > 4000:
                    parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
                    for part in parts:
                        bot.send_message(message.chat.id, part)
                else:
                    bot.send_message(message.chat.id, response)
            else:
                bot.send_message(message.chat.id, "✅ Нет заявок без назначенной даты")

        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка при получении заявок: {str(e)}")

    @bot.message_handler(func=lambda m: m.text == "📚 Редактировать курсы" and is_admin(m.from_user.id))
    def handle_course_menu(message):
        print(f"[DEBUG] Вход в редактор курсов от ID: {message.from_user.id}")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ Добавить курс", "🗑 Удалить курс")
        markup.add("❄ Заморозить курс", "📝 Отредактировать курс")
        markup.add("🔙 Назад")
        bot.send_message(message.chat.id, "🎓 Меню редактирования курсов:", reply_markup=markup)
