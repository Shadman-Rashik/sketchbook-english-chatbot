# Sketchbook · *Little Words Matter*

An AI-powered English-learning chatbot for children under 7. Meet **Dilly**, a doll friend who teaches words step by step, notices how the child feels, and knows when to stop teaching and just play.

**Live demo:** `<paste your Render URL here>`  ·  Design doc: [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md)  ·  Architecture: [docs/architecture.png](docs/architecture.png)

## Features

- **Progressive levels**: L1 first words → L2 numbers, opposites, greetings → L3 tiny sentences. Stars unlock levels; an origami crane “unfolds” as the child grows.
- **Child-mode detection**: learn, chat, engage (games) and support (calming), shown live in the chat header with the reason.
- **Social & Emotional Learning**: mood check-in, breathing bubble, kind feedback, four SEL meters and a *CSE Insight* card (Cognitive + Social-Emotional).
- **Context-aware**: replies adapt to level, mood, hard words and recent messages.
- **< 2 s responses**: Groq LLM with a 1.4 s cap and an instant rule-based fallback; the latency of every reply is displayed.
- **Voice**: Dilly speaks (Web Speech API) and children can answer with the microphone.
- **Child-safe**: input guard for harm, privacy and rude words; no accounts, no personal data.
- Live clock and date, clay-style pastel UI, responsive mobile-first layout.

## Run locally

Requirements: Python 3.11+.

```bash
python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\activate      Mac/Linux:  source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env        # Mac/Linux: cp .env.example .env   → then paste your GROQ_API_KEY inside .env
python -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. Without a `GROQ_API_KEY` the app still works using the rule-based brain.
Get a free key at https://console.groq.com.

Put the mascot image at `static/img/mascot.webp` (a crane is shown if it is missing).

## Test

With the server running:

```bash
python tests/smoke.py                       # local
python tests/smoke.py https://YOUR-URL      # live deployment, also prints latency
```

## Deploy (Render, free)

1. Push this repo to GitHub.
2. render.com → **New + → Web Service** → connect the repo (Render also reads `render.yaml`).
3. Runtime **Python 3**, Build `pip install -r requirements.txt`, Start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
4. Environment → add `GROQ_API_KEY` (your key) and `PYTHON_VERSION` = `3.11.9`.
5. Deploy, then open the URL and run `python tests/smoke.py <URL>`.
6. Optional: create a free UptimeRobot monitor on `<URL>/api/health` (5-minute interval) to prevent cold starts.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness + whether the LLM is configured |
| GET | `/api/state?session_id=` | progress, SEL meters, insight |
| POST | `/api/chat` | `{session_id, message, name}` → reply, mode, reason, latency_ms, state |
| POST | `/api/mood` | mood check-in |
| GET | `/api/quiz?session_id=` | next quiz item for the child's level |
| POST | `/api/answer` | check an answer, award stars, level up |

## Project layout

```
app/        main.py (routes) · engine.py (safety, modes, levels, SEL) · llm.py (Groq client)
            content.py (curriculum, quiz items) · db.py (SQLite)
static/     index.html · style.css · app.js · img/mascot.webp
docs/       SYSTEM_DESIGN.md · architecture.svg/.png
tests/      smoke.py
```

## Trade-offs in one paragraph

A hosted LLM (Groq) is used because a deployed URL cannot reach a laptop GPU; rules handle safety, mode detection and the latency guarantee; SQLite keeps setup at zero (note: Render's free disk is ephemeral); Starlette + vanilla JS keeps the stack small and fast to review. See the design doc for details.
