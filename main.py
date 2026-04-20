"""
APEX AI — Multi-Model Hybrid Assistant
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Online  → Groq (Llama 3.3 70B) | Gemini Flash
Offline → Ollama phi3 | Ollama tinyllama
Search  → DuckDuckGo (free)
Files   → Images + Documents (text extraction)

Run: uvicorn main:app --reload --port 8000
"""

import os, socket, base64, httpx
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from duckduckgo_search import DDGS

load_dotenv()

# ── API Keys & Config ──────────────────────────────────────────────────────────
GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")

GROQ_URL        = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL      = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
OLLAMA_URL      = "http://localhost:11434/api/generate"

GROQ_MODEL      = "llama-3.3-70b-versatile"
GEMINI_MODEL    = "gemini-2.5-flash"

SYSTEM_PROMPT   = (
    "You are APEX — a powerful, intelligent AI assistant. "
    "Be precise, helpful, and clear. Format responses with proper structure."
)

app = FastAPI(title="APEX AI", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions: dict[str, list[dict]] = {}

UPLOAD_DIR = "backend/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── Internet Check ─────────────────────────────────────────────────────────────
def is_online() -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(("8.8.8.8", 53))
        s.close()
        return True
    except:
        return False

# ── Web Search ─────────────────────────────────────────────────────────────────
def web_search(query: str, max_results: int = 4) -> str:
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(f"- {r['title']}: {r['body'][:220]}")
        return "Web Search Results:\n" + "\n".join(results) if results else "(No results)"
    except Exception as e:
        return f"(Search failed: {e})"

# ── Groq ───────────────────────────────────────────────────────────────────────
async def ask_groq(messages: list[dict]) -> str:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024
    }
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(GROQ_URL, headers=headers, json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()

# ── Gemini ─────────────────────────────────────────────────────────────────────
async def ask_gemini(messages: list[dict], image_b64: str = None, image_mime: str = None) -> str:
    parts = []

    # Build conversation context as text
    ctx = ""
    for m in messages[:-1]:  # all but last
        role = "User" if m["role"] == "user" else "Model"
        ctx += f"{role}: {m['content']}\n"
    if ctx:
        parts.append({"text": ctx})

    # Last user message
    last = messages[-1]["content"]
    if image_b64 and image_mime:
        parts.append({"inline_data": {"mime_type": image_mime, "data": image_b64}})
    parts.append({"text": last})

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024}
    }
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(GEMINI_URL, headers={"x-goog-api-key": GEMINI_API_KEY}, json=payload)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

# ── Ollama ─────────────────────────────────────────────────────────────────────
async def ask_ollama(messages: list[dict], model: str) -> str:
    prompt = ""
    for m in messages:
        role = "User" if m["role"] == "user" else "Assistant"
        prompt += f"{role}: {m['content']}\n"
    prompt += "Assistant:"

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 512}
    }
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(OLLAMA_URL, json=payload)
        r.raise_for_status()
        reply = r.json().get("response", "").strip()
        if not reply:
            raise ValueError("Empty response from Ollama")
        return reply

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
def home():
    return FileResponse("backend/templates/index.html")

@app.get("/status")
def status():
    online = is_online()
    return {
        "online": online,
        "groq_ok": bool(GROQ_API_KEY),
        "gemini_ok": bool(GEMINI_API_KEY),
    }

@app.post("/chat")
async def chat(
    message: str = Form(...),
    session_id: str = Form(default="default"),
    model: str = Form(default="auto"),        # groq | gemini | phi3 | tinyllama | auto
    use_search: bool = Form(default=False),
    file: UploadFile = File(default=None)
):
    history = sessions.setdefault(session_id, [])

    # ── Handle file upload ───────────────────────────────────────────────────
    image_b64   = None
    image_mime  = None
    file_text   = ""

    if file and file.filename:
        raw = await file.read()
        fname = file.filename.lower()
        mime  = file.content_type or ""

        if mime.startswith("image/"):
            image_b64  = base64.b64encode(raw).decode()
            image_mime = mime
            file_text  = f"[Image attached: {file.filename}]"
        elif fname.endswith(".txt") or fname.endswith(".md") or fname.endswith(".py") or \
             fname.endswith(".js") or fname.endswith(".html") or fname.endswith(".css") or \
             fname.endswith(".json") or fname.endswith(".csv"):
            try:
                file_text = f"\n\n[File: {file.filename}]\n{raw.decode('utf-8', errors='ignore')[:3000]}"
            except:
                file_text = f"[Could not read file: {file.filename}]"
        else:
            file_text = f"[File attached: {file.filename} — unsupported type for text extraction]"

    # ── Web search ───────────────────────────────────────────────────────────
    search_ctx = ""
    if use_search and is_online():
        search_ctx = web_search(message)

    # ── Build user message ───────────────────────────────────────────────────
    user_content = message
    if file_text:
        user_content += file_text
    if search_ctx:
        user_content += f"\n\n[Web Context]\n{search_ctx}"

    history.append({"role": "user", "content": user_content})
    trimmed  = history[-20:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + trimmed
    online   = is_online()

    # ── Model routing ────────────────────────────────────────────────────────
    reply      = ""
    used_model = model
    error_log  = []

    # AUTO mode: prefer Groq online, phi3 offline
    if model == "auto":
        model = "groq" if online else "phi3"

    if model == "groq":
        if not online:
            return JSONResponse(status_code=400, content={"error": "Groq requires internet. Switch to phi3 or tinyllama."})
        if not GROQ_API_KEY:
            return JSONResponse(status_code=400, content={"error": "GROQ_API_KEY missing in .env"})
        try:
            reply = await ask_groq(messages)
            used_model = "groq"
        except Exception as e:
            error_log.append(f"Groq: {e}")
            # fallback
            try:
                reply = await ask_ollama(trimmed, "phi3:latest")
                used_model = "phi3_fallback"
            except Exception as e2:
                error_log.append(f"phi3 fallback: {e2}")

    elif model == "gemini":
        if not online:
            return JSONResponse(status_code=400, content={"error": "Gemini requires internet."})
        if not GEMINI_API_KEY:
            return JSONResponse(status_code=400, content={"error": "GEMINI_API_KEY missing in .env"})
        try:
            reply = await ask_gemini(trimmed, image_b64, image_mime)
            used_model = "gemini"
        except Exception as e:
            error_log.append(f"Gemini: {e}")

    elif model == "phi3":
        try:
            reply = await ask_ollama(trimmed, "phi3:latest")
            used_model = "phi3"
        except Exception as e:
            error_log.append(f"phi3: {e}")
            # try tinyllama as fallback
            try:
                reply = await ask_ollama(trimmed, "tinyllama:latest")
                used_model = "tinyllama_fallback"
            except Exception as e2:
                error_log.append(f"tinyllama fallback: {e2}")

    elif model == "tinyllama":
        try:
            reply = await ask_ollama(trimmed, "tinyllama:latest")
            used_model = "tinyllama"
        except Exception as e:
            error_log.append(f"tinyllama: {e}")

    if not reply:
        return JSONResponse(
            status_code=500,
            content={"error": "All models failed: " + " | ".join(error_log)}
        )

    history.append({"role": "assistant", "content": reply})
    sessions[session_id] = history[-40:]

    return {
        "reply":      reply,
        "model":      used_model,
        "searched":   use_search and bool(search_ctx),
        "has_image":  image_b64 is not None,
        "session_id": session_id,
    }

@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    sessions.pop(session_id, None)
    return {"cleared": True}

@app.get("/health")
def health():
    return {"status": "running", "online": is_online(), "sessions": len(sessions)}
