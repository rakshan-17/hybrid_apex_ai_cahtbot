# APEX AI — Multi-Model Hybrid Assistant

**4 Models · Online & Offline · Voice · File Upload · Web Search**

---

## ⚡ Quick Start

### 1. Add API Keys to `.env`
```
GROQ_API_KEY=gsk_your_groq_key       ← free at console.groq.com
GEMINI_API_KEY=your_gemini_key       ← free at aistudio.google.com
```

### 2. Install (one time only)
```bash
pip install -r requirements.txt
```

### 3. Run
```bash
uvicorn main:app --reload --port 8000
```
Or double-click `run.bat` on Windows.

Open → http://localhost:8000

---

## 🤖 Models

| Model | Type | Needs Internet | Quality |
|---|---|---|---|
| **GROQ** | Llama 3.3 70B | ✅ Yes | ⭐⭐⭐⭐⭐ |
| **GEMINI** | Flash 1.5 | ✅ Yes | ⭐⭐⭐⭐⭐ |
| **PHI-3** | Ollama Local | ❌ No | ⭐⭐⭐ |
| **TINYLLAMA** | Ollama Local | ❌ No | ⭐⭐ |

**Auto-switch:** Goes offline to phi3 automatically when internet is lost.

---

## 🎯 Features

- **Model switcher** — click any model in sidebar, switches instantly
- **File upload** — images (sent to Gemini for vision), text/code files extracted and sent as context
- **Web search** — toggle ON in top bar, uses DuckDuckGo free
- **Voice input** — 🎤 button, works in Chrome/Edge
- **Session history** — sidebar saves all conversations
- **JJK theme** — red/purple/blue cursed energy aesthetic

---

## 🔧 Troubleshooting

| Problem | Fix |
|---|---|
| phi3 fails offline | Run `ollama serve` in a terminal |
| Groq error | Check GROQ_API_KEY in .env |
| Gemini error | Check GEMINI_API_KEY in .env |
| Image upload only works with Gemini | Switch to Gemini model for vision |
| Voice not working | Use Chrome or Edge |
