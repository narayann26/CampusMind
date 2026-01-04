import os
import sqlite3
from fastapi import FastAPI, UploadFile, File, Form, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from groq import Groq
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# CORS Middleware (Jo 'null' origin issue solve karega)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATABASE INITIALIZATION (Render ke liye zaroori) ---
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    # Users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT, school TEXT, is_approved INTEGER)''')
    # PYQs table
    cursor.execute('''CREATE TABLE IF NOT EXISTS pyqs 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, subject_name TEXT, subject_code TEXT, year INTEGER, file_path TEXT)''')
    # Admin check (Agar admin nahi hai toh bana do)
    cursor.execute("SELECT * FROM users WHERE role='admin'")
    if not cursor.fetchone():
        admin_pass = CryptContext(schemes=["bcrypt"], deprecated="auto").hash("admin123")
        cursor.execute("INSERT INTO users (username, password, role, is_approved) VALUES (?, ?, ?, ?)", ('admin', admin_pass, 'admin', 1))
    conn.commit()
    conn.close()

init_db()

if not os.path.exists("documents"):
    os.makedirs("documents")
app.mount("/documents", StaticFiles(directory="documents"), name="documents")

# --- FIX: Bcrypt ident added ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__ident="2b")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
FAISS_INDEX_PATH = "faiss_index"

class LoginRequest(BaseModel):
    username: str
    password: str

# --- ENDPOINTS ---

@app.post("/login")
async def login(req: LoginRequest):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT password, role, is_approved FROM users WHERE username = ?", (req.username,))
    user = cursor.fetchone()
    conn.close()

    if user and pwd_context.verify(req.password, user[0]):
        role = user[1]
        is_approved = user[2]
        
        if role != 'admin' and is_approved == 0:
            raise HTTPException(status_code=403, detail="Approval Pending by Admin!")
            
        return {"username": req.username, "role": role}
    
    raise HTTPException(status_code=401, detail="Invalid Credentials!")

@app.post("/register_student")
async def register_student(data: dict = Body(...)):
    u, p = data.get("username"), pwd_context.hash(data.get("password"))
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password, role, is_approved) VALUES (?, ?, 'student', 1)", (u, p))
        conn.commit()
        return {"message": "Success"}
    except:
        raise HTTPException(status_code=400, detail="Username exists!")
    finally:
        conn.close()

@app.post("/register_staff")
async def register_staff(data: dict = Body(...)):
    u, p = data.get("username"), pwd_context.hash(data.get("password"))
    s = data.get("school", "SOET")
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password, role, school, is_approved) VALUES (?, ?, 'staff', ?, 0)", (u, p, s))
        conn.commit()
        return {"message": "Success"}
    except:
        raise HTTPException(status_code=400, detail="Username exists!")
    finally:
        conn.close()

@app.get("/admin/analytics")
async def get_analytics():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE role='student'")
    s_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE role='staff' AND is_approved=1")
    t_count = cursor.fetchone()[0]
    conn.close()
    return {"total_students": s_count, "total_staff": t_count}

@app.get("/admin/pending_staff")
async def get_pending():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, school FROM users WHERE role='staff' AND is_approved=0")
    staff = [{"id": r[0], "username": r[1], "school": r[2]} for r in cursor.fetchall()]
    conn.close()
    return staff

@app.post("/admin/approve_user")
async def approve_user(data: dict = Body(...)):
    user_id = data.get("user_id")
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_approved = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"status": "User Approved"}

@app.post("/admin/upload_pyq")
async def upload_pyq(subject_name: str = Form(...), subject_code: str = Form(...), year: int = Form(...), course: str = Form(...), file: UploadFile = File(...)):
    file_path = f"documents/pyqs/{file.filename}"
    os.makedirs("documents/pyqs", exist_ok=True)
    with open(file_path, "wb") as f: f.write(await file.read())
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO pyqs (subject_name, subject_code, year, file_path) VALUES (?, ?, ?, ?)", (subject_name, subject_code, year, file_path))
    conn.commit()
    conn.close()
    loader = PyPDFLoader(file_path)
    pages = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = text_splitter.split_documents(pages)
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    if os.path.exists(FAISS_INDEX_PATH):
        vector_db = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
        vector_db.add_documents(chunks)
    else:
        vector_db = FAISS.from_documents(chunks, embeddings)
    vector_db.save_local(FAISS_INDEX_PATH)
    return {"status": "Success"}

@app.post("/admin/upload_doc")
async def upload_general_doc(doc_type: str = Form(...), file: UploadFile = File(...)):
    folder = f"documents/{doc_type.lower().replace(' ', '_')}"
    os.makedirs(folder, exist_ok=True)
    file_path = f"{folder}/{file.filename}"
    with open(file_path, "wb") as f: f.write(await file.read())
    if file.filename.endswith('.pdf'): loader = PyPDFLoader(file_path)
    else:
        from langchain_community.document_loaders import TextLoader
        loader = TextLoader(file_path)
    pages = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = text_splitter.split_documents(pages)
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    if os.path.exists(FAISS_INDEX_PATH):
        vector_db = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
        vector_db.add_documents(chunks)
    else:
        vector_db = FAISS.from_documents(chunks, embeddings)
    vector_db.save_local(FAISS_INDEX_PATH)
    return {"status": "Success"}

@app.get("/student/search_pyqs")
async def search(query: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT subject_name, subject_code, year, file_path FROM pyqs WHERE subject_name LIKE ? OR subject_code LIKE ?", (f'%{query}%', f'%{query}%'))
    results = [{"name": r[0], "code": r[1], "year": r[2], "path": r[3]} for r in cursor.fetchall()]
    conn.close()
    return results

@app.post("/chat")
async def chat(data: dict = Body(...)):
    query = data.get("query")
    role = data.get("role", "student")
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    if not os.path.exists(FAISS_INDEX_PATH): context = "No documents uploaded yet."
    else:
        vector_db = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
        docs = vector_db.similarity_search(query, k=7)
        context = "\n---\n".join([d.page_content for d in docs])
    system_prompt = f"You are CampusMind AI. User is a {role}. ONLY answer based on context. Prioritize 2026 dates. Context: {context}"
    response = client.chat.completions.create(messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": query}], model="llama-3.3-70b-versatile")
    return {"response": response.choices[0].message.content}
