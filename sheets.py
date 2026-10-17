"""
sheets.py — har bir yangi ovozni Google Sheet'ga yuboradi (Apps Script havolasi orqali).
Kerakli o'zgaruvchi (Railway Variables): APPS_SCRIPT_URL. Yo'q bo'lsa, o'tkazib yuboriladi.
"""

import json
import os
import urllib.request


def append_row(vote_id, telegram_id, full_name, phone, status, created_at, flags=""):
    url = os.getenv("APPS_SCRIPT_URL")
    if not url:
        return

    payload = json.dumps({
        "vote_id": vote_id,
        "telegram_id": telegram_id,
        "full_name": full_name,
        "phone": phone,
        "status": status,
        "created_at": created_at,
        "flags": flags or "",
    }).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp.read()
    except Exception as e:
        print(f"[sheets.py] Google Sheets'ga yozishda xato: {e}")
