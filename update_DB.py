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
        lesson_date TEXT,
        lesson_link TEXT,
        status TEXT DEFAULT 'Ожидает',
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
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
        lesson_date TEXT,
        lesson_link TEXT,
        status TEXT,
        created_at TEXT,
        cancelled_by TEXT,
        cancel_reason TEXT
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

conn.commit()
conn.close()
print("✅ Новая база создана.")
