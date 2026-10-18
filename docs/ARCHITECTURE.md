# Sketchbook architecture

Single-page browser app talking to a Starlette API. The mascot is **Dora**. State lives in SQLite. Optional replies come from Groq; safety, modes, target matching and fallbacks stay in `engine.py`.

## Component diagram

```mermaid
flowchart LR
  subgraph Browser["Child browser · static SPA"]
    UI["index.html · style.css · app.js"]
    TTS["Web Speech API<br/>TTS + microphone"]
    LS["localStorage<br/>session id · name"]
  end

  subgraph API["Starlette + Uvicorn"]
    R["Routes<br/>/ /api/health /api/state<br/>/api/mood /api/chat /api/practice<br/>/api/quiz /api/answer · /static"]
    E["engine.py<br/>safety · modes · stars/levels<br/>SEL · match + instant praise · fallback"]
    L["llm.py<br/>Groq Llama 3.1 8B Instant<br/>1.4s timeout · circuit breaker"]
    C["content.py<br/>word pools L1–L3 · quiz registry"]
  end

  DB[("SQLite<br/>sessions · messages · misses")]
  Groq["Groq HTTPS API"]

  UI --> TTS
  UI --> LS
  UI -->|JSON HTTPS| R
  R --> E
  R --> L
  R --> C
  R --> DB
  L --> Groq
```

## Sequence: one `POST /api/chat` request

```mermaid
sequenceDiagram
  participant B as Browser
  participant A as Starlette /api/chat
  participant D as SQLite
  participant E as engine.py
  participant L as llm.py / Groq

  B->>A: POST {session_id, message, name}
  A->>D: get session, last 6 messages, last 3 modes
  A->>E: safety_check(text)
  alt harm, privacy, or rude words
    E-->>A: canned reply, source=safety
  else message matches session target
    Note over A,E: matches_target (case + punctuation)<br/>no LLM call
    A->>E: instant_praise(word) rotating 5 templates
    E-->>A: reply, source=praise, +1 star, next target
  else other messages
    A->>E: detect_mode → learn | chat | engage | support
    alt mode is learn
      A->>E: pick_word(level, widx), store as target
    end
    A->>L: complete(build_messages(...))
    alt Groq returns within timeout
      L-->>A: cleaned reply, source=llm
    else missing key, timeout, error, or breaker open
      A->>E: fallback(mode, ...)
      E-->>A: rule reply, source=fallback
    end
  end
  A->>D: update session (stars, level, SEL, target, widx)
  A->>D: insert user + assistant messages
  A-->>B: JSON reply, mode, reason, source, latency_ms, praised, leveled_up, state
```
