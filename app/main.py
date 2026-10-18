"""Sketchbook API (Starlette ASGI). Run: uvicorn app.main:app"""
import random
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from starlette.applications import Starlette  # noqa: E402
from starlette.middleware import Middleware  # noqa: E402
from starlette.middleware.gzip import GZipMiddleware  # noqa: E402
from starlette.responses import FileResponse, JSONResponse  # noqa: E402
from starlette.routing import Mount, Route  # noqa: E402
from starlette.staticfiles import StaticFiles  # noqa: E402

from . import content, db, engine, llm  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
MOODS = {"happy", "excited", "calm", "tired", "sad", "angry", "scared"}
SID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
PRAISE = ["Great job! ⭐", "You did it! 🎉", "Wow, super! 🌟", "Yay, that's right! 🌈", "Brilliant! ✨"]
TRY_AGAIN = ["Nice try! Let's look again. 🌈", "Almost! Try another one. 💛", "Good thinking! Try once more. 🌸"]


def err(msg, code=400):
    return JSONResponse({"error": msg}, status_code=code)


async def read_json(request):
    try:
        d = await request.json()
    except Exception:
        return {}
    return d if isinstance(d, dict) else {}


def valid_sid(x):
    x = str(x or "")
    return x if SID_RE.match(x) else None


def clean_name(n):
    return re.sub(r"[^\w '\-]", "", str(n or "")).strip()[:20]


def session_with_name(sid, name):
    s = db.get_session(sid)
    nm = clean_name(name)
    if nm and nm != s["name"]:
        db.update(sid, name=nm)
        s = db.get_session(sid)
    return s


# ---- routes -----------------------------------------------------------------
async def index(request):
    return FileResponse(BASE / "static" / "index.html")


async def health(request):
    return JSONResponse({"ok": True, "llm": llm.enabled()})


async def state(request):
    sid = valid_sid(request.query_params.get("session_id"))
    if not sid:
        return err("bad session")
    s = session_with_name(sid, request.query_params.get("name"))
    return JSONResponse({"state": engine.state_view(s)})


async def mood(request):
    d = await read_json(request)
    sid, m = valid_sid(d.get("session_id")), str(d.get("mood", ""))
    if not sid or m not in MOODS:
        return err("bad request")
    s = session_with_name(sid, d.get("name"))
    mode, reply = engine.mood_reply(m, s)
    db.update(sid, mood=m, aw=s["aw"] + 1)
    db.add_message(sid, "user", f"I feel {m}")
    db.add_message(sid, "assistant", reply, mode)
    return JSONResponse({"reply": reply, "mode": mode, "reason": f"You told me you feel {m}",
                         "state": engine.state_view(db.get_session(sid))})


async def chat(request):
    t0 = time.perf_counter()
    d = await read_json(request)
    sid = valid_sid(d.get("session_id"))
    text = str(d.get("message", "")).strip()[:300]
    if not sid or not text:
        return err("bad request")
    s = session_with_name(sid, d.get("name"))
    history, modes = db.recent_messages(sid, 6), db.recent_modes(sid, 3)

    sel = engine.sel_delta(text)
    stars, widx, target = s["stars"], s["widx"], s["target"]
    praised, prev_word, word, source = False, None, None, "fallback"

    flag = engine.safety_check(text)
    if flag:
        mode, reason, reply, source = flag["mode"], flag["reason"], flag["reply"], "safety"
    else:
        if engine.matches_target(text, target):
            praised, prev_word = True, engine.word_by_key(target)
            stars += 1
            sel["conf"] += 1
        level = engine.level_for(stars)
        if praised:
            mode, reason = "learn", "You said the word!"
            widx += 1
            word = engine.pick_word(level, widx)
            target = word[0]
            said = prev_word[0] if prev_word else s["target"]
            reply = engine.instant_praise(said, stars - 1)
            source = "praise"
        else:
            mode, reason = engine.detect_mode(text, s["mood"], modes)
            if mode == "learn":
                word = engine.pick_word(level, widx)
                target = word[0]
            msgs = llm.build_messages(s, mode, s["mood"], word, prev_word, praised, history, text,
                                      db.recent_misses(sid))
            reply = await llm.complete(msgs)
            if reply:
                source = "llm"
            else:
                reply = engine.fallback(mode, s, word, prev_word, praised, s["mood"])

    new_level = engine.level_for(stars)
    db.update(sid, stars=stars, level=new_level, widx=widx, target=target,
              aw=s["aw"] + sel["aw"], conf=s["conf"] + sel["conf"],
              cur=s["cur"] + sel["cur"], kind=s["kind"] + sel["kind"])
    db.add_message(sid, "user", text)
    db.add_message(sid, "assistant", reply, mode)
    ms = int((time.perf_counter() - t0) * 1000)
    return JSONResponse({"reply": reply, "mode": mode, "reason": reason, "source": source,
                         "latency_ms": ms, "praised": praised,
                         "leveled_up": new_level > s["level"],
                         "suggest": "play" if mode == "engage" else None,
                         "state": engine.state_view(db.get_session(sid))},
                        headers={"Server-Timing": f"app;dur={ms}"})


async def practice(request):
    d = await read_json(request)
    sid = valid_sid(d.get("session_id"))
    word = engine.word_by_key(str(d.get("word", "")).strip().lower())
    if not sid or not word:
        return err("bad request")
    session_with_name(sid, d.get("name"))
    key, emo, phrase = word
    db.update(sid, target=key)
    reply = f"{emo} Let’s practice “{key}”! {phrase} Can you say “{key}”?"
    db.add_message(sid, "assistant", reply, "learn")
    return JSONResponse({"reply": reply, "mode": "learn", "reason": "Word of the day practice",
                         "state": engine.state_view(db.get_session(sid))})


async def quiz(request):
    sid = valid_sid(request.query_params.get("session_id"))
    if not sid:
        return err("bad session")
    s = db.get_session(sid)
    return JSONResponse(content.make_quiz(engine.level_for(s["stars"]),
                                          request.query_params.get("prev", "")))


async def answer(request):
    d = await read_json(request)
    sid = valid_sid(d.get("session_id"))
    item = content.REG.get(str(d.get("item_id", "")))
    if not sid or not item:
        return err("bad request")
    attempt = int(d.get("attempt", 1)) if str(d.get("attempt", 1)).isdigit() else 1
    s = db.get_session(sid)
    ok = str(d.get("choice", "")).strip().lower() == item["answer"].lower()
    upd = {"total": s["total"] + 1}
    gained, msg, reveal = 0, "", False
    if ok:
        streak = s["streak"] + 1
        gained = 2 if streak % 3 == 0 else 1  # bonus star every 3 in a row
        upd.update(correct=s["correct"] + 1, streak=streak, stars=s["stars"] + gained,
                   conf=s["conf"] + (2 if attempt > 1 else 1))
        msg = random.choice(PRAISE) + (" Bonus star for 3 in a row! 🔥" if gained == 2 else "")
    else:
        upd["streak"] = 0
        db.add_miss(sid, item["answer"])
        reveal = attempt >= 2
        msg = (f"Nice try! The answer is “{item['answer']}”. 💛" if reveal else random.choice(TRY_AGAIN))
    new_level = engine.level_for(upd.get("stars", s["stars"]))
    upd["level"] = new_level
    db.update(sid, **upd)
    return JSONResponse({"correct": ok, "answer": item["answer"] if (ok or reveal) else None,
                         "reveal": reveal, "message": msg, "stars_gained": gained,
                         "leveled_up": new_level > s["level"],
                         "state": engine.state_view(db.get_session(sid))})


@asynccontextmanager
async def lifespan(app):
    llm.warm()
    yield


app = Starlette(
    routes=[
        Route("/", index),
        Route("/api/health", health),
        Route("/api/state", state),
        Route("/api/mood", mood, methods=["POST"]),
        Route("/api/chat", chat, methods=["POST"]),
        Route("/api/practice", practice, methods=["POST"]),
        Route("/api/quiz", quiz),
        Route("/api/answer", answer, methods=["POST"]),
        Mount("/static", StaticFiles(directory=BASE / "static"), name="static"),
    ],
    middleware=[Middleware(GZipMiddleware, minimum_size=800)],
    lifespan=lifespan,
)
