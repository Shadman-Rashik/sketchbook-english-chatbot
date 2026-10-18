"""Tiny SQLite persistence (stdlib only). One row per child-session, plus chat log and misses."""
import os
import sqlite3
import threading
import time

DB_PATH = os.getenv("DB_PATH", "sketchbook.db")
_lock = threading.Lock()
_conn = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions(
  id TEXT PRIMARY KEY, name TEXT DEFAULT '', mood TEXT DEFAULT '',
  level INTEGER DEFAULT 1, stars INTEGER DEFAULT 0, correct INTEGER DEFAULT 0,
  total INTEGER DEFAULT 0, streak INTEGER DEFAULT 0, widx INTEGER DEFAULT 0,
  target TEXT DEFAULT '', aw INTEGER DEFAULT 0, conf INTEGER DEFAULT 0,
  cur INTEGER DEFAULT 0, kind INTEGER DEFAULT 0, created REAL, updated REAL);
CREATE TABLE IF NOT EXISTS messages(
  id INTEGER PRIMARY KEY AUTOINCREMENT, sid TEXT, role TEXT, content TEXT, mode TEXT, ts REAL);
CREATE INDEX IF NOT EXISTS ix_msg ON messages(sid, id);
CREATE TABLE IF NOT EXISTS misses(
  id INTEGER PRIMARY KEY AUTOINCREMENT, sid TEXT, word TEXT, ts REAL);
"""
COLS = {"name", "mood", "level", "stars", "correct", "total", "streak", "widx",
        "target", "aw", "conf", "cur", "kind"}


def _c():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(SCHEMA)
    return _conn


def get_session(sid):
    with _lock:
        c = _c()
        r = c.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
        if r is None:
            now = time.time()
            c.execute("INSERT INTO sessions(id,created,updated) VALUES(?,?,?)", (sid, now, now))
            c.commit()
            r = c.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
        return dict(r)


def update(sid, **fields):
    fields = {k: v for k, v in fields.items() if k in COLS}
    if not fields:
        return
    sets = ",".join(f"{k}=?" for k in fields)
    with _lock:
        c = _c()
        c.execute(f"UPDATE sessions SET {sets}, updated=? WHERE id=?",
                  (*fields.values(), time.time(), sid))
        c.commit()


def add_message(sid, role, content, mode=None):
    with _lock:
        c = _c()
        c.execute("INSERT INTO messages(sid,role,content,mode,ts) VALUES(?,?,?,?,?)",
                  (sid, role, content, mode, time.time()))
        c.commit()


def recent_messages(sid, n=6):
    with _lock:
        rows = _c().execute("SELECT role,content FROM messages WHERE sid=? ORDER BY id DESC LIMIT ?",
                            (sid, n)).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def recent_modes(sid, n=3):
    with _lock:
        rows = _c().execute("SELECT mode FROM messages WHERE sid=? AND role='assistant' "
                            "AND mode IS NOT NULL ORDER BY id DESC LIMIT ?", (sid, n)).fetchall()
    return [r["mode"] for r in reversed(rows)]


def add_miss(sid, word):
    with _lock:
        c = _c()
        c.execute("INSERT INTO misses(sid,word,ts) VALUES(?,?,?)", (sid, word, time.time()))
        c.commit()


def recent_misses(sid, n=3):
    with _lock:
        rows = _c().execute("SELECT DISTINCT word FROM misses WHERE sid=? ORDER BY id DESC LIMIT ?",
                            (sid, n)).fetchall()
    return [r["word"] for r in rows]
