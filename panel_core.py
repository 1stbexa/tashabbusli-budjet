"""
panel_core.py — veb panelning "toza" qismi: imzolangan token va HTML sahifalar.
(aiohttp/Telegram'ga bog'liq emas, shuning uchun alohida sinab ko'rish mumkin.)
"""

import hashlib
import hmac
import time
from html import escape

STATUS_LABELS = {
    "submitted": ("Yuborilgan", "b-gray"),
    "review": ("Tekshirish kerak", "b-orange"),
    "verified": ("Tasdiqlangan", "b-green"),
    "rejected": ("Rad etilgan", "b-red"),
}


def make_secret(bot_token: str, password: str) -> bytes:
    return hashlib.sha256(f"{bot_token}|{password}".encode()).digest()


def sign(secret: bytes, purpose: str, ttl_seconds: int) -> str:
    exp = int(time.time()) + ttl_seconds
    msg = f"{purpose}.{exp}"
    sig = hmac.new(secret, msg.encode(), hashlib.sha256).hexdigest()
    return f"{msg}.{sig}"


def verify(secret: bytes, purpose: str, token: str) -> bool:
    try:
        p, exp, sig = (token or "").split(".")
        if p != purpose or int(exp) < time.time():
            return False
    except ValueError:
        return False
    expected = hmac.new(secret, f"{p}.{exp}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


CSS = """
*{box-sizing:border-box}body{margin:0;font-family:-apple-system,Segoe UI,Arial,sans-serif;background:#f3f5f7;color:#1c2430}
header{background:#1c4b63;color:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:center}
header h1{font-size:17px;margin:0}header a{color:#fff;font-size:13px;margin-left:14px}
main{max-width:1100px;margin:0 auto;padding:16px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-bottom:14px}
.card{background:#fff;border:1px solid #dde3e8;border-radius:8px;padding:12px}.card b{display:block;font-size:24px}
.card span{font-size:12px;color:#5b6b76}
form.filter{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
input,select,button{font:inherit;padding:8px 10px;border:1px solid #c5ced6;border-radius:6px;background:#fff}
button{cursor:pointer}button.primary{background:#1c4b63;color:#fff;border-color:#1c4b63}
.wrap{overflow-x:auto;background:#fff;border:1px solid #dde3e8;border-radius:8px}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:9px 10px;border-bottom:1px solid #eef1f4;text-align:left;vertical-align:top}
th{background:#f7f9fa;font-size:12px;color:#5b6b76;white-space:nowrap}
.badge{padding:2px 8px;border-radius:10px;font-size:12px;white-space:nowrap}
.b-gray{background:#e8ecef}.b-orange{background:#ffe7c2}.b-green{background:#d5f0dc}.b-red{background:#fbd6d6}
td form{display:inline}td button{padding:4px 8px;font-size:12px}
.small{font-size:12px;color:#5b6b76}.login{max-width:320px;margin:15vh auto;background:#fff;padding:22px;border-radius:10px;border:1px solid #dde3e8}
.login input{width:100%;margin:10px 0}.err{color:#b3261e;font-size:13px}
"""


def page(title: str, body: str) -> str:
    return (
        "<!DOCTYPE html><html lang='uz'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{escape(title)}</title><style>{CSS}</style></head><body>{body}</body></html>"
    )


def login_page(error: str = "") -> str:
    err = f"<div class='err'>{escape(error)}</div>" if error else ""
    return page("Kirish", (
        "<form class='login' method='post' action='/login'><h2 style='margin-top:0'>Admin panel</h2>"
        f"{err}<input type='password' name='password' placeholder='Parol' autofocus required>"
        "<button class='primary' style='width:100%'>Kirish</button></form>"
    ))


def dashboard_page(stats: dict, rows, q: str, status: str, query_string: str) -> str:
    cards = "".join(
        f"<div class='card'><b>{v}</b><span>{escape(k)}</span></div>" for k, v in stats.items()
    )
    opts = "<option value=''>Barcha holatlar</option>" + "".join(
        f"<option value='{k}'{' selected' if k == status else ''}>{escape(v[0])}</option>"
        for k, v in STATUS_LABELS.items()
    )
    trs = []
    for r in rows:
        # id, telegram_id, full_name, phone, file_id, status, created_at, unique_id, flags
        label, cls = STATUS_LABELS.get(r[5], (r[5], "b-gray"))
        flags = escape(r[8]) if len(r) > 8 and r[8] else ""
        when = escape(str(r[6])[:16].replace("T", " "))

        def btn(new, text):
            return (
                "<form method='post' action='/status'>"
                f"<input type='hidden' name='vote_id' value='{r[0]}'>"
                f"<input type='hidden' name='status' value='{new}'>"
                f"<input type='hidden' name='next' value='{escape(query_string, quote=True)}'>"
                f"<button>{text}</button></form> "
            )

        actions = ""
        if r[5] != "verified":
            actions += btn("verified", "✅ Tasdiqlash")
        if r[5] != "rejected":
            actions += btn("rejected", "❌ Rad etish")
        if r[5] in ("verified", "rejected"):
            actions += btn("submitted", "↩ Tiklash")
        trs.append(
            f"<tr><td>{r[0]}</td><td>{escape(r[2] or '')}<div class='small'>TG: {r[1]}</div></td>"
            f"<td>{escape(r[3] or '')}</td><td><span class='badge {cls}'>{escape(label)}</span></td>"
            f"<td class='small'>{flags}</td><td class='small'>{when}</td>"
            f"<td><a href='/photo/{r[0]}' target='_blank'>Ko'rish</a></td><td>{actions}</td></tr>"
        )
    table = (
        "<div class='wrap'><table><tr><th>#</th><th>Ism</th><th>Raqam</th><th>Holat</th>"
        "<th>Belgilar</th><th>Vaqt</th><th>Skrinshot</th><th>Amal</th></tr>"
        + ("".join(trs) or "<tr><td colspan='8' class='small'>Hech narsa topilmadi.</td></tr>")
        + "</table></div>"
    )
    body = (
        "<header><h1>🗳 Ovoz ro'yxati</h1><span><a href='/export.xlsx'>📥 Excel</a>"
        "<a href='/logout'>Chiqish</a></span></header><main>"
        f"<div class='cards'>{cards}</div>"
        "<form class='filter' method='get' action='/'>"
        f"<input name='q' value='{escape(q, quote=True)}' placeholder='Ism, raqam yoki Telegram ID'>"
        f"<select name='status'>{opts}</select><button class='primary'>Qidirish</button></form>"
        f"{table}<p class='small'>Eng oxirgi 300 ta yozuv ko'rsatiladi.</p></main>"
    )
    return page("Admin panel", body)
