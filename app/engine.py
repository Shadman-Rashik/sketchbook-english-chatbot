"""Rule-based brain: safety, child-mode detection, progression, SEL tracking, offline replies.

Everything here is pure Python (microseconds), so it also acts as the < 2 s latency guarantee:
when the LLM is slow or unavailable, `fallback()` answers instantly.
"""
import random
import re

from . import content

NEG_MOODS = {"sad", "angry", "scared", "tired"}
LEVEL_AT = {2: 6, 3: 14}  # cumulative stars needed

SUPPORT_RE = re.compile(r"\b(sad|cry|crying|scared|afraid|angry|mad|upset|lonely|nobody|bad day|"
                        r"miss (my )?(mom|mommy|dad|daddy)|i can'?t do)\b")
PLAY_RE = re.compile(r"\b(play|game|games|story|joke|riddle|sing|song|fun|puzzle|quiz)\b")
LEARN_RE = re.compile(r"\b(teach|learn|lesson|new word|word|words|spell|abc|count|counting|"
                      r"colou?rs?|numbers?|what is|how do you say|what does)\b")
BORED_RE = re.compile(r"\b(bored|boring|enough|no more|stop|tired of)\b")
FEEL_RE = re.compile(r"\b(happy|sad|angry|mad|scared|excited|tired|proud|lonely|calm|love|"
                     r"sleepy|worried|brave)\b")
KIND_RE = re.compile(r"\b(please|thank|thanks|sorry|friend|good job|love you)\b")

HARM_RE = re.compile(r"(want to die|kill myself|hurt myself|hits me|hit me|beats me|touch(es|ed)? me|"
                     r"alone at home|abuse)")
PRIVACY_RE = re.compile(r"(\d{6,}|my (home )?address|i live (at|in)|my phone|my school is|my last name)")
RUDE_RE = re.compile(r"\b(stupid|idiot|shut up|dumb|ugly|hate you)\b")


# ---- safety ---------------------------------------------------------------
def safety_check(text):
    t = text.lower()
    if HARM_RE.search(t):
        return {"mode": "support", "reason": "I want you to be safe",
                "reply": "I'm so sorry you feel that way. 💛 Please tell a grown-up you trust, "
                         "like mom, dad or your teacher, right now. I'm here with you."}
    if PRIVACY_RE.search(t):
        return {"mode": "chat", "reason": "Keeping your secrets safe",
                "reply": "Let's keep that a secret! 🔒 We don't share our home or phone with anyone online. "
                         "Want to learn a new word instead?"}
    if RUDE_RE.search(t):
        return {"mode": "support", "reason": "Let's use kind words",
                "reply": "Oh! Let's use kind words. 🌸 Maybe you feel upset? It's okay. "
                         "Do you want to take a big breath with me?"}
    return None


# ---- mode detection ---------------------------------------------------------
def detect_mode(text, mood, recent_modes):
    """Returns (mode, reason). Modes: learn | chat | engage | support."""
    t = text.lower()
    last = recent_modes[-1] if recent_modes else None
    if SUPPORT_RE.search(t):
        return "support", "You sounded like you need a hug"
    if mood in NEG_MOODS and last != "support" and not (PLAY_RE.search(t) or LEARN_RE.search(t)):
        return "support", f"You told me you feel {mood}"
    if BORED_RE.search(t) or PLAY_RE.search(t):
        return "engage", "Let's have some fun"
    if len(recent_modes) >= 3 and all(m == "learn" for m in recent_modes[-3:]):
        return "engage", "Lots of learning! Time for fun"
    if LEARN_RE.search(t):
        return "learn", "You asked to learn"
    if last == "learn" and len(t.split()) <= 3:
        return "learn", "Practicing together"
    return "chat", "Just chatting"


# ---- progression ------------------------------------------------------------
def level_for(stars):
    return 3 if stars >= LEVEL_AT[3] else 2 if stars >= LEVEL_AT[2] else 1


def pick_word(level, widx):
    pool = content.POOLS[level]
    return pool[widx % len(pool)]


def word_by_key(key):
    for pool in content.POOLS.values():
        for w in pool:
            if w[0] == key:
                return w
    return None


def sel_delta(text):
    t = text.lower()
    d = {"aw": 0, "conf": 0, "cur": 0, "kind": 0}
    if FEEL_RE.search(t):
        d["aw"] = 1
    if "?" in t or re.match(r"\s*(why|how|what|who|where|when)\b", t):
        d["cur"] = 1
    if KIND_RE.search(t):
        d["kind"] = 1
    return d


TIPS = {"awareness": "tell Dilly how you feel today.",
        "confidence": "try one more quiz round. Mistakes help us grow!",
        "curiosity": "ask Dilly a “why” question.",
        "kindness": "say “please” and “thank you” to Dilly."}


def state_view(s):
    stars, lvl = s["stars"], level_for(s["stars"])
    acc = round(100 * s["correct"] / s["total"]) if s["total"] else 0
    meters = {k: min(100, s[col] * 12) for k, col in
              (("awareness", "aw"), ("confidence", "conf"), ("curiosity", "cur"), ("kindness", "kind"))}
    cog = min(100, round(stars * 5 + acc * 0.2))
    who = s["name"] or "Your little learner"
    if s["total"] == 0 and not any(meters.values()):
        note = f"{who} is just starting. Say hi, share a feeling, or play a quiz to grow the crane!"
    else:
        top = max(meters, key=meters.get)
        low = min(meters, key=meters.get)
        if meters[top] == meters[low]:
            note = f"{who} is growing evenly. Keep playing to unlock the next level!"
        else:
            note = f"{who} shines in {top.title()}. Next step for {low.title()}: {TIPS[low]}"
    return {"name": s["name"], "mood": s["mood"], "level": lvl, "level_name": content.LEVEL_NAMES[lvl],
            "stars": stars, "next_at": LEVEL_AT.get(lvl + 1),
            "crane": min(stars, 16) / 16, "accuracy": acc, "streak": s["streak"],
            "cognitive": cog, "sel": meters, "insight": note}


# ---- offline replies --------------------------------------------------------
def _n(s):
    return f", {s['name']}" if s.get("name") else ""


def mood_reply(mood, s):
    n = _n(s)
    if mood in NEG_MOODS:
        return ("support", f"I'm here{n}. 🤗 It's okay to feel {mood}. Let's breathe together: "
                           "in… and out… Do you want to talk, or play a gentle game?")
    if mood in ("happy", "excited"):
        return ("engage", f"Yay{n}! 😄 Happy days are the best! Want a quick game?")
    return ("chat", f"Nice and calm{n}. 😌 Shall we learn a new word together?")


def fallback(mode, s, word, prev_word, praised, mood):
    n = _n(s)
    if mode == "support":
        f = mood if mood in NEG_MOODS else "that way"
        return random.choice([
            f"I'm here{n}. 🤗 It's okay to feel {f}. Let's take a big breath: in… and out… Want to talk or play?",
            f"Thank you for telling me{n}. 💛 Feelings are okay. Hug a soft toy and breathe slowly with me.",
        ])
    if mode == "learn" and word:
        key, emo, phrase = word
        if praised and prev_word:
            return (f"Yay{n}! You said “{prev_word[0]}”! ⭐ Next word: {emo} “{key}”. "
                    f"{phrase} Can you say it?")
        return f"{emo} This is “{key}”! {phrase} Can you say “{key}”?"
    if mode == "engage":
        return random.choice([
            f"Let's play{n}! 🎈 I'm thinking of an animal that says meow. Who am I? Or tap Play for a quiz!",
            f"Time for fun{n}! 🎉 Tap the Play button and let's find the right pictures together!",
            "Riddle time! 🧩 I have four legs and I say woof. Who am I?",
        ])
    return random.choice([
        f"That sounds nice{n}! 😊 What is your favorite animal?",
        f"I like talking with you{n}! 🌸 What is your favorite color?",
        f"Tell me more{n}! 🦋 What did you eat today?",
    ])
