import sqlite3
from datetime import datetime
import re
import os

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

def check_database_integrity():
    """
    Проверяет целостность базы данных
    Возвращает: (is_ok, error_message)
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем целостность БД
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            
            if result[0] != "ok":
                return False, f"Целостность БД нарушена: {result[0]}"
            
            # Проверяем внешние ключи
            cursor.execute("PRAGMA foreign_key_check")
            foreign_key_errors = cursor.fetchall()
            
            if foreign_key_errors:
                return False, f"Найдены ошибки внешних ключей: {foreign_key_errors}"
            
            # Проверяем размер БД
            db_size = os.path.getsize(DB_NAME) / (1024 * 1024)  # МБ
            if db_size > 100:  # Предупреждение если БД больше 100 МБ
                print(f"⚠️ База данных большая: {db_size:.1f} МБ")
            
            print("✅ Проверка целостности БД пройдена успешно")
            return True, "OK"
            
    except Exception as e:
        error_msg = f"Ошибка при проверке целостности БД: {e}"
        print(f"❌ {error_msg}")
        return False, error_msg


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
                status TEXT,
                created_at DATETIME DEFAULT (datetime('now', 'localtime')),
                reminder_sent BOOLEAN DEFAULT 0,
                review_request_sent BOOLEAN DEFAULT 0,
                last_admin_notification DATETIME
            )
        """)
        
        # Индексы для applications (добавляем новые)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_tg_id ON applications(tg_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_lesson_date ON applications(lesson_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_created_at ON applications(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_course ON applications(course)")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                active BOOLEAN DEFAULT 1
            )
        """)
        
        # Индексы для courses
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_courses_active ON courses(active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_courses_name ON courses(name)")
        
        # Новая таблица обращений
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_tg_id TEXT,
                user_contact TEXT,
                message TEXT,
                admin_reply TEXT,
                status TEXT DEFAULT 'Ожидает ответа',
                created_at DATETIME DEFAULT (datetime('now', 'localtime')),
                reply_at DATETIME,
                banned BOOLEAN DEFAULT 0,
                ban_reason TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_user_tg_id ON contacts(user_tg_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_status ON contacts(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_created_at ON contacts(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_banned ON contacts(banned)")
        
        # Таблица отзывов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER,
                user_tg_id TEXT,
                rating INTEGER CHECK (rating >= 1 AND rating <= 10),
                feedback TEXT,
                is_anonymous BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_application_id ON reviews(application_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_user_tg_id ON reviews(user_tg_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews(rating)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_created_at ON reviews(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_is_anonymous ON reviews(is_anonymous)")
        
        # Таблица архива (если не существует)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS archive (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id TEXT,
                parent_name TEXT,
                student_name TEXT,
                age TEXT,
                contact TEXT,
                course TEXT,
                lesson_date DATETIME,
                lesson_link TEXT,
                status TEXT,
                created_at DATETIME,
                archived_at DATETIME,
                cancelled_by TEXT,
                comment TEXT
            )
        """)
        
        # --- Добавляем колонку archived_at, если её нет (для старых БД) ---
        cursor.execute("PRAGMA table_info(archive)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'archived_at' not in columns:
            cursor.execute("ALTER TABLE archive ADD COLUMN archived_at DATETIME")
            cursor.execute("UPDATE archive SET archived_at = datetime('now', 'localtime') WHERE archived_at IS NULL")
        
        # Индексы для archive
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_archive_tg_id ON archive(tg_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_archive_status ON archive(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_archive_archived_at ON archive(archived_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_archive_cancelled_by ON archive(cancelled_by)")
        
        conn.commit()


def add_application(tg_id, parent_name, student_name, age, contact, course):
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # ИСПРАВЛЕНО: Проверяем существующие заявки
        cursor.execute("""
            SELECT id, status FROM applications 
            WHERE tg_id = ? 
            ORDER BY created_at DESC LIMIT 1
        """, (tg_id,))
        existing = cursor.fetchone()
        
        if existing:
            app_id, status = existing
            if status == "Ожидает":
                raise ValueError(f"У пользователя {tg_id} уже есть активная заявка #{app_id}")
            elif status == "Назначено":
                raise ValueError(f"У пользователя {tg_id} уже назначен урок (заявка #{app_id})")
        
        cursor.execute("""
            INSERT INTO applications (tg_id, parent_name, student_name, age, contact, course, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (tg_id, parent_name, student_name, age, contact, course, 'Ожидает'))
        conn.commit()

def get_application_by_tg_id(tg_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, tg_id, parent_name, student_name, age, contact, course, 
                   lesson_date, lesson_link, status, created_at, reminder_sent
            FROM applications
            WHERE tg_id = ?
            ORDER BY created_at DESC LIMIT 1
        """, (tg_id,))
        return cursor.fetchone()

def get_pending_applications():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, tg_id, parent_name, student_name, age, contact, course, 
                   lesson_date, lesson_link, status, created_at, reminder_sent
            FROM applications
            WHERE lesson_date IS NULL AND lesson_link IS NULL
            ORDER BY created_at DESC
        """)
        return cursor.fetchall()

def update_application_lesson(app_id, lesson_date, lesson_link):
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Конвертируем строку даты в datetime объект, если необходимо
        if isinstance(lesson_date, str):
            parsed_date = parse_date_string(lesson_date)
            if parsed_date is None:
                raise ValueError(f"Неверный формат даты: {lesson_date}")
            lesson_date = parsed_date
        
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
        cursor.execute("SELECT id, name, description, active FROM courses WHERE active = 1 ORDER BY id DESC")
        return cursor.fetchall()


def get_all_courses():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, description, active FROM courses ORDER BY id DESC")
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

def clear_courses():
    """Очищает все курсы"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM courses")
        conn.commit()




def clear_applications():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM applications")
        conn.commit()



def get_application_by_id(app_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, tg_id, parent_name, student_name, age, contact, course, 
                   lesson_date, lesson_link, status, created_at, reminder_sent
            FROM applications WHERE id = ?
        """, (app_id,))
        return cursor.fetchone()


def get_assigned_applications():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, tg_id, parent_name, student_name, age, contact, course, 
                   lesson_date, lesson_link, status, created_at, reminder_sent
            FROM applications
            WHERE lesson_date IS NOT NULL AND lesson_link IS NOT NULL
            ORDER BY created_at DESC
        """)
        return cursor.fetchall()

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
        cursor.execute("""
            SELECT id, tg_id, parent_name, student_name, age, contact, course, 
                   lesson_date, lesson_link, status, created_at, reminder_sent
            FROM applications ORDER BY created_at DESC
        """)
        return cursor.fetchall()

def get_all_archive():
    """Возвращает все записи из архива."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, tg_id, parent_name, student_name, age, contact, course,
                   lesson_date, lesson_link, status, created_at, archived_at, 
                   cancelled_by, comment
            FROM archive ORDER BY archived_at DESC
        """)
        return cursor.fetchall()

def get_cancelled_count_by_tg_id(tg_id):
    """Возвращает количество отменённых заявок и уроков пользователя (статусы 'Заявка отменена', 'Урок отменён')."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM archive 
            WHERE tg_id = ? AND (status = 'Заявка отменена' OR status = 'Урок отменён')
        """, (tg_id,))
        return cursor.fetchone()[0]

def get_finished_count_by_tg_id(tg_id):
    """Возвращает количество завершённых уроков пользователя (статус 'Завершено')."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM archive 
            WHERE tg_id = ? AND status = 'Завершено'
        """, (tg_id,))
        return cursor.fetchone()[0]

# --- Функции для работы с обращениями ---
def add_contact(user_tg_id, user_contact, message):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO contacts (user_tg_id, user_contact, message)
            VALUES (?, ?, ?)
        """, (user_tg_id, user_contact, message))
        conn.commit()
        return cursor.lastrowid

def get_last_contact_time(user_tg_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT created_at FROM contacts 
            WHERE user_tg_id = ? 
            ORDER BY created_at DESC LIMIT 1
        """, (user_tg_id,))
        row = cursor.fetchone()
        return row[0] if row else None

def get_open_contacts():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_tg_id, user_contact, message, admin_reply, status, 
                   created_at, reply_at, banned, ban_reason
            FROM contacts 
            WHERE status = 'Ожидает ответа' 
            ORDER BY created_at ASC
        """)
        return cursor.fetchall()

def get_all_contacts():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_tg_id, user_contact, message, admin_reply, status, 
                   created_at, reply_at, banned, ban_reason
            FROM contacts 
            ORDER BY created_at DESC
        """)
        return cursor.fetchall()

def get_contact_by_id(contact_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_tg_id, user_contact, message, admin_reply, status, 
                   created_at, reply_at, banned, ban_reason
            FROM contacts WHERE id = ?
        """, (contact_id,))
        return cursor.fetchone()

def reply_to_contact(contact_id, reply_text):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE contacts
            SET admin_reply = ?, status = 'Ответ предоставлен', reply_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (reply_text, contact_id))
        conn.commit()

def update_contact_reply(contact_id, reply_text):
    """Обновляет ответ на обращение (аналогично reply_to_contact, но с другим названием)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE contacts
            SET admin_reply = ?, status = 'Ответ предоставлен', reply_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (reply_text, contact_id))
        conn.commit()

def ban_user_by_contact(user_tg_id, reason=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        if reason:
            cursor.execute("""
                UPDATE contacts 
                SET banned = 1, ban_reason = ?, status = 'Ответ предоставлен', admin_reply = NULL, reply_at = CURRENT_TIMESTAMP
                WHERE user_tg_id = ?
            """, (reason, user_tg_id))
        else:
            cursor.execute("""
                UPDATE contacts 
                SET banned = 1, status = 'Ответ предоставлен', admin_reply = NULL, reply_at = CURRENT_TIMESTAMP
                WHERE user_tg_id = ?
            """, (user_tg_id,))
        conn.commit()

def is_user_banned(user_tg_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT banned FROM contacts 
            WHERE user_tg_id = ? 
            ORDER BY created_at DESC LIMIT 1
        """, (user_tg_id,))
        row = cursor.fetchone()
        return bool(row[0]) if row else False

def get_ban_reason(user_tg_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ban_reason FROM contacts 
            WHERE user_tg_id = ? AND banned = 1 
            ORDER BY created_at DESC LIMIT 1
        """, (user_tg_id,))
        row = cursor.fetchone()
        return row[0] if row else None

def clear_contacts():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM contacts")
        conn.commit()

def get_upcoming_lessons(minutes=30):
    """Возвращает заявки, у которых урок через <=minutes и напоминание не отправлено"""
    import datetime
    now = datetime.datetime.now()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, tg_id, parent_name, student_name, age, contact, course, 
                   lesson_date, lesson_link, status, created_at, reminder_sent
            FROM applications
            WHERE lesson_date IS NOT NULL
              AND lesson_link IS NOT NULL
              AND reminder_sent = 0
        """)
        rows = cursor.fetchall()
        result = []
        for row in rows:
            lesson_date = row[7]  # lesson_date - индекс 7
            if not lesson_date:
                continue
            dt = None
            try:
                dt = datetime.datetime.fromisoformat(lesson_date)
            except Exception as e:
                try:
                    dt = datetime.datetime.strptime(lesson_date, "%Y-%m-%d %H:%M:%S")
                except Exception as e2:
                    try:
                        dt = datetime.datetime.strptime(lesson_date, "%Y-%m-%d %H:%M:%S.%f")
                    except Exception as e3:
                        continue
            if not dt:
                continue
            delta = (dt - now).total_seconds() / 60
            if 0 < delta <= minutes:
                result.append(row)
        return result

def mark_reminder_sent(app_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE applications SET reminder_sent = 1 WHERE id = ?", (app_id,))
        conn.commit()

# === ФУНКЦИИ ДЛЯ РАБОТЫ С ОТЗЫВАМИ ===

def add_review(application_id, user_tg_id, rating, feedback, is_anonymous=False):
    """Добавляет отзыв"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reviews (application_id, user_tg_id, rating, feedback, is_anonymous)
            VALUES (?, ?, ?, ?, ?)
        """, (application_id, user_tg_id, rating, feedback, is_anonymous))
        conn.commit()
        return cursor.lastrowid

def get_reviews_for_publication(limit=10):
    """Возвращает отзывы для публикации (с рейтингом >= 7)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.rating, r.feedback, r.is_anonymous, 
                   a.parent_name, a.student_name, a.course,
                   r.created_at
            FROM reviews r
            JOIN applications a ON r.application_id = a.id
            WHERE r.rating >= 7
            ORDER BY r.created_at DESC
            LIMIT ?
        """, (limit,))
        return cursor.fetchall()

def get_reviews_for_publication_with_deleted(limit=10):
    """Возвращает отзывы для публикации (с рейтингом >= 7), включая удаленные заявки"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.rating, r.feedback, r.is_anonymous, 
                   COALESCE(a.parent_name, ar.parent_name) as parent_name,
                   COALESCE(a.student_name, ar.student_name) as student_name,
                   COALESCE(a.course, ar.course) as course,
                   r.created_at
            FROM reviews r
            LEFT JOIN applications a ON r.application_id = a.id
            LEFT JOIN archive ar ON r.application_id = ar.id
            WHERE r.rating >= 7 AND r.is_anonymous = 0
            ORDER BY r.created_at DESC
            LIMIT ?
        """, (limit,))
        return cursor.fetchall()

def get_all_reviews():
    """Возвращает все отзывы для админа (даже если заявка удалена)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.id, r.rating, r.feedback, r.is_anonymous, 
                   COALESCE(a.parent_name, ar.parent_name) as parent_name,
                   COALESCE(a.student_name, ar.student_name) as student_name,
                   COALESCE(a.course, ar.course) as course,
                   r.created_at, r.user_tg_id
            FROM reviews r
            LEFT JOIN applications a ON r.application_id = a.id
            LEFT JOIN archive ar ON r.application_id = ar.id
            ORDER BY r.created_at DESC
        """)
        return cursor.fetchall()

def get_review_stats():
    """Возвращает статистику отзывов"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_reviews,
                AVG(rating) as avg_rating,
                COUNT(CASE WHEN rating >= 8 THEN 1 END) as positive_reviews,
                COUNT(CASE WHEN rating <= 5 THEN 1 END) as negative_reviews
            FROM reviews
        """)
        return cursor.fetchone()

def has_user_reviewed_application(application_id, user_tg_id):
    """Проверяет, оставил ли пользователь отзыв на заявку"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM reviews 
            WHERE application_id = ? AND user_tg_id = ?
        """, (application_id, user_tg_id))
        return cursor.fetchone()[0] > 0

def clear_reviews():
    """Очищает все отзывы"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reviews")
        conn.commit()

def update_application(app_id, parent_name, student_name, age, contact, course):
    """Обновляет данные заявки"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE applications 
            SET parent_name=?, student_name=?, age=?, contact=?, course=? 
            WHERE id=?
        """, (parent_name, student_name, age, contact, course, app_id))
        conn.commit()

def delete_application_by_tg_id(tg_id):
    """Удаляет заявку по tg_id"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM applications WHERE tg_id = ?", (str(tg_id),))
        conn.commit()

def migrate_database():
    """Безопасная миграция базы данных - добавляет новые индексы и структуры"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем существование колонки review_request_sent в applications
            cursor.execute("PRAGMA table_info(applications)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'review_request_sent' not in columns:
                cursor.execute("ALTER TABLE applications ADD COLUMN review_request_sent BOOLEAN DEFAULT 0")
                print("✅ Добавлена колонка review_request_sent в таблицу applications")
            
            # Проверяем существование колонки last_admin_notification в applications
            if 'last_admin_notification' not in columns:
                cursor.execute("ALTER TABLE applications ADD COLUMN last_admin_notification DATETIME")
                print("✅ Добавлена колонка last_admin_notification в таблицу applications")
            
            # Проверяем существование индексов
            cursor.execute("PRAGMA index_list(applications)")
            existing_indexes = [row[1] for row in cursor.fetchall()]
            
            # Добавляем недостающие индексы для applications
            if 'idx_applications_tg_id' not in existing_indexes:
                cursor.execute("CREATE INDEX idx_applications_tg_id ON applications(tg_id)")
                print("✅ Добавлен индекс idx_applications_tg_id")
            
            if 'idx_applications_status' not in existing_indexes:
                cursor.execute("CREATE INDEX idx_applications_status ON applications(status)")
                print("✅ Добавлен индекс idx_applications_status")
            
            if 'idx_applications_lesson_date' not in existing_indexes:
                cursor.execute("CREATE INDEX idx_applications_lesson_date ON applications(lesson_date)")
                print("✅ Добавлен индекс idx_applications_lesson_date")
            
            if 'idx_applications_created_at' not in existing_indexes:
                cursor.execute("CREATE INDEX idx_applications_created_at ON applications(created_at)")
                print("✅ Добавлен индекс idx_applications_created_at")
            
            if 'idx_applications_course' not in existing_indexes:
                cursor.execute("CREATE INDEX idx_applications_course ON applications(course)")
                print("✅ Добавлен индекс idx_applications_course")
            
            # Проверяем индексы для courses
            cursor.execute("PRAGMA index_list(courses)")
            existing_course_indexes = [row[1] for row in cursor.fetchall()]
            
            if 'idx_courses_active' not in existing_course_indexes:
                cursor.execute("CREATE INDEX idx_courses_active ON courses(active)")
                print("✅ Добавлен индекс idx_courses_active")
            
            if 'idx_courses_name' not in existing_course_indexes:
                cursor.execute("CREATE INDEX idx_courses_name ON courses(name)")
                print("✅ Добавлен индекс idx_courses_name")
            
            # Проверяем индексы для contacts
            cursor.execute("PRAGMA index_list(contacts)")
            existing_contact_indexes = [row[1] for row in cursor.fetchall()]
            
            if 'idx_contacts_created_at' not in existing_contact_indexes:
                cursor.execute("CREATE INDEX idx_contacts_created_at ON contacts(created_at)")
                print("✅ Добавлен индекс idx_contacts_created_at")
            
            if 'idx_contacts_banned' not in existing_contact_indexes:
                cursor.execute("CREATE INDEX idx_contacts_banned ON contacts(banned)")
                print("✅ Добавлен индекс idx_contacts_banned")
            
            # Проверяем индексы для reviews
            cursor.execute("PRAGMA index_list(reviews)")
            existing_review_indexes = [row[1] for row in cursor.fetchall()]
            
            if 'idx_reviews_created_at' not in existing_review_indexes:
                cursor.execute("CREATE INDEX idx_reviews_created_at ON reviews(created_at)")
                print("✅ Добавлен индекс idx_reviews_created_at")
            
            if 'idx_reviews_is_anonymous' not in existing_review_indexes:
                cursor.execute("CREATE INDEX idx_reviews_is_anonymous ON reviews(is_anonymous)")
                print("✅ Добавлен индекс idx_reviews_is_anonymous")
            
            # Проверяем индексы для archive
            cursor.execute("PRAGMA index_list(archive)")
            existing_archive_indexes = [row[1] for row in cursor.fetchall()]
            
            if 'idx_archive_tg_id' not in existing_archive_indexes:
                cursor.execute("CREATE INDEX idx_archive_tg_id ON archive(tg_id)")
                print("✅ Добавлен индекс idx_archive_tg_id")
            
            if 'idx_archive_status' not in existing_archive_indexes:
                cursor.execute("CREATE INDEX idx_archive_status ON archive(status)")
                print("✅ Добавлен индекс idx_archive_status")
            
            if 'idx_archive_archived_at' not in existing_archive_indexes:
                cursor.execute("CREATE INDEX idx_archive_archived_at ON archive(archived_at)")
                print("✅ Добавлен индекс idx_archive_archived_at")
            
            if 'idx_archive_cancelled_by' not in existing_archive_indexes:
                cursor.execute("CREATE INDEX idx_archive_cancelled_by ON archive(cancelled_by)")
                print("✅ Добавлен индекс idx_archive_cancelled_by")
            
            conn.commit()
            print("✅ Миграция базы данных завершена успешно")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка при миграции базы данных: {e}")
        return False

def get_database_stats():
    """Получает статистику базы данных"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Статистика заявок
        cursor.execute("SELECT COUNT(*) FROM applications WHERE status = 'Ожидает'")
        pending_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM applications WHERE status = 'Назначено'")
        assigned_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM archive")
        archived_count = cursor.fetchone()[0]
        
        # Статистика курсов
        cursor.execute("SELECT COUNT(*) FROM courses WHERE active = 1")
        active_courses = cursor.fetchone()[0]
        
        # Статистика отзывов
        cursor.execute("SELECT COUNT(*) FROM reviews")
        reviews_count = cursor.fetchone()[0]
        
        # Статистика обращений
        cursor.execute("SELECT COUNT(*) FROM contacts WHERE status = 'Ожидает ответа'")
        open_contacts = cursor.fetchone()[0]
        
        return {
            'pending_applications': pending_count,
            'assigned_applications': assigned_count,
            'archived_applications': archived_count,
            'active_courses': active_courses,
            'reviews_count': reviews_count,
            'open_contacts': open_contacts
        }

def get_completed_lessons_without_review_request():
    """Получает завершенные уроки, для которых еще не отправлен запрос на оценку"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, tg_id, course, lesson_date, lesson_link
            FROM applications 
            WHERE status = 'Назначено' 
            AND lesson_date < datetime('now', 'localtime')
            AND review_request_sent = 0
            AND lesson_date IS NOT NULL
            ORDER BY lesson_date DESC
        """)
        return cursor.fetchall()

def mark_review_request_sent(app_id):
    """Отмечает, что запрос на оценку был отправлен для заявки"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE applications 
            SET review_request_sent = 1 
            WHERE id = ?
        """, (app_id,))
        conn.commit()

def get_lessons_completed_after_time(hours=0.5):
    """Получает уроки, завершенные более указанного времени назад"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, tg_id, course, lesson_date, lesson_link
            FROM applications 
            WHERE status = 'Назначено' 
            AND lesson_date < datetime('now', '-{} hours', 'localtime')
            AND review_request_sent = 0
            AND lesson_date IS NOT NULL
            ORDER BY lesson_date DESC
        """.format(hours))
        return cursor.fetchall()

def reset_review_request_status(app_id):
    """Сбрасывает статус отправки запроса на оценку (для тестирования)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE applications 
            SET review_request_sent = 0 
            WHERE id = ?
        """, (app_id,))
        conn.commit()

def can_send_admin_notification(app_id):
    """Проверяет, можно ли отправить уведомление админу (не чаще раза в 24 часа)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT last_admin_notification FROM applications WHERE id = ?", (app_id,))
        result = cursor.fetchone()
        
        if not result or not result[0]:
            return True
        
        last_notification = datetime.fromisoformat(result[0])
        time_diff = datetime.now() - last_notification
        
        return time_diff.total_seconds() >= 24 * 3600  # 24 часа в секундах

def mark_admin_notification_sent(app_id):
    """Отмечает, что уведомление админу было отправлено"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE applications SET last_admin_notification = datetime('now', 'localtime') WHERE id = ?", 
            (app_id,)
        )
        conn.commit()
