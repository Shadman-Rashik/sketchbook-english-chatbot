# Sketchbook · *Little Words Matter*

An English-learning chatbot for children under 7. **Dora** is a doll friend who teaches one word at a time, notices feelings, and switches between learning, chatting, play, and support. Stars unfold an origami crane as the child grows.

**Live demo:** `<paste your Render URL here>`  
Design: [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) · Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Features

- **Dora**: system persona, greetings, chat header, and Home copy.
- **Levels L1–L3**: Little Sprout → Word Explorer → Sentence Star (6 and 14 stars).
- **Instant praise**: saying the current target (case/punctuation tolerant) answers from a rotating template with **no LLM call**.
- **Word of the day**: Home card from the chat curriculum and today’s date; 🔊 uses `speechSynthesis`; Practice sets that word as `target` and opens chat.
- **Modes**: learn / chat / engage / support, shown with a reason.
- **CSE Insight**: cognitive bar plus awareness, confidence, curiosity, kindness.
- **Play**: server-checked picture/sentence quiz.
- **Voice**: Web Speech API out and optional microphone in.
- **Safety**: harm, privacy, and rude-word guards skip the LLM.
- **Latency badge** on every chat reply; Groq capped then rule fallback.

## Requirement checklist

| Requirement | Status |
|---|---|
| Progressive L1 / L2 / L3 | Yes — stars, `POOLS`, quiz `REG`, crane |
| Child mode detection (learning, conversation, engagement, support) | Yes — `learn` / `chat` / `engage` / `support` |
| Social-emotional learning | Yes — mood, support breaths, SEL meters, CSE Insight |
| Context-aware responses | Yes — prompt has level, mood, misses, last 6 turns, target word |
| End-to-end under 2 s | Yes — 1.4 s Groq cap, fallback, instant praise; smoke test |
| Live deployed URL | Render via `render.yaml` |

## Local setup

Python 3.11+. From this directory (`sketchbook/sketchbook/` if the repo is nested):

```bash
python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\activate
# Mac/Linux:             source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env        # Mac/Linux: cp .env.example .env
python -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. Without `GROQ_API_KEY` the app still runs on `engine.fallback`. Optional mascot file: `static/img/mascot.webp` (crane fallback if missing).

```bash
python tests/smoke.py                       # local
python tests/smoke.py https://YOUR-URL      # live, prints latency
```

## Environment variables

Copy `.env.example`. Do not commit real keys.

| Variable | Purpose | Typical value |
|---|---|---|
| `GROQ_API_KEY` | Groq bearer token; empty disables the LLM | *(your key)* |
| `GROQ_MODEL` | Chat model id | `llama-3.1-8b-instant` |
| `LLM_TIMEOUT` | Groq read timeout in seconds | `1.4` |
| `DB_PATH` | SQLite file | `sketchbook.db` |
| `PORT` | Set by Render for Uvicorn | *(platform)* |
| `PYTHON_VERSION` | Render runtime pin | `3.11.9` |

## Render deployment

1. Push the repo to GitHub.
2. [render.com](https://render.com) → **New + → Web Service** → connect the repo (`render.yaml` is included).
3. Runtime **Python 3**. Build: `pip install -r requirements.txt`. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
4. If the app lives in a nested folder, set that folder as the service root so `app.main:app` resolves.
5. Environment: `GROQ_API_KEY` (secret), `PYTHON_VERSION=3.11.9`. Optional: `GROQ_MODEL`, `LLM_TIMEOUT`, `DB_PATH`.
6. Deploy, open the URL, run `python tests/smoke.py <URL>`.
7. Optional: UptimeRobot (or similar) `GET <URL>/api/health` every 5 minutes to reduce free-tier cold starts. Free disk is ephemeral, so SQLite progress can reset on restart.

## Project structure

```
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
