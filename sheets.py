"""
sheets.py — har bir yangi ovozni Google Sheet'ga yuboradi.

Google Apps Script "Web app" havolasiga oddiy so'rov yuboriladi
(JSON kalit, Google Cloud yoki qo'shimcha kutubxona kerak emas).

Kerakli o'zgaruvchi (Railway Variables): APPS_SCRIPT_URL
Agar u kiritilmagan bo'lsa, bot yiqilmaydi — shunchaki o'tkazib yuboradi.
"""

import json
import os
import urllib.request


def append_row(vote_id, telegram_id, full_name, phone, status, created_at):
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
    }).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp.read()
    except Exception as e:
        print(f"[sheets.py] Google Sheets'ga yozishda xato: {e}")
