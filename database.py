import sqlite3
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # 1. Users Table (With Approval & Course details)
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY, 
                       username TEXT UNIQUE, 
                       password TEXT, 
                       role TEXT, 
                       school TEXT DEFAULT 'SOET',
                       course TEXT,
                       year INTEGER,
                       is_approved INTEGER DEFAULT 0)''') # 0 = Pending, 1 = Approved
    
    # 2. PYQ Metadata Table (Question Papers ki details ke liye)
    cursor.execute('''CREATE TABLE IF NOT EXISTS pyqs 
                      (id INTEGER PRIMARY KEY, 
                       subject_name TEXT, 
                       subject_code TEXT, 
                       year INTEGER, 
                       school TEXT,
                       course TEXT,
                       file_path TEXT)''')

    # Default Admin (Tu khud) - Isko hamesha approved rakhenge
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        hashed_admin = pwd_context.hash("admin123")
        cursor.execute("INSERT INTO users (username, password, role, is_approved) VALUES (?, ?, ?, ?)", 
                       ('admin', hashed_admin, 'admin', 1))
        
        # Ek sample student (Narayan)
        hashed_std = pwd_context.hash("student123")
        cursor.execute("INSERT INTO users (username, password, role, school, course, year, is_approved) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                       ('narayan', hashed_std, 'student', 'SOET', 'B.Tech', 3, 1))
        
        print("✅ CampusMind Database v2.0 Initialized!")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    