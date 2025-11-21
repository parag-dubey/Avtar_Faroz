import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    
    
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GOOGLE_SHEET_WEBHOOK = os.getenv("GOOGLE_SHEET_WEBHOOK")
    BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

   