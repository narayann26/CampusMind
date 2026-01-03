import sqlite3
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__ident="2b")
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Password 'admin123' hash kar raha hoon
hashed_pw = pwd_context.hash("admin123")

try:
    cursor.execute("INSERT INTO users (username, password, role, is_approved) VALUES (?, ?, ?, ?)", 
                   ('admin', hashed_pw, 'admin', 1))
    conn.commit()
    print("Admin Created: username='admin', password='admin123'")
except:
    print("Admin already exists or Error!")
finally:
    conn.close()