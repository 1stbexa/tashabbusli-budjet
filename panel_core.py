"""
panel_core.py — veb panelning "toza" qismi: imzolangan token va HTML sahifalar.
(aiohttp/Telegram'ga bog'liq emas, shuning uchun alohida sinab ko'rish mumkin.)

Dizayn: Figma-inspired zamonaviy dashboard (dark sidebar + clean cards)
"""

import hashlib
import hmac
import time
from html import escape

STATUS_LABELS = {
    "submitted": ("Yuborilgan", "badge-gray"),
    "review": ("Tekshirish kerak", "badge-orange"),
    "verified": ("Tasdiqlangan", "badge-green"),
    "rejected": ("Rad etilgan", "badge-red"),
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


# ─────────────────────────────────────────────
#  GLOBAL CSS  (Figma-inspired, Inter font)
# ─────────────────────────────────────────────
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --primary:      #4F6EF7;
  --primary-dark: #3B56D9;
  --primary-soft: #EEF1FF;
  --sidebar-bg:   #0F172A;
  --sidebar-text: #94A3B8;
  --sidebar-active:#fff;
  --body-bg:      #F1F5F9;
  --card-bg:      #FFFFFF;
  --border:       #E2E8F0;
  --text-main:    #0F172A;
  --text-muted:   #64748B;
  --green:        #22C55E;
  --green-soft:   #DCFCE7;
  --orange:       #F59E0B;
  --orange-soft:  #FEF3C7;
  --red:          #EF4444;
  --red-soft:     #FEE2E2;
  --gray-soft:    #F1F5F9;
  --radius:       12px;
  --shadow:       0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.04);
  --shadow-md:    0 4px 6px -1px rgba(0,0,0,.10), 0 2px 4px -1px rgba(0,0,0,.06);
}

html, body {
  height: 100%;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--body-bg);
  color: var(--text-main);
  font-size: 14px;
  line-height: 1.5;
}

/* ── LAYOUT ── */
.layout { display: flex; min-height: 100vh; }

/* ── SIDEBAR ── */
.sidebar {
  width: 240px;
  background: var(--sidebar-bg);
  display: flex;
  flex-direction: column;
  padding: 24px 0;
  position: fixed;
  top: 0; left: 0; bottom: 0;
  z-index: 100;
  transition: width .25s;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px 24px;
  border-bottom: 1px solid rgba(255,255,255,.06);
  margin-bottom: 16px;
}
.sidebar-logo .logo-icon {
  width: 36px; height: 36px;
  background: var(--primary);
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; flex-shrink: 0;
}
.sidebar-logo span { color: #fff; font-weight: 700; font-size: 15px; }

.nav-section { padding: 0 12px; margin-bottom: 8px; }
.nav-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: #475569;
  padding: 0 8px;
  margin-bottom: 4px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 8px;
  color: var(--sidebar-text);
  text-decoration: none;
  font-size: 13.5px;
  font-weight: 500;
  transition: background .15s, color .15s;
  cursor: pointer;
}
.nav-item:hover { background: rgba(255,255,255,.06); color: #CBD5E1; }
.nav-item.active { background: var(--primary); color: #fff; }
.nav-item .icon { font-size: 16px; width: 20px; text-align: center; flex-shrink: 0; }
.nav-item .badge-count {
  margin-left: auto;
  background: var(--red);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 20px;
  min-width: 20px;
  text-align: center;
}

.sidebar-footer {
  margin-top: auto;
  padding: 16px 12px 0;
  border-top: 1px solid rgba(255,255,255,.06);
}

/* ── MAIN CONTENT ── */
.content {
  margin-left: 240px;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* ── TOPBAR ── */
.topbar {
  background: var(--card-bg);
  border-bottom: 1px solid var(--border);
  padding: 0 28px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky; top: 0; z-index: 50;
}
.topbar-title { font-size: 16px; font-weight: 600; color: var(--text-main); }
.topbar-right { display: flex; align-items: center; gap: 12px; }
.topbar-time {
  font-size: 12px;
  color: var(--text-muted);
  background: var(--gray-soft);
  padding: 4px 10px;
  border-radius: 6px;
}
.avatar {
  width: 34px; height: 34px;
  background: var(--primary);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-weight: 700; font-size: 14px;
}

/* ── PAGE CONTENT ── */
.page { padding: 28px; }

/* ── STAT CARDS ── */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.stat-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: box-shadow .2s, transform .2s;
}
.stat-card:hover { box-shadow: var(--shadow-md); transform: translateY(-1px); }
.stat-icon {
  width: 40px; height: 40px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px;
  margin-bottom: 4px;
}
.stat-icon.blue   { background: #EEF1FF; }
.stat-icon.green  { background: var(--green-soft); }
.stat-icon.orange { background: var(--orange-soft); }
.stat-icon.red    { background: var(--red-soft); }
.stat-value { font-size: 28px; font-weight: 700; color: var(--text-main); line-height: 1; }
.stat-label { font-size: 12px; color: var(--text-muted); font-weight: 500; }

/* ── CARD CONTAINER ── */
.card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
  margin-bottom: 20px;
}
.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.card-title { font-size: 15px; font-weight: 600; color: var(--text-main); }
.card-body { padding: 20px; }

/* ── FILTER BAR ── */
.filter-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.filter-bar input,
.filter-bar select {
  font-family: inherit;
  font-size: 13px;
  padding: 7px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--card-bg);
  color: var(--text-main);
  outline: none;
  transition: border-color .15s, box-shadow .15s;
}
.filter-bar input:focus,
.filter-bar select:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(79,110,247,.12);
}

/* ── BUTTONS ── */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  padding: 7px 14px;
  border-radius: 8px;
  border: 1px solid transparent;
  cursor: pointer;
  text-decoration: none;
  transition: background .15s, border-color .15s, box-shadow .15s, transform .1s;
  white-space: nowrap;
}
.btn:active { transform: scale(.97); }
.btn-primary  { background: var(--primary); color: #fff; border-color: var(--primary); }
.btn-primary:hover { background: var(--primary-dark); border-color: var(--primary-dark); }
.btn-outline  { background: transparent; color: var(--text-main); border-color: var(--border); }
.btn-outline:hover { background: var(--gray-soft); }
.btn-green    { background: var(--green); color: #fff; border-color: var(--green); }
.btn-green:hover { background: #16A34A; }
.btn-red      { background: var(--red); color: #fff; border-color: var(--red); }
.btn-red:hover { background: #DC2626; }
.btn-sm { padding: 4px 10px; font-size: 12px; border-radius: 6px; }
.btn-ghost { background: transparent; color: var(--text-muted); border-color: transparent; }
.btn-ghost:hover { background: var(--gray-soft); color: var(--text-main); }

/* ── TABLE ── */
.table-wrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 13.5px; }
thead tr { background: #F8FAFC; }
th {
  padding: 10px 14px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: .04em;
  text-transform: uppercase;
  color: var(--text-muted);
  white-space: nowrap;
  border-bottom: 1px solid var(--border);
}
td {
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
  color: var(--text-main);
}
tbody tr:last-child td { border-bottom: none; }
tbody tr:hover { background: #F8FAFC; }

.td-name { font-weight: 500; }
.td-phone { font-family: 'Courier New', monospace; font-size: 13px; color: var(--text-muted); }
.td-date { font-size: 12px; color: var(--text-muted); white-space: nowrap; }
.td-actions { display: flex; gap: 6px; flex-wrap: wrap; }
td form { display: inline; }

/* ── BADGES ── */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 9px;
  border-radius: 20px;
  font-size: 11.5px;
  font-weight: 600;
  white-space: nowrap;
}
.badge-gray   { background: var(--gray-soft); color: #475569; }
.badge-orange { background: var(--orange-soft); color: #92400E; }
.badge-green  { background: var(--green-soft); color: #166534; }
.badge-red    { background: var(--red-soft); color: #991B1B; }

/* ── SCREENSHOT LINK ── */
.screenshot-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--primary);
  text-decoration: none;
  font-weight: 500;
}
.screenshot-link:hover { text-decoration: underline; }

/* ── EMPTY STATE ── */
.empty-state {
  padding: 60px 20px;
  text-align: center;
  color: var(--text-muted);
}
.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-state p { font-size: 15px; font-weight: 500; }
.empty-state small { font-size: 13px; }

/* ── ALERT ── */
.alert {
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.alert-red    { background: var(--red-soft); color: #991B1B; border: 1px solid #FECACA; }
.alert-green  { background: var(--green-soft); color: #166534; border: 1px solid #BBF7D0; }
.alert-orange { background: var(--orange-soft); color: #92400E; border: 1px solid #FDE68A; }

/* ── PAGINATION ── */
.pagination { display: flex; gap: 4px; justify-content: center; padding: 16px 0 4px; }
.pagination a, .pagination span {
  display: inline-flex; align-items: center; justify-content: center;
  width: 32px; height: 32px;
  border-radius: 8px;
  font-size: 13px; font-weight: 500;
  text-decoration: none;
  color: var(--text-muted);
  border: 1px solid var(--border);
  background: var(--card-bg);
  transition: background .15s, color .15s;
}
.pagination a:hover { background: var(--gray-soft); color: var(--text-main); }
.pagination .current { background: var(--primary); color: #fff; border-color: var(--primary); }

/* ── DIVIDER ── */
.divider { height: 1px; background: var(--border); margin: 16px 0; }

/* ── RESPONSIVE ── */
@media (max-width: 768px) {
  .sidebar { width: 60px; }
  .sidebar-logo span, .nav-item span, .nav-label { display: none; }
  .content { margin-left: 60px; }
  .page { padding: 16px; }
  .stat-grid { grid-template-columns: 1fr 1fr; }
}

/* ── ANIMATIONS ── */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.page { animation: fadeIn .25s ease; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 10px; }
"""

# ─────────────────────────────────────────────
#  SHARED LAYOUT HELPERS
# ─────────────────────────────────────────────

def _sidebar(active: str = "", review_count: int = 0) -> str:
    items = [
        ("📊", "Statistika",        "/",          "dashboard"),
        ("🕘", "So'nggi yozuvlar",  "/?tab=recent","recent"),
        ("⚠️", "Tekshirish kerak",  "/?tab=review","review", review_count),
        ("🔍", "Qidirish",          "/?tab=search","search"),
        ("📥", "Excel eksport",     "/export",     "export"),
        ("🖥",  "Veb panel sozlash","/?tab=panel", "panel"),
    ]

    nav_html = ""
    for item in items:
        icon, label, href, key = item[0], item[1], item[2], item[3]
        count = item[4] if len(item) > 4 else 0
        is_active = "active" if active == key else ""
        badge_html = f'<span class="badge-count">{count}</span>' if count and count > 0 else ""
        nav_html += f"""
        <a href="{href}" class="nav-item {is_active}">
          <span class="icon">{icon}</span>
          <span>{label}</span>
          {badge_html}
        </a>"""

    return f"""
<aside class="sidebar">
  <div class="sidebar-logo">
    <div class="logo-icon">🗳</div>
    <span>Admin Panel</span>
  </div>
  <div class="nav-section">
    <div class="nav-label">Asosiy</div>
    {nav_html}
  </div>
  <div class="sidebar-footer">
    <a href="/logout" class="nav-item">
      <span class="icon">🚪</span>
      <span>Chiqish</span>
    </a>
  </div>
</aside>"""


def _topbar(title: str) -> str:
    now = time.strftime("%d.%m.%Y  %H:%M")
    return f"""
<div class="topbar">
  <div class="topbar-title">{escape(title)}</div>
  <div class="topbar-right">
    <span class="topbar-time">🕒 {now}</span>
    <div class="avatar">A</div>
  </div>
</div>"""


def _page_wrap(title: str, body: str, active: str = "dashboard", review_count: int = 0) -> str:
    return f"""<!DOCTYPE html>
<html lang="uz">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} — Admin Panel</title>
  <style>{CSS}</style>
</head>
<body>
<div class="layout">
  {_sidebar(active, review_count)}
  <div class="content">
    {_topbar(title)}
    <div class="page">
      {body}
    </div>
  </div>
</div>
<script>
  // Active nav highlight from URL
  document.querySelectorAll('.nav-item').forEach(el => {{
    if (el.href && window.location.href.startsWith(el.href) && el.href !== window.location.origin + '/') return;
  }});
</script>
</body>
</html>"""


# ─────────────────────────────────────────────
#  STAT CARDS
# ─────────────────────────────────────────────

def _stat_cards(total: int, today: int, review: int, rejected: int) -> str:
    cards = [
        ("blue",   "📊", "Jami ishtirokchi",    total,    "Rad etilmagan"),
        ("green",  "✅", "Bugun tasdiqlangan",   today,    "Bugungi ko'rsatkich"),
        ("orange", "⚠️", "Tekshirish kerak",    review,   "Admin tasdiqini kutmoqda"),
        ("red",    "❌", "Rad etilgan",         rejected, "Noto'g'ri yozuvlar"),
    ]
    html = '<div class="stat-grid">'
    for color, icon, label, value, sub in cards:
        html += f"""
    <div class="stat-card">
      <div class="stat-icon {color}">{icon}</div>
      <div class="stat-value">{value}</div>
      <div class="stat-label">{label}</div>
      <div style="font-size:11px;color:var(--text-muted);margin-top:2px">{sub}</div>
    </div>"""
    html += "</div>"
    return html


# ─────────────────────────────────────────────
#  TABLE BUILDER
# ─────────────────────────────────────────────

def _table(rows, show_actions: bool = False, bot_url: str = "") -> str:
    if not rows:
        return """
    <div class="empty-state">
      <div class="empty-icon">📭</div>
      <p>Hech narsa topilmadi</p>
      <small>Ushbu bo'limda yozuvlar yo'q</small>
    </div>"""

    header = """
    <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Ism</th>
          <th>Telefon</th>
          <th>Holat</th>
          <th>Skrinshot</th>
          <th>Sana</th>
          <th>Belgilar</th>
    """
    if show_actions:
        header += "<th>Amallar</th>"
    header += "</tr></thead><tbody>"

    body = ""
    for row in rows:
        rid, tg_id, name, phone, file_id, status, created, unique_id = row[:8]
        flags = row[8] if len(row) > 8 else ""
        label, badge_cls = STATUS_LABELS.get(status, (status, "badge-gray"))
        date_str = str(created)[:16].replace("T", " ") if created else "—"

        screenshot_html = "—"
        if file_id:
            # Telegram file havolasi (agar bot_url bo'lsa)
            screenshot_html = f'<a class="screenshot-link" href="{escape(bot_url)}?file={escape(file_id)}" target="_blank">📎 Ko\'rish</a>'

        actions_html = ""
        if show_actions:
            actions_html = f"""<td class="td-actions">
              <form method="post" action="/action" style="display:inline">
                <input type="hidden" name="id" value="{rid}">
                <input type="hidden" name="action" value="verify">
                <button class="btn btn-sm btn-green" type="submit">✅</button>
              </form>
              <form method="post" action="/action" style="display:inline">
                <input type="hidden" name="id" value="{rid}">
                <input type="hidden" name="action" value="reject">
                <button class="btn btn-sm btn-red" type="submit">❌</button>
              </form>
            </td>"""

        body += f"""
      <tr>
        <td style="font-size:12px;color:var(--text-muted)">{rid}</td>
        <td class="td-name">{escape(str(name or '—'))}</td>
        <td class="td-phone">{escape(str(phone or '—'))}</td>
        <td><span class="badge {badge_cls}">{label}</span></td>
        <td>{screenshot_html}</td>
        <td class="td-date">{date_str}</td>
        <td style="font-size:11px;color:var(--text-muted)">{escape(str(flags or ''))}</td>
        {actions_html if show_actions else ''}
      </tr>"""

    return header + body + "</tbody></table></div>"


# ─────────────────────────────────────────────
#  LOGIN PAGE
# ─────────────────────────────────────────────

def login_page(error: str = "") -> str:
    error_html = ""
    if error:
        error_html = f'<div class="alert alert-red">⚠️ {escape(error)}</div>'

    return f"""<!DOCTYPE html>
<html lang="uz">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Kirish — Admin Panel</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', sans-serif;
      background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F172A 100%);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }}
    .login-box {{
      background: #fff;
      border-radius: 20px;
      padding: 40px;
      width: 100%;
      max-width: 380px;
      box-shadow: 0 25px 50px rgba(0,0,0,.35);
    }}
    .login-logo {{
      text-align: center;
      margin-bottom: 28px;
    }}
    .login-icon {{
      width: 60px; height: 60px;
      background: #4F6EF7;
      border-radius: 16px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 28px;
      margin-bottom: 12px;
    }}
    .login-logo h1 {{
      font-size: 20px;
      font-weight: 700;
      color: #0F172A;
    }}
    .login-logo p {{
      font-size: 13px;
      color: #64748B;
      margin-top: 4px;
    }}
    label {{
      display: block;
      font-size: 13px;
      font-weight: 500;
      color: #374151;
      margin-bottom: 6px;
    }}
    input[type=password] {{
      width: 100%;
      padding: 11px 14px;
      border: 1.5px solid #E2E8F0;
      border-radius: 10px;
      font-size: 14px;
      font-family: inherit;
      outline: none;
      transition: border-color .15s, box-shadow .15s;
      margin-bottom: 16px;
    }}
    input[type=password]:focus {{
      border-color: #4F6EF7;
      box-shadow: 0 0 0 3px rgba(79,110,247,.15);
    }}
    button {{
      width: 100%;
      padding: 12px;
      background: #4F6EF7;
      color: #fff;
      border: none;
      border-radius: 10px;
      font-size: 15px;
      font-weight: 600;
      font-family: inherit;
      cursor: pointer;
      transition: background .15s, transform .1s;
    }}
    button:hover {{ background: #3B56D9; }}
    button:active {{ transform: scale(.98); }}
    .alert {{
      padding: 11px 14px;
      background: #FEE2E2;
      border: 1px solid #FECACA;
      color: #991B1B;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 500;
      margin-bottom: 16px;
    }}
    .footer-text {{
      text-align: center;
      font-size: 12px;
      color: #94A3B8;
      margin-top: 20px;
    }}
  </style>
</head>
<body>
  <div class="login-box">
    <div class="login-logo">
      <div class="login-icon">🗳</div>
      <h1>Admin Panel</h1>
      <p>Ovoz yig'ish boshqaruvi</p>
    </div>
    {error_html}
    <form method="post" action="/auth">
      <label for="pw">Parol</label>
      <input type="password" id="pw" name="password" placeholder="••••••••" autofocus required>
      <button type="submit">Kirish →</button>
    </form>
    <div class="footer-text">Faqat adminlar uchun</div>
  </div>
</body>
</html>"""


# ─────────────────────────────────────────────
#  DASHBOARD (asosiy sahifa)
# ─────────────────────────────────────────────

def dashboard_page(total: int, today: int, review: int, rejected: int,
                   recent_rows: list, tab: str = "dashboard") -> str:
    stats_html = _stat_cards(total, today, review, rejected)

    table_html = _table(recent_rows)

    body = f"""
{stats_html}

<div class="card">
  <div class="card-header">
    <span class="card-title">🕘 So'nggi ishtirokchilar</span>
    <a href="/?tab=recent" class="btn btn-outline btn-sm">Barchasini ko'rish</a>
  </div>
  {table_html}
</div>
"""
    return _page_wrap("Dashboard", body, active="dashboard", review_count=review)


# ─────────────────────────────────────────────
#  REVIEW sahifasi
# ─────────────────────────────────────────────

def review_page(rows: list, review_count: int = 0) -> str:
    alert = ""
    if not rows:
        alert = '<div class="alert alert-green">✅ Tekshirishni kutayotgan yozuvlar yo\'q!</div>'

    table_html = _table(rows, show_actions=True)

    body = f"""
{alert}
<div class="card">
  <div class="card-header">
    <span class="card-title">⚠️ Tekshirish kerak</span>
    <span class="badge badge-orange">{review_count} ta</span>
  </div>
  {table_html}
</div>
"""
    return _page_wrap("Tekshirish kerak", body, active="review", review_count=review_count)


# ─────────────────────────────────────────────
#  SEARCH sahifasi
# ─────────────────────────────────────────────

def search_page(rows: list = None, query: str = "", review_count: int = 0) -> str:
    result_html = ""
    if rows is not None:
        count = len(rows)
        result_html = f"""
<div class="card" style="margin-top:16px">
  <div class="card-header">
    <span class="card-title">Natijalar: <b>{count}</b> ta topildi</span>
  </div>
  {_table(rows)}
</div>"""

    body = f"""
<div class="card">
  <div class="card-header">
    <span class="card-title">🔍 Raqam bo'yicha qidirish</span>
  </div>
  <div class="card-body">
    <form method="get" action="/?tab=search" class="filter-bar">
      <input type="hidden" name="tab" value="search">
      <input type="text" name="q" value="{escape(query)}"
             placeholder="Telefon raqami kiriting..." style="min-width:240px">
      <button type="submit" class="btn btn-primary">🔍 Qidirish</button>
    </form>
  </div>
</div>
{result_html}
"""
    return _page_wrap("Qidirish", body, active="search", review_count=review_count)


# ─────────────────────────────────────────────
#  FULL LIST sahifasi (filter + pagination)
# ─────────────────────────────────────────────

def list_page(rows: list, total: int, status_filter: str = "",
              page: int = 1, per_page: int = 30, review_count: int = 0) -> str:
    status_options = [
        ("", "Barcha holatlar"),
        ("submitted", "Yuborilgan"),
        ("review",    "Tekshirish kerak"),
        ("verified",  "Tasdiqlangan"),
        ("rejected",  "Rad etilgan"),
    ]
    opts_html = ""
    for val, lbl in status_options:
        sel = "selected" if val == status_filter else ""
        opts_html += f'<option value="{val}" {sel}>{lbl}</option>'

    pages_total = max(1, (total + per_page - 1) // per_page)
    pag_html = ""
    for p in range(1, pages_total + 1):
        cls = "current" if p == page else ""
        pag_html += f'<a href="/?tab=recent&status={status_filter}&page={p}" class="{cls}">{p}</a>'

    table_html = _table(rows)

    body = f"""
<div class="card">
  <div class="card-header">
    <span class="card-title">🕘 Barcha yozuvlar ({total} ta)</span>
    <div class="filter-bar">
      <form method="get" action="/" class="filter-bar">
        <input type="hidden" name="tab" value="recent">
        <select name="status" onchange="this.form.submit()">{opts_html}</select>
        <button type="submit" class="btn btn-outline btn-sm">Filtrlash</button>
      </form>
      <a href="/export" class="btn btn-primary btn-sm">📥 Excel</a>
    </div>
  </div>
  {table_html}
  <div class="pagination">{pag_html}</div>
</div>
"""
    return _page_wrap("Barcha yozuvlar", body, active="recent", review_count=review_count)


# ─────────────────────────────────────────────
#  PANEL LINK SAHIFASI
# ─────────────────────────────────────────────

def panel_link_page(url: str, review_count: int = 0) -> str:
    body = f"""
<div class="card" style="max-width:480px">
  <div class="card-body">
    <div class="empty-state" style="padding:30px 0">
      <div class="empty-icon">🖥</div>
      <p>Veb panel havolasi</p>
      <small style="display:block;margin:12px 0">{escape(url)}</small>
      <a href="{escape(url)}" class="btn btn-primary" target="_blank">Ochish →</a>
    </div>
  </div>
</div>
"""
    return _page_wrap("Veb panel", body, active="panel", review_count=review_count)
