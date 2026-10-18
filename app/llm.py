"""Groq (OpenAI-compatible) client with a hard timeout and a tiny circuit breaker.

Why this shape: the product promise is < 2 s end-to-end. We give the LLM at most ~1.4 s; on timeout or
error we return None and the caller answers instantly from the rule-based brain. After 3 consecutive
failures the breaker skips the LLM for 30 s so a bad network never slows the child down.
"""
import asyncio
import os
import re
import threading
import time

import requests

URL = "https://api.groq.com/openai/v1/chat/completions"
_session = requests.Session()  # keep-alive: reuses the TLS connection between turns
_fails = 0
_skip_until = 0.0

LEVEL_DESC = {1: "first words (objects, colors)", 2: "numbers, opposites, greetings",
              3: "tiny sentences"}


def enabled():
    return bool(os.getenv("GROQ_API_KEY"))


def _timeout():
    return float(os.getenv("LLM_TIMEOUT", "1.4"))


def _post(messages):
    r = _session.post(
        URL, headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"]},
        json={"model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"), "messages": messages,
              "max_tokens": 80, "temperature": 0.7},
        timeout=(0.8, _timeout()))
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def warm():
    """Open the TLS connection in the background at startup (saves ~150 ms on the first turn)."""
    def run():
        try:
            _session.get("https://api.groq.com/openai/v1/models", timeout=3,
                         headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"]})
        except Exception:
            pass
    if enabled():
        threading.Thread(target=run, daemon=True).start()


def clean(text):
    if not text:
        return None
    text = re.sub(r"[*#_`>]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    words = text.split(" ")
    if len(words) > 45:
        text = " ".join(words[:45])
        cut = max(text.rfind("."), text.rfind("!"), text.rfind("?"))
        if cut > 20:
            text = text[:cut + 1]
    return text or None


async def complete(messages):
    """Returns a cleaned reply string, or None (disabled / slow / failed)."""
    global _fails, _skip_until
    if not enabled() or time.time() < _skip_until:
        return None
    try:
        raw = await asyncio.wait_for(asyncio.to_thread(_post, messages), _timeout() + 0.1)
        _fails = 0
        return clean(raw)
    except Exception:
        _fails += 1
        if _fails >= 3:
            _skip_until = time.time() + 30
            _fails = 0
        return None


def build_messages(s, mode, mood, word, prev_word, praised, history, text, misses):
    name = s["name"] or "friend"
    lvl = s["level"]
    if mode == "learn" and word:
        key, emo, phrase = word
        lead = f"The child just said “{prev_word[0]}” correctly. Celebrate in a few words first. " if praised and prev_word else ""
        task = (f"{lead}Teach the word “{key}” {emo} with this tiny example: {phrase} "
                "End by asking the child to say the word.")
    elif mode == "engage":
        task = "Make it fun: offer one tiny riddle, joke or guessing game in very easy English."
    elif mode == "support":
        task = (f"The child may feel {mood or 'upset'}. Name the feeling gently, say it is okay, offer one calming "
                "idea (deep breath, hug a toy) and ask if they want to talk or play. Do not teach.")
    else:
        task = "Chat naturally about what the child said. Do not teach unless asked. Ask one friendly question."
    trouble = f" Words the child found hard recently: {', '.join(misses)}." if misses else ""
    system = (
        "You are Dora, a warm, playful doll friend who helps a child under 7 learn English. "
        "Reply in at most 2 short sentences (under 30 words) using very simple words and exactly one emoji. "
        "No lists, no markdown. Never say the child is wrong: say 'Nice try!' and show the right way. "
        "Never ask for personal information such as address, phone or school. "
        f"Child: {name}. Level L{lvl} ({LEVEL_DESC[lvl]}), {s['stars']} stars. Mood: {mood or 'unknown'}."
        f"{trouble} Current mode: {mode}. {task}")
    return [{"role": "system", "content": system}, *history[-6:], {"role": "user", "content": text}]
