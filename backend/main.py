import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles 
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sys
import requests
import bcrypt
import json
import os
import re  
import uuid  
import edge_tts 
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from jose import JWTError, jwt
from dotenv import load_dotenv


# Load Environment Variables
load_dotenv()

GOOGLE_SHEET_WEBHOOK = os.getenv("GOOGLE_SHEET_WEBHOOK")
JWT_SECRET = os.getenv("JWT_SECRET", "farozazeezsecret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Import RAG Functions
try:
    from rag_model import load_knowledge_base, get_feroze_response, get_consult_response
except ImportError:
    print("Error: Could not import functions from rag_core.py.")
    sys.exit(1)

# --- 1. FastAPI App Initialization ---
app = FastAPI()

if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Chat History Storage
chat_histories: Dict[str, List[Dict[str, str]]] = {}
CHAT_HISTORY_LIMIT = 15 

# --- 2. CORS Setup ---
origins = ["*"] 

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. Knowledge Base Loading ---
print("Loading Knowledge Base...")
try:
    retriever = load_knowledge_base()
    print("✅ Knowledge Base Loaded.")
except Exception as e:
    print(f"FATAL ERROR loading KB: {e}")
    sys.exit(1)

# -------------------------------
# Models
# -------------------------------
class RegisterRequest(BaseModel):
    Email: str
    Password: str
    Name: str

class LoginRequest(BaseModel):
    Email: str
    Password: str

class ChatRequest(BaseModel):
    question: str

class ConsultRequest(BaseModel):
    question: str 
    screenshot: str 

class ChatResponse(BaseModel):
    answer: str
    audio_url: Optional[str] = None

# -------------------------------
# 🧹 Audio & Text Cleaning
# -------------------------------
def clean_text_for_audio(text: str) -> str:
    text = text.replace('|', ' ')
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'#+', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'[-_`]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

async def generate_audio_file(text: str) -> str:
    try:
        clean_text = clean_text_for_audio(text)
        print(f"Speaking: {clean_text[:50]}...") 

        filename = f"reply_{uuid.uuid4()}.mp3"
        file_path = os.path.join("static", filename)
        voice = "en-IN-PrabhatNeural"
        
        communicate = edge_tts.Communicate(clean_text, voice)
        await communicate.save(file_path)
        
        return f"/static/{filename}"
    except Exception as e:
        print(f"Audio Error: {e}")
        return None

# -------------------------------
# Utility Functions
# -------------------------------
def normalize_email(email: str) -> str:
    return (email or "").strip().lower()

def get_sheet_data(sheet_name: str) -> List[Dict[str, str]]:
    try:
        url = f"{GOOGLE_SHEET_WEBHOOK}?sheet={sheet_name}"
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        response_json = res.json()
        if response_json.get("status") == "success":
            return response_json.get("data", []) 
        else:
            return []
    except Exception as e:
        print(f"Error fetching sheet: {e}")
        return []

def append_to_sheet(sheet_name: str, data: Dict[str, Any]):
    try:
        url = f"{GOOGLE_SHEET_WEBHOOK}?sheet={sheet_name}"
        headers = {"Content-Type": "application/json"}
        # Ensure no null values
        clean_data = {k: (v if v is not None else "") for k, v in data.items()}
        res = requests.post(url, json=clean_data, headers=headers, timeout=10)
        return res.json()
    except Exception as e:
        print(f"Error appending to sheet: {e}")
        return {"status": "error"}

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

# 🔥 JWT CREATION FUNCTION
def create_jwt(email: str) -> str:
    payload = {"email": email, "exp": datetime.utcnow() + timedelta(days=1)}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

def find_user_by_email(email: str) -> Optional[Dict[str, str]]:
    email = normalize_email(email)
    users = get_sheet_data("users")
    for u in users:
        if normalize_email(u.get("Email") or "") == email:
            return u
    return None

def format_history_for_prompt(history: List[Dict[str, str]]) -> str:
    if not history:
        return "No previous conversation."
    lines = []
    for msg in history[-CHAT_HISTORY_LIMIT:]:
        role = "User" if msg.get("role") == "user" else "Feroze AI"
        lines.append(f"{role}: {msg.get('content')}")
    return "\n".join(lines)

# -------------------------------
# 🔒 STRICT JWT SECURITY LOGIC
# -------------------------------
oauth2_scheme = HTTPBearer()

async def get_current_user(token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token_str = token.credentials
        
        # 🔥 STRICT MODE: Sirf Asli JWT chalega (No tricks)
        payload = jwt.decode(token_str, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("email")
        
        if email is None:
            raise credentials_exception
            
        return email # Return valid email from token

    except JWTError:
        print("⚠️ JWT Validation Failed")
        raise credentials_exception

# -------------------------------
# Auth Routes
# -------------------------------
@app.post("/register")
async def register_user(req: RegisterRequest):
    Email = normalize_email(req.Email)
    existing = find_user_by_email(Email)
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Password Hash karke Sheet me bhejo
    hashed_pw = hash_password(req.Password)
    
    user_data = {
        "Name": req.Name,
        "Email": Email,
        "Password_Hash": hashed_pw,
        "Created_At": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    append_to_sheet("users", user_data)
    return {"message": "✅ Registration successful", "user": {"Name": req.Name, "Email": Email}}

@app.post("/login")
def login_user(req: LoginRequest):
    email = normalize_email(req.Email)
    
    # 1. Sheet se user dhoondo
    user = find_user_by_email(email)
    
    # 2. Password Verify Karo
    if not user or not verify_password(req.Password, user.get("Password_Hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # 3. Asli JWT Token banao
    token = create_jwt(email)
    
    return {
        "message": "✅ Login successful",
        "token": token, # Yeh Token frontend ko bhejo
        "user": {"Name": user.get("Name"), "Email": email}
    }

# -------------------------------
# 💬 Secure Chat Endpoints
# -------------------------------

# -------------------------------
# 💬 Secure Chat Endpoints (Updated)
# -------------------------------

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest, 
    current_user: str = Depends(get_current_user) # 🔒 Locked
):
    print(f"--> User ({current_user}) asked: {request.question}")

    # 1. History Load
    user_history = chat_histories.get(current_user, [])
    
    # 🔥 Greeting Logic Check
    clean_q = request.question.strip().lower()
    GREETINGS = ["hi", "hello", "hy", "hey", "hola", "namaste", "greetings"]
    
    # Agar Greeting hai to AI ko mat call karo
    if clean_q in GREETINGS or (len(clean_q) < 5 and "hi" in clean_q):
        response_text = "Hello! I am Feroze Azeez. How can I assist you with your portfolio today?"
        # Greeting me history print karne ki zaroorat nahi hai
    else:
        # 🔥 Normal Question: Last 15 Messages nikal kar bhejo
        recent_history = user_history[-CHAT_HISTORY_LIMIT:] 
        history_str = format_history_for_prompt(recent_history)
        
        # ✅ PRINT: Ye terminal me dikhayega ki AI ko pichli kya baat yaad hai
        print("\n" + "="*30)
        print(f"🧠 MEMORY SENT TO AI ({current_user}):")
        print(history_str)
        print("="*30 + "\n")
        
        # RAG Response
        response_text = get_feroze_response(request.question, retriever, history_str)

    # 3. Save History (Greeting ho ya Question, save zaroor karo)
    user_history.append({"role": "user", "content": request.question})
    user_history.append({"role": "assistant", "content": response_text})
    chat_histories[current_user] = user_history 
    
    print(f"<-- Text Answer: {response_text[:50]}...")

    # 4. Audio Generation
    clean_speech = clean_text_for_audio(response_text)
    audio_link = await generate_audio_file(clean_speech)
    
    return ChatResponse(answer=response_text, audio_url=audio_link)


@app.post("/api/consult", response_model=ChatResponse)
async def consult_endpoint(
    request: ConsultRequest, 
    current_user: str = Depends(get_current_user) # 🔒 Locked
):
    print(f"--> Consult Request from: {current_user}")

    # 1. History Load
    user_history = chat_histories.get(current_user, [])
    
    
    # 🔥 Last 15 messages logic yahan bhi
    recent_history = user_history[-CHAT_HISTORY_LIMIT:]
    history_str = format_history_for_prompt(recent_history)

    # ✅ PRINT HISTORY (Vision ke liye bhi zaroori hai)
    print("\n" + "="*30)
    print(f"🧠 VISION MEMORY CONTEXT ({current_user}):")
    print(history_str)
    print("="*30 + "\n")

    # 2. Vision Response
    try:
        response_text = get_consult_response(
            request.question, 
            request.screenshot, 
            retriever, 
            history_str
        )
    except Exception as e:
        print(f"Vision Error: {e}")
        raise HTTPException(status_code=500, detail="Error processing image.")

    # 3. Save History
    user_history.append({"role": "user", "content": request.question})
    user_history.append({"role": "assistant", "content": response_text})
    chat_histories[current_user] = user_history

    # 4. Audio Generation
    clean_speech = clean_text_for_audio(response_text)
    audio_link = await generate_audio_file(clean_speech)

    return ChatResponse(answer=response_text, audio_url=audio_link)

# ==========================================
# 👇 FRONTEND SERVING CODE (Ye End me Paste karein)
# ==========================================

# 1. Main Website Route
@app.get("/")
async def read_root():
    # Jab koi website open karega, index.html file bhej do
    return FileResponse('static/index.html')

# 2. React Router Support (Catch-All)
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    # Check karo agar file static folder me hai (jaise image.png, logo.ico)
    file_path = os.path.join("static", full_path)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    
    # Agar file nahi mili, toh wapis index.html bhejo (React handle karega)
    return FileResponse('static/index.html')


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)