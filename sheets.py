"""
sheets.py — yozuvlarni Google Sheet'ga yuboradi (Apps Script "Web app" havolasi orqali).
Kerakli o'zgaruvchi (Railway Variables): APPS_SCRIPT_URL
"""

import json
import os
import urllib.error
import urllib.request


def send_row(vote_id, telegram_id, full_name, phone, status, created_at, flags=""):
    """(muvaffaqiyatli_mi, izoh) qaytaradi."""
    url = os.getenv("APPS_SCRIPT_URL")
    if not url:
        return False, "APPS_SCRIPT_URL kiritilmagan (Railway Variables)"

    payload = json.dumps({
        "vote_id": vote_id, "telegram_id": telegram_id, "full_name": full_name,
        "phone": phone, "status": status, "created_at": created_at, "flags": flags or "",
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code} (havola noto'g'ri yoki ruxsat yo'q)"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

    if '"success"' in body.replace(" ", ""):
        return True, "ok"
    return False, ("Apps Script kutilgan javobni bermadi (Deploy'da 'Все/Anyone' tanlanganmi? "
                   "kod to'g'ri joylashtirilganmi?). Javob boshi: " + body[:80].replace("\n", " "))


def append_row(vote_id, telegram_id, full_name, phone, status, created_at, flags=""):
    ok, info = send_row(vote_id, telegram_id, full_name, phone, status, created_at, flags)
    if not ok and os.getenv("APPS_SCRIPT_URL"):
        print(f"[sheets.py] Google Sheets'ga yozilmadi: {info}")
