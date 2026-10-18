# Sketchbook · 
*Little Words Matter* 

An English-learning chatbot for children under 7. **Dora** is a doll friend who teaches one word at a time, notices feelings, and switches between learning, chatting, play, and support. Stars unfold an origami crane as the child grows.

**Live demo:** https://sketchbook-english-chatbot.onrender.com  
Design: [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) · Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Features

- **Dora**: system persona, greetings, and a person with friendly tone.
- **Levels L1–L3**: Little Sprout → Word Explorer → Sentence Star (6 and 14 stars).
- **Instant praise**: saying the current target (case/punctuation tolerant) answers from a rotating template.
- **Word of the day**: Home card from the chat curriculum and today’s date; 🔊 uses `speechSynthesis`; Practice sets that word as `target` and opens chat.
- **Modes**: learn / chat / engage / support, shown with a reason.
- **Insight**: cognitive bar plus awareness, confidence, curiosity, kindness.
- **Play**: server-checked picture/sentence quiz.
- **Voice**: Web Speech API out and optional microphone in.
- **Safety**: harm, privacy, and rude-word guards skip the LLM.
- **Latency badge** on every chat reply; Groq capped then rule fallback.

## Requirement checklist

| Requirement | Status |

| Progressive L1 / L2 / L3 | Yes — stars, `POOLS`, quiz `REG`, crane |
| Child mode detection (learning, conversation, engagement, support) | Yes — `learn` / `chat` / `engage` / `support` |
| Social-emotional learning | Yes — mood, support breaths, SEL meters, CSE Insight |
| Context-aware responses | Yes — prompt has level, mood, misses, last 6 turns, target word |
| End-to-end under 2 s | Yes — 1.4 s Groq cap, fallback, instant praise; smoke test |
| Live deployed URL | Render via `render.yaml` |


## Stack
Python, FastAPI, Groq LLM, SQLite, plain HTML/CSS/JavaScript, hosted on Render.

## Local setup

Python 3.11+. From this directory (`sketchbook/sketchbook/` if the repo is nested):


python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        (# Mac/Linux: cp .env.example .env)
python -m uvicorn app.main:app --reload


Open http://127.0.0.1:8000. Without `GROQ_API_KEY` the app still runs on `engine.fallback`.

python tests/smoke.py                       # local
python tests/smoke.py https://THE-URL      # live, prints latency

## Deploying ( Render ) 
1. Push the repo to GitHub.
2. Render: New, Web Service, select the repo, Python 3, Free plan.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables `GROQ_API_KEY` and `GROQ_MODEL`.
6. Open the Render URL. `/health` should return **ok**.

The free plan sleeps when idle, so the first request after a quiet period can be slow.


## Environment variables


| Variable | Purpose | Typical value |

| `GROQ_API_KEY` | Groq bearer token; empty disables the LLM | 
| `GROQ_MODEL` | Chat model id | `llama-3.1-8b-instant` |
| `LLM_TIMEOUT` | Groq read timeout in seconds | `1.4` |
| `DB_PATH` | SQLite file | `sketchbook.db` |
| `PORT` | Set by Render for Uvicorn | 
| `PYTHON_VERSION` | Render runtime pin | `3.11.9` |


## Project structure


app/
  main.py       routes
  engine.py     safety, modes, stars, SEL, target match, instant praise, fallback
  llm.py        Groq client
  content.py    curriculum + quiz items
  db.py         SQLite
static/
  index.html · style.css · app.js · img/mascot.webp
docs/
  ARCHITECTURE.md · SYSTEM_DESIGN.md · architecture.svg · VIDEO_SCRIPT.md
tests/
  smoke.py
render.yaml · requirements.txt · .env.example
```
