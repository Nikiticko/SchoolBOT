import sqlite3
from datetime import datetime

DB_NAME = "data/database.db"

def get_connection():
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
                lesson_date TEXT,
                lesson_link TEXT,
                status TEXT DEFAULT 'Ожидает',
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
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


def archive_application(app_id):
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
        row = cursor.fetchone()
        if not row:
            return False  # <-- важно

        cursor.execute("""
            INSERT INTO archive (
                tg_id, parent_name, student_name, age, contact, course,
                lesson_date, lesson_link, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, row[1:])  # без ID

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
