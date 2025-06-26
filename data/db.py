import sqlite3
from datetime import datetime
import re

DB_NAME = "data/database.db"

def parse_date_string(date_str):
    """Парсит строку даты в формате 'DD.MM HH:MM' в datetime объект"""
    if not date_str or date_str == 'None':
        return None
    
    try:
        # Предполагаем формат "22.06 17:30"
        if '.' in date_str and ':' in date_str:
            # Извлекаем дату и время
            date_part, time_part = date_str.split(' ')
            day, month = date_part.split('.')
            hour, minute = time_part.split(':')
            
            # Текущий год
            current_year = datetime.now().year
            
            # Создаем datetime объект
            dt = datetime(current_year, int(month), int(day), int(hour), int(minute))
            
            # Если дата в прошлом, добавляем год
            if dt < datetime.now():
                dt = datetime(current_year + 1, int(month), int(day), int(hour), int(minute))
            
            return dt
        else:
            # Попробуем другие форматы
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except Exception as e:
        print(f"⚠️ Не удалось распарсить дату '{date_str}': {e}")
        return None

def format_date_for_display(dt):
    """Форматирует datetime объект для отображения в формате 'DD.MM HH:MM'"""
    if not dt:
        return "Не назначено"
    
    if isinstance(dt, str):
        # Если это строка, пытаемся распарсить
        dt = parse_date_string(dt)
        if not dt:
            return dt
    
    return dt.strftime("%d.%m %H:%M")

def get_connection():
    import os
    path = os.path.abspath(DB_NAME)
    print(f"🛠 Путь к базе, которую использует бот: {path}")
    return sqlite3.connect(DB_NAME)


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id TEXT,
                parent_name TEXT,
                student_name TEXT,
                age TEXT,
                contact TEXT,
                course TEXT,
                lesson_date DATETIME,
                lesson_link TEXT,
                status TEXT DEFAULT 'Ожидает',
                created_at DATETIME DEFAULT (datetime('now', 'localtime'))
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                active BOOLEAN DEFAULT 1
            )
        """)
        
        # Создаем индексы для улучшения производительности
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_lesson_date ON applications(lesson_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_created_at ON applications(created_at)")
        
        conn.commit()


def add_application(tg_id, parent_name, student_name, age, contact, course):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO applications (tg_id, parent_name, student_name, age, contact, course)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (tg_id, parent_name, student_name, age, contact, course))
        conn.commit()

def get_application_by_tg_id(tg_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM applications
            WHERE tg_id = ?
            ORDER BY created_at DESC LIMIT 1
        """, (tg_id,))
        return cursor.fetchone()

def get_pending_applications():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM applications
            WHERE status = 'Ожидает'
            ORDER BY created_at DESC
        """)
        return cursor.fetchall()

def update_application_lesson(app_id, lesson_date, lesson_link):
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Конвертируем строку даты в datetime объект, если необходимо
        if isinstance(lesson_date, str):
            lesson_date = parse_date_string(lesson_date)
        
        cursor.execute("""
            UPDATE applications
            SET lesson_date = ?, lesson_link = ?, status = 'Назначено'
            WHERE id = ?
        """, (lesson_date, lesson_link, app_id))
        conn.commit()

# === КУРСЫ ===
# === КУРСЫ ===

def get_active_courses():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM courses WHERE active = 1 ORDER BY id DESC")
        return cursor.fetchall()


def get_all_courses():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM courses ORDER BY id DESC")
        return cursor.fetchall()

def add_course(name, description):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO courses (name, description, active)
            VALUES (?, ?, 1)
        """, (name, description))
        conn.commit()

def delete_course(course_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM courses WHERE id = ?", (course_id,))
        conn.commit()

def update_course(course_id, new_name, new_description):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE courses SET name = ?, description = ?
            WHERE id = ?
        """, (new_name, new_description, course_id))
        conn.commit()

def toggle_course_active(course_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE courses
            SET active = NOT active
            WHERE id = ?
        """, (course_id,))
        conn.commit()




def clear_applications():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM applications")
        conn.commit()



def get_application_by_id(app_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
        return cursor.fetchone()


def update_application_status(app_id, new_status):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE applications
            SET status = ?
            WHERE id = ?
        """, (new_status, app_id))
        conn.commit()

def get_assigned_applications():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM applications
            WHERE status = 'Назначено'
            ORDER BY created_at DESC
        """)
        return cursor.fetchall()

def cancel_assigned_lesson(app_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE applications
            SET lesson_date = NULL,
                lesson_link = NULL,
                status = 'Отменено'
            WHERE id = ?
        """, (app_id,))
        conn.commit()


def archive_application(app_id: int, cancelled_by="user", comment="", archived_status="Заявка отменена"):
    with get_connection() as conn:
        cursor = conn.cursor()

        # Получаем заявку
        cursor.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
        row = cursor.fetchone()
        if not row:
            print("[❌] archive_application: заявка не найдена")
            return False

        # Вставляем в archive
        try:
            cursor.execute("""
                INSERT INTO archive (
                    tg_id, parent_name, student_name, age, contact, course,
                    lesson_date, lesson_link, status, created_at,
                    cancelled_by, comment
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row[1], row[2], row[3], row[4], row[5], row[6],
                row[7], row[8], archived_status, row[10],
                cancelled_by, comment
            ))
        except Exception as e:
            print("🔥 [FATAL] Ошибка при вставке в archive:", e)
            print("🔥 Параметры:", (
                row[1], row[2], row[3], row[4], row[5], row[6],
                row[7], row[8], archived_status, row[10],
                cancelled_by, comment
            ))
            raise

        # Удаляем из applications
        cursor.execute("DELETE FROM applications WHERE id = ?", (app_id,))
        conn.commit()
        return True





def get_archive_count_by_tg_id(tg_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM archive WHERE tg_id = ?", (tg_id,))
        return cursor.fetchone()[0]


def clear_archive():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM archive")
        conn.commit()

def validate_date_format(date_str):
    """Проверяет, соответствует ли строка даты правильному формату 'DD.MM HH:MM'"""
    if not date_str or not isinstance(date_str, str):
        return False, "Дата должна быть строкой"
    
    date_str = date_str.strip()
    
    # Проверяем строгий формат: ДД.ММ ЧЧ:ММ (с ведущими нулями)
    if not re.match(r'^\d{2}\.\d{2}\s+\d{2}:\d{2}$', date_str):
        return False, "Формат должен быть: ДД.ММ ЧЧ:ММ (например: 22.06 17:30)"
    
    try:
        # Разбираем дату
        date_part, time_part = date_str.split(' ')
        day, month = date_part.split('.')
        hour, minute = time_part.split(':')
        
        # Проверяем диапазоны
        day = int(day)
        month = int(month)
        hour = int(hour)
        minute = int(minute)
        
        if not (1 <= day <= 31):
            return False, "День должен быть от 1 до 31"
        
        if not (1 <= month <= 12):
            return False, "Месяц должен быть от 1 до 12"
        
        if not (0 <= hour <= 23):
            return False, "Час должен быть от 0 до 23"
        
        if not (0 <= minute <= 59):
            return False, "Минуты должны быть от 0 до 59"
        
        # Проверяем корректность даты
        current_year = datetime.now().year
        test_date = datetime(current_year, month, day, hour, minute)
        
        # Если дата в прошлом, добавляем год
        if test_date < datetime.now():
            test_date = datetime(current_year + 1, month, day, hour, minute)
        
        return True, test_date
        
    except ValueError as e:
        return False, f"Некорректная дата: {str(e)}"
    except Exception as e:
        return False, f"Ошибка при проверке даты: {str(e)}"

def get_all_applications():
    """Возвращает все заявки из таблицы applications."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM applications ORDER BY created_at DESC")
        return cursor.fetchall()

def get_all_archive():
    """Возвращает все записи из архива."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM archive ORDER BY created_at DESC")
        return cursor.fetchall()

def get_cancelled_count_by_tg_id(tg_id):
    """Возвращает количество отменённых заявок и уроков пользователя (статусы 'Заявка отменена', 'Урок отменён')."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM archive WHERE tg_id = ? AND (status = 'Заявка отменена' OR status = 'Урок отменён')", (tg_id,))
        return cursor.fetchone()[0]

def get_finished_count_by_tg_id(tg_id):
    """Возвращает количество завершённых уроков пользователя (статус 'Завершено')."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM archive WHERE tg_id = ? AND status = 'Завершено'", (tg_id,))
        return cursor.fetchone()[0]
