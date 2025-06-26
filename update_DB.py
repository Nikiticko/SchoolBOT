import sqlite3
import os

DB_PATH = "data/database.db"

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print("🗑 Удалена старая база данных")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE applications (
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
        reminder_sent BOOLEAN DEFAULT 0
    )
""")

cursor.execute("""
    CREATE TABLE archive (
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
        cancelled_by TEXT,
        comment TEXT
    )
""")

cursor.execute("""
    CREATE TABLE courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        description TEXT,
        active BOOLEAN DEFAULT 1
    )
""")

cursor.execute("""
    CREATE TABLE contacts (
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

# Создаем индексы для улучшения производительности
cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_lesson_date ON applications(lesson_date)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_created_at ON applications(created_at)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_archive_lesson_date ON archive(lesson_date)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_archive_created_at ON archive(created_at)")

conn.commit()
conn.close()
print("✅ Новая база создана с типом DATETIME для lesson_date и created_at.")
