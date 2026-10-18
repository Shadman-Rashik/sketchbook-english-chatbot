# Sketchbook · Little Words Matter

An AI English tutor for children under 7. Dora, a knitted doll, teaches step by step, notices how the child feels, and adapts.

**Live demo:** https://sketchbook-english-chatbot.onrender.com

## Requirements covered
| Requirement | How it is done |

| Progressive learning (L1, L2, L3) | Single words, then short phrases, then short questions. Five correct answers in a row unlock the next level, with a level-up celebration. |
| Child mode detection | Switches between learning, conversation, engagement and support using mood, keywords and recent answers. It does not teach in every turn. |
| Social and emotional learning | Mood check-in, effort-based praise, calming support when the child feels sad. The CSE Insight view shows the cognitive and social-emotional signals behind each reply. |
| Context-aware responses | Remembers each child's level, learned words and recent messages. |
| Latency under 2 seconds | Rules handle grading and mode detection instantly. The LLM only phrases short replies, with a short timeout and a rule-based fallback. |
| Deliverables | Live URL, source code, architecture diagram and system design in `docs/`, this README. |

## Highlights
- Name screen, then a home screen with Learn, Play, Chat and My Crane (progress)
- Live clock and date, and a Word of the Day
- Instant, high-energy praise when the child says the target word
- Voice: tap to hear Dora, use the microphone to answer
- Child-safe replies: very short, simple sentences and gentle redirection

## Stack
Python, FastAPI, Groq LLM, SQLite, plain HTML/CSS/JavaScript, hosted on Render.

## Run locally

python -m venv venv
venv\Scripts\activate          
pip install -r requirements.txt
Create a `.env` file:
GROQ_API_KEY=INPUT
Start the app and open http://127.0.0.1:8000:
uvicorn app.main:app --reload
Without a key, the app still works in rule-based mode.

## Deploy on Render
1. Push the repo to GitHub.
2. Render: New, Web Service, select the repo, Python 3, Free plan.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables `GROQ_API_KEY` and `GROQ_MODEL`.
6. Open the Render URL. `/health` should return ok.


- [System design](docs/SYSTEM_DESIGN.md)
