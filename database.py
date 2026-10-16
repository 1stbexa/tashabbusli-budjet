"""
database.py — botning "xotira" qismi (SQLite).
Ma'lumotlar votes.db faylida saqlanadi.
"""

import sqlite3
from datetime import datetime

DB_PATH = "votes.db"


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    """Jadval yo'q bo'lsa yaratadi, bor bo'lsa tegmaydi."""
    conn = _conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            full_name TEXT,
            phone TEXT,
            screenshot_file_id TEXT,
            status TEXT DEFAULT 'submitted',
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def add_vote(telegram_id, full_name, phone, screenshot_file_id, status="submitted") -> int:
    """Yangi yozuv qo'shadi va uning ID raqamini qaytaradi."""
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO votes (telegram_id, full_name, phone, screenshot_file_id, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (telegram_id, full_name, phone, screenshot_file_id, status, datetime.now().isoformat()),
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


def find_by_phone(fragment: str, limit: int = 10):
    """Raqamning bir qismi bo'yicha qidiradi (faqat raqamlar hisobga olinadi)."""
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


def exists_for_user(telegram_id: int) -> bool:
    conn = _conn()
    row = conn.execute("SELECT 1 FROM votes WHERE telegram_id = ? LIMIT 1", (telegram_id,)).fetchone()
    conn.close()
    return row is not None


def exists_for_phone(phone: str) -> bool:
    conn = _conn()
    row = conn.execute("SELECT 1 FROM votes WHERE phone = ? LIMIT 1", (phone,)).fetchone()
    conn.close()
    return row is not None


def count_total() -> int:
    conn = _conn()
    n = conn.execute("SELECT COUNT(*) FROM votes").fetchone()[0]
    conn.close()
    return n


def count_today() -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    conn = _conn()
    n = conn.execute("SELECT COUNT(*) FROM votes WHERE created_at LIKE ?", (today + "%",)).fetchone()[0]
    conn.close()
    return n


def clear_all() -> int:
    """Barcha yozuvlarni o'chiradi (test ma'lumotlarini tozalash uchun)."""
    conn = _conn()
    n = conn.execute("SELECT COUNT(*) FROM votes").fetchone()[0]
    conn.execute("DELETE FROM votes")
    conn.commit()
    conn.close()
    return n
