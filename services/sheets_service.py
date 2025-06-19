from datetime import datetime
from state.users import user_data, used_contacts, pending, writing_ids
from .sheets_init import worksheet
from utils.menu import get_main_menu


def finish_registration(bot, chat_id):
    print(f"[finish] ▶ Попытка завершить регистрацию для chat_id={chat_id}")

    data = user_data.get(chat_id)
    if not data:
        print(f"[finish] ❌ user_data пустой для chat_id={chat_id}")
        bot.send_message(chat_id, "⚠️ Регистрация была прервана. Начните сначала.")
        return

    identifier = data.get("contact") or str(chat_id)
    print(f"[finish] ▶ Проверка существующей заявки по идентификатору: {identifier}")

    # 🔒 Блокировка от повторной одновременной записи
    if identifier in writing_ids:
        print(f"[finish] ⛔ Регистрация уже выполняется для {identifier}, отмена.")
        return

    writing_ids.add(identifier)

    try:
        existing = get_user_row(identifier)
        if existing:
            print(f"[finish] 🔁 Уже существует заявка для {identifier}. Запись отменена.")
            markup = get_main_menu()
            bot.send_message(chat_id, "⛔ Вы уже отправляли заявку. Ожидайте ответа.", reply_markup=markup)
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        row = [
            str(chat_id),                   # ID (A)
            data.get('parent_name', ""),   # Имя родителя (B)
            data.get('student_name', ""),  # Имя ученика (C)
            data.get('age', ""),           # Возраст (D)
            data.get('contact', ""),       # Контакт (E)
            data.get('course', ""),        # Курс (F)
            "",                            # Дата занятия (G)
            "",                            # Ссылка (H)
            "Ожидает",                     # Статус (I)
            now                            # Время создания (J)
        ]

        worksheet.append_row(row)
        print(f"[finish] ✅ Заявка добавлена в таблицу: {identifier}")

        contact = data.get('contact')
        if contact:
            used_contacts.add(contact)
        pending[contact or chat_id] = row

        markup = get_main_menu()
        bot.send_message(chat_id, "✅ Заявка успешно отправлена. Мы свяжемся с вами для назначения занятия.", reply_markup=markup)

    except Exception as e:
        print(f"[finish] ❌ Ошибка при сохранении заявки: {e}")
        bot.send_message(chat_id, f"❌ Ошибка при сохранении данных: {e}")

    finally:
        writing_ids.discard(identifier)
        user_data.pop(chat_id, None)


def get_user_row(identifier):
    """Поиск строки пользователя по chat_id или contact"""
    try:
        cell = worksheet.find(str(identifier))
        if not cell:
            return None
        return worksheet.row_values(cell.row)
    except Exception as e:
        print(f"[get_user_row] ❌ Ошибка при поиске: {e}")
        return None


def update_status_by_user_id(user_id, new_status):
    """Обновляет поле 'Статус' по chat_id"""
    try:
        cell = worksheet.find(str(user_id))
        row = cell.row
        worksheet.update_cell(row, 9, new_status)  # Столбец I
        return True
    except Exception as e:
        print(f"[update_status] ❌ Ошибка при обновлении статуса: {e}")
        return False
