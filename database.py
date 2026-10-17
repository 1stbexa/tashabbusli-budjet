"""
database.py — botning "xotira" qismi (SQLite). Ma'lumotlar votes.db faylida.

Ustunlar: id, telegram_id, full_name, phone, screenshot_file_id, status, created_at,
          screenshot_unique_id, flags
Holatlar: submitted (oddiy), review (tekshirish kerak), verified (admin tasdiqlagan),
          rejected (rad etilgan)
"""

import sqlite3
from datetime import datetime, date

DB_PATH = "votes.db"


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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
        """INSERT INTO votes
           (telegram_id, full_name, phone, screenshot_file_id,
            status, created_at, screenshot_unique_id, flags)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (telegram_id, full_name, phone, screenshot_file_id,
         status, datetime.utcnow().isoformat(), screenshot_unique_id, flags)
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def get_by_id(row_id: int):
    conn = _conn()
    row = conn.execute("SELECT * FROM votes WHERE id=?", (row_id,)).fetchone()
    conn.close()
    return tuple(row) if row else None


def set_status(row_id: int, status: str):
    conn = _conn()
    conn.execute("UPDATE votes SET status=? WHERE id=?", (status, row_id))
    conn.commit()
    conn.close()


def phone_exists(phone: str) -> bool:
    conn = _conn()
    r = conn.execute(
        "SELECT 1 FROM votes WHERE phone=? AND status!='rejected' LIMIT 1",
        (phone,)
    ).fetchone()
    conn.close()
    return r is not None


def unique_id_exists(unique_id: str) -> bool:
    if not unique_id:
        return False
    conn = _conn()
    r = conn.execute(
        "SELECT 1 FROM votes WHERE screenshot_unique_id=? AND status!='rejected' LIMIT 1",
        (unique_id,)
    ).fetchone()
    conn.close()
    return r is not None


def count_per_tg(telegram_id: int) -> int:
    conn = _conn()
    r = conn.execute(
        "SELECT COUNT(*) FROM votes WHERE telegram_id=? AND status!='rejected'",
        (telegram_id,)
    ).fetchone()
    conn.close()
    return r[0] if r else 0


# ── Statistika funksiyalari ──────────────────────────────────────────────────

def count_total() -> int:
    """Rad etilmaganlar soni."""
    conn = _conn()
    r = conn.execute(
        "SELECT COUNT(*) FROM votes WHERE status != 'rejected'"
    ).fetchone()
    conn.close()
    return r[0] if r else 0


def count_today() -> int:
    """Bugun qo'shilgan (rad etilmagan) yozuvlar soni."""
    today = date.today().isoformat()
    conn = _conn()
    r = conn.execute(
        "SELECT COUNT(*) FROM votes WHERE status != 'rejected' AND created_at LIKE ?",
        (f"{today}%",)
    ).fetchone()
    conn.close()
    return r[0] if r else 0


def count_by_status(status: str) -> int:
    conn = _conn()
    r = conn.execute(
        "SELECT COUNT(*) FROM votes WHERE status=?", (status,)
    ).fetchone()
    conn.close()
    return r[0] if r else 0


def count_all(status_filter: str = None) -> int:
    """Filter bilan jami yozuvlar soni."""
    conn = _conn()
    if status_filter:
        r = conn.execute(
            "SELECT COUNT(*) FROM votes WHERE status=?", (status_filter,)
        ).fetchone()
    else:
        r = conn.execute("SELECT COUNT(*) FROM votes").fetchone()
    conn.close()
    return r[0] if r else 0


# ── Ma'lumot olish funksiyalari ──────────────────────────────────────────────

def _rows_to_tuples(rows):
    return [tuple(r) for r in rows]


def get_recent(n: int = 10) -> list:
    """Oxirgi n ta yozuv (rad etilmaganlar)."""
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM votes WHERE status != 'rejected' ORDER BY id DESC LIMIT ?",
        (n,)
    ).fetchall()
    conn.close()
    return _rows_to_tuples(rows)


def get_by_status(status: str) -> list:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM votes WHERE status=? ORDER BY id DESC",
        (status,)
    ).fetchall()
    conn.close()
    return _rows_to_tuples(rows)


def get_all(status_filter: str = None, limit: int = 30, offset: int = 0) -> list:
    """Filter va pagination bilan barcha yozuvlar."""
    conn = _conn()
    if status_filter:
        rows = conn.execute(
            "SELECT * FROM votes WHERE status=? ORDER BY id DESC LIMIT ? OFFSET ?",
            (status_filter, limit, offset)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM votes ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
    conn.close()
    return _rows_to_tuples(rows)


def search_by_phone(query: str) -> list:
    """Telefon raqami bo'yicha qidirish (qisman moslik)."""
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM votes WHERE phone LIKE ? ORDER BY id DESC LIMIT 50",
        (f"%{query}%",)
    ).fetchall()
    conn.close()
    return _rows_to_tuples(rows)


# ── Boshqaruv ────────────────────────────────────────────────────────────────

def delete_test_data():
    """'test' belgisi bor yoki juda eski (development) yozuvlarni o'chirish."""
    conn = _conn()
    conn.execute("DELETE FROM votes WHERE flags LIKE '%test%'")
    conn.commit()
    conn.close()
