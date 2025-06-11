from telebot import types
from services.sheets_init import worksheet
from config import ADMIN_ID

def is_admin(user_id):
    """Проверка является ли пользователь администратором"""
    return str(user_id) == str(ADMIN_ID)

def notify_admin_new_application(bot, application_data):
    """Отправка уведомления администратору о новой заявке"""
    try:
        notification = (
            "🔔 Новая заявка на обучение!\n\n"
            f"👤 Имя: {application_data.get('name', 'Не указано')}\n"
            f"📱 Контакт: {application_data.get('contact', 'Не указан')}\n"
            f"📚 Курс: {application_data.get('course', 'Не указан')}\n"
            f"🎯 Цель: {application_data.get('goal', 'Не указана')}\n"
            f"📅 Возраст: {application_data.get('age', 'Не указан')}"
        )
        
        # Отправляем уведомление напрямую админу
        bot.send_message(ADMIN_ID, notification)
        print(f"✅ Уведомление отправлено админу {ADMIN_ID}")
    except Exception as e:
        print(f"❌ Ошибка при отправке уведомления админу: {str(e)}")

def register(bot):
    @bot.message_handler(func=lambda m: m.text == "👨‍💼 Админ-панель" and is_admin(m.from_user.id))
    def handle_admin_panel(message):
        """Обработчик входа в админ-панель"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📋 Список заявок")
        bot.send_message(message.chat.id, "Добро пожаловать в админ-панель!", reply_markup=markup)

    @bot.message_handler(func=lambda m: m.text == "📋 Список заявок" and is_admin(m.from_user.id))
    def handle_pending_applications(message):
        """Показать список заявок без назначенной даты"""
        try:
            # Получаем все данные из таблицы
            data = worksheet.get_all_values()
            if len(data) <= 1:  # Если есть только заголовки или таблица пуста
                bot.send_message(message.chat.id, "✅ Нет заявок в таблице")
                return
                
            # Получаем индексы колонок
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
            
            # Начинаем с 1, пропуская заголовки
            for row in data[1:]:
                # Проверяем, что и дата, и ссылка пустые
                date = str(row[date_col]).strip() if date_col < len(row) else ""
                link = str(row[link_col]).strip() if link_col < len(row) else ""
                
                if not date and not link:  # Только если оба поля пустые
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
                # Разбиваем сообщение на части, если оно слишком длинное
                if len(response) > 4000:
                    parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
                    for part in parts:
                        bot.send_message(message.chat.id, part)
                else:
                    bot.send_message(message.chat.id, response)
            else:
                bot.send_message(message.chat.id, "✅ Нет заявок без назначенной даты")
                
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка при получении списка заявок: {str(e)}") 