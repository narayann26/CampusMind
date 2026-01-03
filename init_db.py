import sqlite3
from passlib.context import CryptContext

# Same configuration as your app.py
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__ident="2b")

def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # 1. Create Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT,
            school TEXT,
            is_approved INTEGER DEFAULT 0
        )
    ''')

    # 2. Create PYQs Table (Student Hub ke liye zaroori hai)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pyqs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_name TEXT,
            subject_code TEXT,
            year INTEGER,
            file_path TEXT
        )
    ''')

    # 3. Create a Default Admin
    admin_pw = pwd_context.hash("admin123")
    try:
        cursor.execute("INSERT INTO users (username, password, role, is_approved) VALUES (?, ?, ?, ?)",
                       ('admin', admin_pw, 'admin', 1))
        print("✅ Admin created: user='admin', pass='admin123'")
    except sqlite3.IntegrityError:
        print("ℹ️ Admin already exists.")

    conn.commit()
    conn.close()
    print("🚀 Database initialized successfully!")

if __name__ == "__main__":
    init_db()
    