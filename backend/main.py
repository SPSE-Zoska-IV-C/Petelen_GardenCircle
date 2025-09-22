# backend/main.py
# Simple FastAPI backend with optional OpenAI proxy for chatbot.
# Configure OPENAI_API_KEY in .env to enable real AI responses.
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY")  # optional
ALLOWED = os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500").split(",")

app = FastAPI(title="GardenCircle Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    message: str

@app.get("/")
async def root():
    return {"status": "ok", "message": "GardenCircle backend running"}

@app.post("/chatbot")
async def chatbot(msg: ChatMessage):
    content = msg.message.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Message is empty")

    # If OPENAI_API_KEY is set, proxy to OpenAI (or any other AI provider)
    if OPENAI_KEY:
        try:
            import openai
            openai.api_key = OPENAI_KEY
            # Use gpt-3.5-turbo or a model available to you
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role":"user","content": content}],
                max_tokens=250,
                temperature=0.7
            )
            reply = resp.choices[0].message.get("content", "").strip()
            return {"reply": reply}
        except Exception as e:
            # graceful fallback
            return {"reply": f"Chyba pri volaní AI: {str(e)}"}
    # Otherwise return a polite demo answer
    demo = f"Ahoj — toto je demo odpoveď. Povedal si: {content}"
    return {"reply": demo}

# Run with: uvicorn main:app --reload --host 127.0.0.1 --port 8000
