# Sketchbook: System Design

**Product:** an AI-powered English-learning friend for children under 7.  
**Tagline:** *Little Words Matter*. **Mascot:** Dora, a doll friend.

See also [ARCHITECTURE.md](ARCHITECTURE.md).

## 1. Goals

| Requirement | What the code does |
|---|---|
| Progressive learning L1 / L2 / L3 | Stars are the only progress currency. `engine.LEVEL_AT` unlocks L2 at 6 stars and L3 at 14. `content.POOLS` and the quiz registry `content.REG` are per level. Stars come from saying the current chat target (`+1`, plus `conf`) or from Play (`+1`, or `+2` every 3rd correct in a streak). |
| Child mode detection | `engine.detect_mode()` returns `learn`, `chat`, `engage`, or `support`. The chat header shows UI labels Learning / Chatting / Fun time / Here for you plus a reason string. |
| Social-emotional learning | Home mood check-in (`POST /api/mood`), support-mode breathing bubble, praise-first quiz and chat copy, four SEL counters, CSE Insight on My Crane. |
| Context-aware replies | Groq system prompt includes name, level, stars, mood, mode, recent misses, last 6 messages, and the word being taught. |
| Under 2 seconds | Groq hard cap (`LLM_TIMEOUT`, default 1.4 s), keep-alive + startup warm, circuit breaker, rule fallback, and instant praise with no LLM when the child says the target. |
| Live URL | `render.yaml` defines a Python web service (`uvicorn app.main:app`). |

## 2. Components

- **Front-end** (`static/`): one HTML page, five screens (splash, home, chat, play, progress). No build step. Web Speech API for Dora’s voice and the microphone. Session id and optional first name in `localStorage`. Home has a live clock/date and a Word of the Day card (curriculum word from the local calendar date, TTS button, Practice → `POST /api/practice`).
- **API** (`app/main.py`): Starlette ASGI + Uvicorn. GZip middleware. Routes: `GET /`, `/api/health`, `/api/state`, `POST /api/mood`, `/api/chat`, `/api/practice`, `GET /api/quiz`, `POST /api/answer`, `/static`.
- **Rule-based brain** (`app/engine.py`): `safety_check`, `detect_mode`, `level_for` / `pick_word`, `matches_target`, `instant_praise`, `sel_delta`, `state_view`, `mood_reply`, `fallback`.
- **LLM client** (`app/llm.py`): Groq OpenAI-compatible `llama-3.1-8b-instant` (override with `GROQ_MODEL`), `max_tokens` 80, timeout, 3-failure / 30 s breaker, `clean()` (strip markdown, cap ~45 words). Disabled when `GROQ_API_KEY` is unset.
- **Curriculum** (`app/content.py`): chat word pools L1–L3; quiz items (objects, colors, counts, opposites, greetings, sentences). `make_quiz` picks a level item (20% chance of the level below when `level > 1`) and three shuffled options.
- **Persistence** (`app/db.py`): SQLite (`DB_PATH`, default `sketchbook.db`). Thread lock. Tables `sessions`, `messages`, `misses`.

## 3. Data model

`sessions(id, name, mood, level, stars, correct, total, streak, widx, target, aw, conf, cur, kind, created, updated)`

`messages(sid, role, content, mode, ts)` · `misses(sid, word, ts)`

- `target` is the word/phrase the child should say next (last taught word, or Word of the Day after Practice).
- `widx` indexes `content.POOLS[level]`.
- `aw` / `conf` / `cur` / `kind` are integer SEL counters. `state_view` maps each to `min(100, count * 12)`.
- Cognitive meter: `min(100, round(stars * 5 + accuracy * 0.2))`.
- Crane fill: `min(stars, 16) / 16` (eight SVG pieces).

No accounts. Identity is a random 8–64 character `session_id` plus an optional first name (max 20, stripped of most punctuation).

## 4. Level progression L1–L3

| Level | Name (`LEVEL_NAMES`) | Unlock | Chat pool (`POOLS`) | Play (`REG`) |
|---|---|---|---|---|
| 1 | Little Sprout | 0 stars | First words (apple, cat, …) | Emoji objects + colors |
| 2 | Word Explorer | 6 stars | Numbers, hello, big/small, hot/cold | Counts, opposites, greetings |
| 3 | Sentence Star | 14 stars | Tiny sentence words (happy, friend, …) | Fill-in-the-blank sentences |

`level` stored on the session is `engine.level_for(stars)` after each chat or quiz update. Crossing a threshold sets `leveled_up` in the JSON; the UI shows an origami overlay.

Chat target match: `matches_target` folds case and punctuation, then `\b` word-boundary search. On match, `source=praise`, `stars += 1`, `widx += 1`, next `pick_word`, **no Groq call**. Five praise templates rotate on `stars - 1`.

Play: answers compared case-insensitively on the server. Wrong twice reveals the answer and records a miss.

## 5. Child mode detection

`detect_mode(text, mood, recent_modes)` — modes in code vs UI:

| Code | UI | Trigger (from `engine.py`) |
|---|---|---|
| `support` | Here for you | Support regex (sad, cry, scared, …); or check-in mood in `{sad, angry, scared, tired}` unless the child asked to play/learn and last mode was not already support |
| `engage` | Fun time | Bored/stop regex or play/game/story/joke/… regex; **or** last three assistant modes were all `learn` |
| `learn` | Learning | Teach/learn/word/… regex; or last mode was `learn` and the message is ≤ 3 words (practice) |
| `chat` | Chatting | Default (“Just chatting”) |

Safety runs first and never calls the LLM: harm → tell a trusted adult; privacy (phone/address/school/last name) → refuse; rude words → kindness + breath.

Mood check-in is a separate `POST /api/mood` path (`engine.mood_reply`), not `detect_mode`.

## 6. Social-emotional learning and CSE Insight

- **Mood check-in:** six buttons (happy, excited, calm, tired, sad, angry). Increments `aw`. Negative moods get a support reply; happy/excited get engage; calm gets chat.
- **Support UI:** 14 s breathing orb in chat.
- **SEL increments (`sel_delta`):** feeling words → awareness; `?` or why/how/what/who/where/when → curiosity; please/thank/sorry/friend/… → kindness. Target match and quiz correctness increment confidence.
- **CSE Insight** (My Crane): bars for Thinking (cognitive), Feelings (awareness), Confidence, Curiosity, Kindness, plus `insight` copy that names the strongest/weakest meter and a tip (`TIPS`).

## 7. Context handling

For LLM turns, `llm.build_messages` builds: system (Dora persona, ≤ 2 short sentences, one emoji, no lists/markdown, never “you’re wrong”, never ask for address/phone/school, child name/level/stars/mood/misses/mode/task) + last 6 stored messages + current user text.

Learn task: teach `POOLS` phrase and ask the child to say the word. Engage: one easy riddle/joke. Support: name the feeling, do not teach. Chat: talk, one question, do not teach unless asked.

Word of the Day does not call the backend to pick the word: `app.js` uses the same `(key, emoji)` pairs as `POOLS` and `year * 372 + (month+1) * 31 + day` modulo the list. Practice only posts the chosen key so `target` is set.

## 8. Latency strategy (< 2 s)

| Step | Budget / behavior |
|---|---|
| Browser ↔ server | Typical LAN/WAN; splash also `GET /api/health` to wake a sleeping free-tier process |
| Safety, `matches_target`, `detect_mode`, DB | In-process Python |
| **Instant praise** (target match) | Template in `engine.instant_praise`; **no LLM**; `source=praise` |
| Groq | Connect timeout 0.8 s, read `LLM_TIMEOUT` (default 1.4 s); `max_tokens` 80; TLS warmed at startup |
| Circuit breaker | After 3 consecutive failures, skip Groq for 30 s |
| Fallback | `engine.fallback` if the key is missing, breaker is open, or Groq fails/times out |
| Measured end-to-end (typical chat) | fill in |

Each chat response includes `latency_ms` and `Server-Timing`. The chat header shows it. `tests/smoke.py` asserts max of seven turns `< 2000` ms.

Honest limit: Render’s free plan can sleep; first request after idle can be tens of seconds. The splash health ping and an optional `/api/health` uptime monitor are how the project deals with that—not a fix for the sleep itself.

## 9. Trade-offs

| Decision | Alternative | Why this way (from the code/deploy files) |
|---|---|---|
| Groq cloud LLM | Local Ollama | Hosted URL cannot use a laptop GPU; Groq is the configured provider |
| Rules + LLM | LLM only | Safety, modes, target praise, and the 2 s cap must not wait on the network |
| SQLite file | Postgres | Stdlib, zero extra service; Render free disk is ephemeral |
| Regex modes | A classifier model | Instant and the reason is shown in the UI |
| Starlette + vanilla JS | FastAPI + React | Six endpoints, no build, smaller cold start |
| Instant praise templates | LLM celebration | Match path must add no model latency |

## 10. Limitations

- Session progress is lost if the SQLite file is wiped (typical on Render free redeploy/restart).
- Mode detection is keyword/regex, not a full NLU model.
- Dora does not score pronunciation; TTS/mic are browser APIs.
- Chat messages are capped at 300 characters; LLM output is truncated after cleaning.
- Quiz options are generated server-side but the visual content is emoji/CSS, not illustrated assets.
- Word of the Day list is duplicated in `app.js` to avoid a fetch; it must stay aligned with `content.POOLS`.
- No authentication, parent accounts, or multi-device sync.

## 11. Future work

Durable database if progress must survive deploys; token streaming of Groq replies; pronunciation scoring; illustrated quiz art; optional parent view over the same `state_view` meters. None of these are implemented.
