"""
database.py — botning "xotira" qismi (SQLite). Ma'lumotlar votes.db faylida.

Ustunlar: id, telegram_id, full_name, phone, screenshot_file_id, status, created_at,
          screenshot_unique_id, flags
Holatlar: submitted (oddiy), review (tekshirish kerak), verified (admin tasdiqlagan),
          rejected (rad etilgan)
"""

import sqlite3
from datetime import datetime

DB_PATH = "votes.db"


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = _conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            full_name TEXT,
            phone TEXT,
            screenshot_file_id TEXT,
            status TEXT DEFAULT 'submitted',
            created_at TEXT,
            screenshot_unique_id TEXT,
            flags TEXT
        )
    """)
    # Eski bazada yangi ustunlar bo'lmasa, qo'shib qo'yamiz
    cols = {r[1] for r in conn.execute("PRAGMA table_info(votes)").fetchall()}
    if "screenshot_unique_id" not in cols:
        conn.execute("ALTER TABLE votes ADD COLUMN screenshot_unique_id TEXT")
    if "flags" not in cols:
        conn.execute("ALTER TABLE votes ADD COLUMN flags TEXT")
    conn.commit()
    conn.close()


def add_vote(telegram_id, full_name, phone, screenshot_file_id,
             status="submitted", screenshot_unique_id=None, flags=None) -> int:
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO votes (telegram_id, full_name, phone, screenshot_file_id, status, "
        "created_at, screenshot_unique_id, flags) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (telegram_id, full_name, phone, screenshot_file_id, status,
         datetime.now().isoformat(), screenshot_unique_id, flags),
    )
    conn.commit()
    vote_id = cur.lastrowid
    conn.close()
    return vote_id


def get_vote(vote_id: int):
    conn = _conn()
    row = conn.execute("SELECT * FROM votes WHERE id = ?", (vote_id,)).fetchone()
    conn.close()
    return row


def set_status(vote_id: int, status: str):
    conn = _conn()
    conn.execute("UPDATE votes SET status = ? WHERE id = ?", (status, vote_id))
    conn.commit()
    conn.close()


def get_all():
    conn = _conn()
    rows = conn.execute("SELECT * FROM votes ORDER BY created_at DESC").fetchall()
    conn.close()
    return rows


def get_recent(limit: int = 10):
    conn = _conn()
    rows = conn.execute("SELECT * FROM votes ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows


def get_by_status(status: str, limit: int = 10):
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM votes WHERE status = ? ORDER BY id DESC LIMIT ?", (status, limit)
    ).fetchall()
    conn.close()
    return rows


def find_by_phone(fragment: str, limit: int = 10):
    digits = "".join(ch for ch in fragment if ch.isdigit())
    if not digits:
        return []
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM votes WHERE REPLACE(phone, '+', '') LIKE ? ORDER BY id DESC LIMIT ?",
        (f"%{digits}%", limit),
    ).fetchall()
    conn.close()
    return rows


def exists_for_phone(phone: str) -> bool:
    conn = _conn()
    row = conn.execute("SELECT 1 FROM votes WHERE phone = ? LIMIT 1", (phone,)).fetchone()
    conn.close()
    return row is not None


def exists_screenshot(unique_id: str) -> bool:
    if not unique_id:
        return False
    conn = _conn()
    row = conn.execute(
        "SELECT 1 FROM votes WHERE screenshot_unique_id = ? LIMIT 1", (unique_id,)
    ).fetchone()
    conn.close()
    return row is not None


def count_for_user(telegram_id: int) -> int:
    conn = _conn()
    n = conn.execute("SELECT COUNT(*) FROM votes WHERE telegram_id = ?", (telegram_id,)).fetchone()[0]
    conn.close()
    return n


def count_by_status(status: str) -> int:
    conn = _conn()
    n = conn.execute("SELECT COUNT(*) FROM votes WHERE status = ?", (status,)).fetchone()[0]
    conn.close()
    return n


def count_total() -> int:
    """Rad etilganlardan tashqari barcha yozuvlar."""
    conn = _conn()
    n = conn.execute("SELECT COUNT(*) FROM votes WHERE status != 'rejected'").fetchone()[0]
    conn.close()
    return n


def count_today() -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    conn = _conn()
    n = conn.execute(
        "SELECT COUNT(*) FROM votes WHERE created_at LIKE ? AND status != 'rejected'",
        (today + "%",),
    ).fetchone()[0]
    conn.close()
    return n


def clear_all() -> int:
    conn = _conn()
    n = conn.execute("SELECT COUNT(*) FROM votes").fetchone()[0]
    conn.execute("DELETE FROM votes")
    conn.commit()
    conn.close()
    return n
