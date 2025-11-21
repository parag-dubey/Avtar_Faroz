import os
import sys

# --- 1. Load API Key from .env file ---
try:
    from dotenv import load_dotenv
    # This will find the .env file in your RAG_MODEL folder
    load_dotenv() 
except ImportError:
    print("Error: 'python-dotenv' library not found.")
    print("Please run: pip install python-dotenv")
    sys.exit()

# --- NAYE IMPORTS (NEW IMPORTS) ---
import google.generativeai as genai
from PIL import Image
import io
import base64

# --- 2. Import required libraries ---
try:
    from groq import Groq  # <-- Native Groq client
    from langchain_community.document_loaders import TextLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS
except ImportError:
    print("Error: Required libraries not found.")
    print("Please run: pip install -U groq langchain-community langchain-text-splitters faiss-cpu sentence-transformers")
    sys.exit()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Gemini (Vision) Model
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    vision_model = genai.GenerativeModel('gemini-2.5-flash')
    print("Gemini Vision Model initialized successfully.")
except Exception as e:
    print(f"Error initializing Gemini Vision: {e}")
    sys.exit(1)

# --- 3. Load the API Key and Initialize Groq Client ---
API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    print("Error: GROQ_API_KEY not found.")
    print("Please make sure your API key is in the .env file (e.g., GROQ_API_KEY=your_key_here)")
    sys.exit()

# Initialize the native Groq client
client = Groq(api_key=API_KEY)
# We will use a fast Llama 3 model
GROQ_MODEL = "openai/gpt-oss-20b"

# --- 4. Set File and Index Paths ---
DOC_PATH = "docs/feroze.txt"
INDEX_PATH = "feroze_faiss_index"



# --- 7. RAG Prompt Template (as a simple string) ---
# This is the instruction manual for the LLM

template = """
You are Feroze Azeez, the CEO of Anand Rathi Wealth and a top financial expert in India.
You are NOT an AI assistant. You ARE Feroze Azeez.

Your goal is to advise the user using your specific investment philosophy (Asset Allocation, Risk Management, Structured Products).

*** IMPORTANT INSTRUCTIONS ***
1. **First Person Perspective:** ALWAYS use "I", "me", and "my". Speak as if you are Feroze.
2. **No Third Person:** NEVER refer to Feroze Azeez by name. Instead, say "I suggest..." or "My analysis shows...".
3. **Tone & Style:** Be direct, confident, mathematical, and logic-driven.
   - Avoid filler words like "I hope this helps" or "Thank you for asking".
   - **Keep answers SHORT and PRECISE (under 100 words unless detailed analysis is asked).**
   - Use bullet points for clarity.

4. **🚫 STRICT GUARDRAILS (NO FALSE PROMISES):**
   - **NEVER guarantee returns.** (e.g., Instead of saying "You will get 15%", say "Historically, this asset has delivered ~12-14%").
   - **Always acknowledge Risk.** Remind the user that markets are volatile.
   - Do not give "Buy/Sell" calls on specific stocks unless explicit data is in the Context. Focus on **Strategy** and **Portfolio Health**.

5. **Context Usage:**
   - Use the provided 'Context' to formulate your answer.
   - **If the answer is NOT in the context:** Do NOT make it up. Clearly say, "I don't have specific data on this right now, but typically I look at..." and give a general principle.

6. **The "Feroze" Philosophy:**
   - You dislike speculation (F&O, Crypto). You prefer consistency and compounding.
   - You focus on "Risk-Adjusted Returns" rather than just high returns.

PREVIOUS CONVERSATION:
{chat_history}

Context (My knowledge base):
{context}

Question (from the investor):
{question}

Answer (as Feroze Azeez, short, accurate, and first-person):
"""

# =======================================================
## FUNCTION 1: Knowledge Base Loading (FastAPI will call this once)
# =======================================================
def load_knowledge_base():
    """Builds or loads the FAISS index and returns the retriever object."""
    print("Loading Embedding Model (all-MiniLM-L6-v2)...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    # The logic below is directly from your original code block 5
    if os.path.exists(INDEX_PATH):
        # If index exists, load it
        print(f"Loading existing Knowledge Base from '{INDEX_PATH}'...")
        db = FAISS.load_local(
            INDEX_PATH, 
            embeddings, 
            allow_dangerous_deserialization=True
        )
        print("Knowledge Base loaded successfully.")
    else:
        # If index doesn't exist, build a new one
        print(f"Knowledge Base not found. Building new one from '{DOC_PATH}'...")
        
        if not os.path.exists(DOC_PATH):
            raise FileNotFoundError(f"Error: Document file not found at '{DOC_PATH}'.")

        # 1. Load
        loader = TextLoader(DOC_PATH, encoding="utf-8")
        documents = loader.load()
        print(f"Documents from '{DOC_PATH}' loaded.")
        
        # 2. Split
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        docs = text_splitter.split_documents(documents)
        print(f"Documents split into {len(docs)} chunks.")
        
        # 3. Store
        print("Creating vector database (FAISS)... This may take a moment.")
        db = FAISS.from_documents(docs, embeddings)
        
        # 4. Save
        db.save_local(INDEX_PATH)
        print(f"Knowledge Base built and saved to '{INDEX_PATH}'.")

    # Create the Retriever and return it
    return db.as_retriever(search_kwargs={"k": 3})


# =======================================================
## FUNCTION 2: Response Generation (FastAPI will call this per message)
# =======================================================
def get_feroze_response(user_question: str, retriever, chat_history_str: str) -> str:
    """Retrieves context and generates the AI response using Groq."""
    
    # Check for empty question
    if not user_question:
        return "Please ask a valid question."
        
    # --- This is the new RAG logic (from your original code block 8) ---

    # 1. Retrieve: Get relevant documents from FAISS
    retrieved_docs = retriever.invoke(user_question)
    
    # Format the context string
    context_string = "\n\n".join([doc.page_content for doc in retrieved_docs])

    # 2. Prepare Prompt: Fill the template with context and question
    final_prompt = template.format(chat_history=chat_history_str,context=context_string, question=user_question)

    # 3. Generate: Call Groq API
    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL, # Corrected model used here
            messages=[
                {
                    "role": "user",
                    "content": final_prompt
                }
            ],
            temperature=0.7, 
            max_tokens=8192,
            top_p=1,
            stream=False, # Changed to False for API response compatibility
            stop=None,
        )

        # Return the final content (no streaming print needed)
        return completion.choices[0].message.content
        
    except Exception as e:
        # Better error reporting for the server
        print(f"\nGroq API An error occurred: {e}")
        return "An internal error occurred while generating the AI response."


# --- 6. Vision + RAG Function (Naya function) ---
def get_consult_response(question: str, base64_image: str, retriever, history: str) -> str:
    """
    Generates a response using RAG context, chat history, AND an image.
    """
    print("Processing consultation with text and image...")

    # --- 1. Image ko process karein ---
    try:
        # Base64 string se data header hatayein (jaise "data:image/jpeg;base64,")
        image_data = base64.b64decode(base64_image.split(',')[1])
        # Image ko PIL format mein open karein
        img = Image.open(io.BytesIO(image_data))
    except Exception as e:
        print(f"Error processing image: {e}")
        return "I'm sorry, I couldn't understand the screenshot you sent. Please try again."

    # --- 2. RAG Context Haasil Karein ---
    print("Fetching RAG context for vision query...")
    context_docs = retriever.invoke(question)
    context = "\n\n".join([doc.page_content for doc in context_docs])

    # --- 3. Gemini Vision ke liye Prompt Banayein ---
    prompt_parts = [
        "You are Feroze Azeez AI, a world-class financial advisor.",
        "Analyze the user's question and the provided screenshot. Use the 'Financial Context' to form your answer.",
        "Be concise, professional, and helpful.",
        "---",
        "USER'S QUESTION:",
        question,
        "---",
        "PREVIOUS CHAT HISTORY:",
        history,
        "---",
        "FINANCIAL CONTEXT (From Knowledge Base):",
        context,
        "---",
        "SCREENSHOT:",
        img, # Yahan hum PIL image object pass kar rahe hain
        "---",
        "Based on all this information, provide your expert financial advice:"
    ]

    # --- 4. Gemini Vision ko Call Karein ---
    print("Calling Gemini Vision API...")
    try:
        response = vision_model.generate_content(prompt_parts)
        response_text = response.text
        print("Successfully got response from Gemini Vision.")
    except Exception as e:
        print(f"Error calling Gemini Vision: {e}")
        response_text = "I'm sorry, I encountered an error analyzing the screen. Please ask again."

    return response_text # <-- ✅ ERROR 3 FIX: Jawab ko return kiya

