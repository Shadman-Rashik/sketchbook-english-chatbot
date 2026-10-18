"""End-to-end smoke test + latency check. Works on localhost or on the live URL.

    python tests/smoke.py                      # http://127.0.0.1:8000
    python tests/smoke.py https://your-app.onrender.com
"""
import statistics
import sys
import time
import uuid

import requests

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
SID = uuid.uuid4().hex
fails = []


def check(name, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"  {extra}" if extra else ""))
    if not cond:
        fails.append(name)


def chat(msg):
    t = time.perf_counter()
    r = requests.post(f"{BASE}/api/chat", json={"session_id": SID, "message": msg, "name": "Mimi"}, timeout=10)
    return r.json(), (time.perf_counter() - t) * 1000


h = requests.get(f"{BASE}/api/health", timeout=60).json()
check("health", h.get("ok") is True, f"(llm enabled: {h.get('llm')})")

j, _ = chat("hello dora")
check("chat mode", j["mode"] == "chat", j["mode"])
j, _ = chat("I feel sad today")
check("support mode on sad", j["mode"] == "support", j["reply"][:50])
j, _ = chat("teach me a word")
check("learn mode on request", j["mode"] == "learn", j["reply"][:60])
j, _ = chat("let's play a game")
check("engage mode on play", j["mode"] == "engage")
j, _ = chat("my phone is 01712345678")
check("privacy guard", j["source"] == "safety")
p = requests.post(f"{BASE}/api/practice", json={"session_id": SID, "word": "apple", "name": "Mimi"}, timeout=10)
check("practice sets word", p.ok)
j, _ = chat("Apple!")
check("instant praise skips LLM", j.get("source") == "praise" and j.get("praised") is True, str(j.get("source")))
check("instant praise includes the word", "apple" in j.get("reply", "").lower())

# level up through the quiz
st = requests.get(f"{BASE}/api/state", params={"session_id": SID}, timeout=10).json()["state"]
leveled = False
for _ in range(30):
    q = requests.get(f"{BASE}/api/quiz", params={"session_id": SID}, timeout=10).json()
    from_item = q["id"]
    # ask the server using every option until correct (attempt counter) to avoid importing app code
    for i, opt in enumerate(q["options"], 1):
        r = requests.post(f"{BASE}/api/answer", json={"session_id": SID, "item_id": from_item,
                                                     "choice": opt, "attempt": i}, timeout=10).json()
        if r["correct"] or r["reveal"]:
            break
    leveled = leveled or r["leveled_up"]
    st = r["state"]
    if st["level"] >= 2:
        break
check("quiz progression reaches level 2", st["level"] >= 2, f"stars={st['stars']} level={st['level']}")

times = []
for m in ["hi", "what is a cat?", "I love my friend", "tell me a joke", "teach me", "apple", "ok"]:
    j, ms = chat(m)
    times.append(ms)
check("end-to-end latency < 2000 ms (max of 7 turns)", max(times) < 2000,
      f"median={statistics.median(times):.0f}ms max={max(times):.0f}ms")
print("\nALL GOOD" if not fails else f"\n{len(fails)} FAILED: {fails}")
sys.exit(1 if fails else 0)
