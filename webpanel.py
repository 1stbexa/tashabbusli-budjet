"""
webpanel.py — brauzerda (va Telegram ichida) ochiladigan zamonaviy admin panel.
Bot bilan bir jarayonda, aiohttp orqali ishlaydi.
"""

import io
import time
from urllib.parse import urlencode

from aiohttp import web

import database as db
import panel_core as core

SESSION_TTL = 7 * 24 * 3600
_failed = {}   # ip -> [vaqtlar]

PER_PAGE = 30


def build_app(bot, secret: bytes, password: str) -> web.Application:

    # ── Auth middleware ──────────────────────────────────────────────────
    @web.middleware
    async def auth_mw(request, handler):
        if request.path in ("/login", "/auth", "/health"):
            return await handler(request)
        if not core.verify(secret, "session", request.cookies.get("sid", "")):
            raise web.HTTPFound("/login")
        return await handler(request)

    def start_session(resp: web.Response) -> web.Response:
        token = core.sign(secret, "session", SESSION_TTL)
        resp.set_cookie("sid", token, max_age=SESSION_TTL,
                        httponly=True, secure=True, samesite="Lax")
        return resp

    # ── Health check ─────────────────────────────────────────────────────
    async def health(request):
        return web.Response(text="ok")

    # ── Login ─────────────────────────────────────────────────────────────
    async def login_get(request):
        return web.Response(text=core.login_page(), content_type="text/html")

    async def login_post(request):
        ip = request.headers.get("X-Forwarded-For",
                                  request.remote or "?").split(",")[0].strip()
        now = time.time()
        recent = [t for t in _failed.get(ip, []) if now - t < 600]
        if len(recent) >= 5:
            return web.Response(
                text=core.login_page("Juda ko'p urinish. 10 daqiqadan keyin qayta urinib ko'ring."),
                content_type="text/html", status=429)
        form = await request.post()
        import hmac as _hmac
        if _hmac.compare_digest(str(form.get("password", "")), password):
            _failed.pop(ip, None)
            return start_session(web.HTTPFound("/"))
        recent.append(now)
        _failed[ip] = recent
        return web.Response(
            text=core.login_page("Parol noto'g'ri!"),
            content_type="text/html", status=401)

    # ── Logout ────────────────────────────────────────────────────────────
    async def logout(request):
        resp = web.HTTPFound("/login")
        resp.del_cookie("sid")
        return resp

    # ── Dashboard / tablar ────────────────────────────────────────────────
    async def index(request):
        tab    = request.rel_url.query.get("tab", "dashboard")
        query  = request.rel_url.query.get("q", "").strip()
        status = request.rel_url.query.get("status", "")
        page   = max(1, int(request.rel_url.query.get("page", "1")))

        # Umumiy statistika (sidebar badge uchun)
        review_count = db.count_by_status("review")

        if tab == "review":
            rows = db.get_by_status("review")
            html = core.review_page(rows, review_count=review_count)

        elif tab == "search":
            rows = db.search_by_phone(query) if query else None
            html = core.search_page(rows=rows, query=query, review_count=review_count)

        elif tab == "recent":
            offset = (page - 1) * PER_PAGE
            rows   = db.get_all(status_filter=status or None,
                                limit=PER_PAGE, offset=offset)
            total  = db.count_all(status_filter=status or None)
            html   = core.list_page(rows, total, status_filter=status,
                                    page=page, per_page=PER_PAGE,
                                    review_count=review_count)

        elif tab == "panel":
            # Veb panel havolasini ko'rsatish (PUBLIC_URL .env dan)
            import os
            url = os.getenv("PUBLIC_URL", request.url.origin().human_repr())
            html = core.panel_link_page(url, review_count=review_count)

        else:
            # Dashboard — asosiy sahifa
            total    = db.count_total()
            today    = db.count_today()
            rejected = db.count_by_status("rejected")
            recent   = db.get_recent(10)
            html = core.dashboard_page(total, today, review_count, rejected,
                                        recent, tab=tab)

        return web.Response(text=html, content_type="text/html")

    # ── Tasdiqlash / rad etish (review tugmalari) ─────────────────────────
    async def action(request):
        form = await request.post()
        row_id = int(form.get("id", 0))
        act    = form.get("action", "")
        if act == "verify":
            db.set_status(row_id, "verified")
            try:
                row = db.get_by_id(row_id)
                if row:
                    await bot.send_message(
                        row[1],
                        "✅ Ishtirokingiz tasdiqlandi! Rahmat.")
            except Exception:
                pass
        elif act == "reject":
            db.set_status(row_id, "rejected")
            try:
                row = db.get_by_id(row_id)
                if row:
                    await bot.send_message(
                        row[1],
                        "❌ Skrinshot rad etildi. Iltimos, qayta yuboring.")
            except Exception:
                pass
        raise web.HTTPFound("/?tab=review")

    # ── Excel eksport ─────────────────────────────────────────────────────
    async def export(request):
        try:
            import export_excel
            buf = io.BytesIO()
            export_excel.write_excel(db.get_all(), buf)
            buf.seek(0)
            fname = time.strftime("votes_%Y%m%d_%H%M%S.xlsx")
            return web.Response(
                body=buf.read(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f'attachment; filename="{fname}"'})
        except Exception as e:
            return web.Response(text=f"Xato: {e}", status=500)

    # ── Test ma'lumotlarini tozalash ──────────────────────────────────────
    async def clear_test(request):
        db.delete_test_data()
        raise web.HTTPFound("/")

    # ── App qurish ────────────────────────────────────────────────────────
    app = web.Application(middlewares=[auth_mw])
    app.router.add_get("/health", health)
    app.router.add_get("/login",  login_get)
    app.router.add_post("/auth",  login_post)
    app.router.add_get("/auth",   lambda r: web.HTTPFound("/login"))  # GET /auth → login
    app.router.add_get("/logout", logout)
    app.router.add_get("/",       index)
    app.router.add_post("/action", action)
    app.router.add_get("/action", lambda r: web.HTTPFound("/"))       # GET /action → home
    app.router.add_get("/export", export)
    app.router.add_post("/clear", clear_test)
    app.router.add_get("/clear",  lambda r: web.HTTPFound("/"))       # GET /clear → home
    return app
