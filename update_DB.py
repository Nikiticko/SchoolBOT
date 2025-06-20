import sqlite3

conn = sqlite3.connect("data/database.db")
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS archive (
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
        created_at TEXT
    )
""")

conn.commit()
conn.close()
