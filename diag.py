"""
diag.py — botning o'zini tekshirish (/diag buyrug'i uchun).
Qaysi fayl yo'q, qaysi o'zgaruvchi kiritilmagan, baza doimiymi — hammasini ko'rsatadi.
Maxfiy qiymatlar (token, parol, havolalar) HECH QACHON ko'rsatilmaydi.
"""

import importlib
import os
import urllib.request

import database as db

MODULES = ["checks", "database", "sheets", "panel_core", "webpanel", "export_excel"]
ENV_KEYS = [
    ("BOT_TOKEN", True), ("ADMIN_ID", True), ("PROJECT_LINK", True), ("PROJECT_NAME", False),
    ("APPS_SCRIPT_URL", False), ("ADMIN_PASSWORD", False), ("PORT", False),
    ("DB_PATH", False), ("RAILWAY_PUBLIC_DOMAIN", False),
]


def modules_lines(import_errors):
    lines = []
    for m in MODULES:
        try:
            importlib.import_module(m)
            lines.append(f"✅ {m}.py")
        except Exception as e:
            lines.append(f"❌ {m}.py — {type(e).__name__}: {str(e)[:70]}")
    for name, err in (import_errors or {}).items():
        lines.append(f"⚠️ bot ishga tushganda {name} yuklanmagan: {err[:70]}")
    return lines


def env_lines():
    lines = []
    for key, required in ENV_KEYS:
        mark = "✅" if os.getenv(key) else ("❌" if required else "➖")
        lines.append(f"{mark} {key}")
    return lines


def db_lines():
    lines = []
    path = db.DB_PATH
    folder = os.path.dirname(os.path.abspath(path))
    try:
        db.init_db()
        total = len(db.get_all(limit=1000000))
        lines.append(f"Baza: {path} — {total} ta yozuv")
        for st in ("submitted", "review", "verified", "rejected"):
            lines.append(f"  {st}: {db.count_by_status(st)}")
    except Exception as e:
        lines.append(f"❌ Baza xatosi: {type(e).__name__}: {e}")
    if os.path.ismount(folder):
        lines.append("✅ Baza doimiy diskda (Volume)")
    else:
        lines.append("⚠️ Baza VAQTINCHALIK: har deploy'da o'chadi (Volume + DB_PATH kerak)")
    return lines


def health_line(public_url, panel_enabled):
    if not panel_enabled:
        return "➖ Veb panel o'chiq (ADMIN_PASSWORD yoki panel fayllari yo'q)"
    if not public_url:
        return "⚠️ Veb panel yoqilgan, lekin domen yo'q (Railway: Generate Domain)"
    try:
        with urllib.request.urlopen(public_url + "/health", timeout=8) as r:
            return "✅ Veb panel tashqaridan ochiladi" if r.read().strip() == b"ok" else "⚠️ /health kutilmagan javob berdi"
    except Exception as e:
        return f"❌ Veb panelga tashqaridan kirib bo'lmadi: {type(e).__name__} (PORT=8080 va domen porti bir xilmi?)"


def build_report(public_url, panel_enabled, import_errors):
    parts = ["🔎 DIAGNOSTIKA", "", "Fayllar:"] + modules_lines(import_errors)
    parts += ["", "Railway Variables:"] + env_lines()
    parts += ["", "Baza:"] + db_lines()
    parts += ["", health_line(public_url, panel_enabled)]
    parts += ["", "Google Sheet'ni sinash: /diag sheets"]
    return "\n".join(parts)
