import sqlite3
from passlib.context import CryptContext

# Same configuration as app.py
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__ident="2b")

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# 1. Table dobara banate hain (clean start)
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
               (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                username TEXT UNIQUE, 
                password TEXT, 
                role TEXT, 
                school TEXT, 
                is_approved INTEGER)''')

# 2. Hashed Password banate hain
hashed_pw = pwd_context.hash("admin123")

# 3. Admin insert karte hain
try:
    cursor.execute("INSERT INTO users (username, password, role, is_approved) VALUES (?, ?, ?, ?)", 
                   ('admin', hashed_pw, 'admin', 1))
    conn.commit()
    print("✅ New Admin created: admin / admin123")
except Exception as e:
    print("❌ Error:", e)

conn.close()