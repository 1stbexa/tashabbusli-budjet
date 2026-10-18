"""
webpanel.py — brauzerda (va Telegram ichida) ochiladigan admin panel.
Bot bilan bir jarayonda, aiohttp orqali ishlaydi.

Tuzatishlar (oldingi versiyaga nisbatan):
  * /auth?t=... — botdagi "Panelni ochish" havolasi endi parolsiz kiritadi
  * ?file=<file_id> — skrinshotni panelda ochish (oldin havola ishlamas edi)
  * Excel: mavjud export_excel.make_excel_file ishlatiladi (write_excel yo'q edi)
  * Parol tekshiruvi va "page" parametri xatolarga chidamli
"""

import hmac
import time

from aiohttp import web

import database as db
import panel_core as core

SESSION_TTL = 7 * 24 * 3600
_failed = {}  # ip -> [vaqtlar]
PER_PAGE = 30


def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_app(bot, secret: bytes, password: str) -> web.Application:
    @web.middleware
    async def auth_mw(request, handler):
        if request.path in ("/login", "/auth", "/health"):
            return await handler(request)
        if not core.verify(secret, "session", request.cookies.get("sid", "")):
            raise web.HTTPFound("/login")
        return await handler(request)

    def start_session(resp):
        token = core.sign(secret, "session", SESSION_TTL)
        resp.set_cookie("sid", token, max_age=SESSION_TTL,
                        httponly=True, secure=True, samesite="Lax")
        return resp

    async def health(request):
        return web.Response(text="ok")

    async def login_get(request):
        return web.Response(text=core.login_page(), content_type="text/html")

    async def auth_get(request):
        """Botdagi /panel havolasi: imzolangan 10 daqiqalik token."""
        if core.verify(secret, "magic", request.query.get("t", "")):
            return start_session(web.HTTPFound("/"))
        raise web.HTTPFound("/login")

    async def login_post(request):
        ip = request.headers.get("X-Forwarded-For", request.remote or "?").split(",")[0].strip()
        now = time.time()
        recent = [t for t in _failed.get(ip, []) if now - t < 600]
        if len(recent) >= 5:
            return web.Response(
                text=core.login_page("Juda ko'p urinish. 10 daqiqadan keyin qayta urinib ko'ring."),
                content_type="text/html", status=429)
        form = await request.post()
        given = str(form.get("password", "")).encode("utf-8")
        if hmac.compare_digest(given, password.encode("utf-8")):
            _failed.pop(ip, None)
            return start_session(web.HTTPFound("/"))
        recent.append(now)
        _failed[ip] = recent
        return web.Response(text=core.login_page("Parol noto'g'ri!"),
                            content_type="text/html", status=401)

    async def logout(request):
        resp = web.HTTPFound("/login")
        resp.del_cookie("sid")
        return resp

    async def send_screenshot(file_id: str):
        import io
        try:
            f = await bot.get_file(file_id)
            buf = io.BytesIO()
            await bot.download_file(f.file_path, buf)
        except Exception:
            raise web.HTTPNotFound(text="Rasm topilmadi")
        return web.Response(body=buf.getvalue(), content_type="image/jpeg",
                            headers={"Cache-Control": "private, max-age=3600"})

    async def index(request):
        q = request.rel_url.query

        # Skrinshotni ko'rish: /?file=<telegram file_id>
        if q.get("file"):
            return await send_screenshot(q["file"])

        tab = q.get("tab", "dashboard")
        query = q.get("q", "").strip()
        status = q.get("status", "")
        page = max(1, _to_int(q.get("page", "1"), 1))
        review_count = db.count_by_status("review")

        if tab == "review":
            html = core.review_page(db.get_by_status("review"), review_count=review_count)
        elif tab == "search":
            rows = db.search_by_phone(query) if query else None
            html = core.search_page(rows=rows, query=query, review_count=review_count)
        elif tab == "recent":
            offset = (page - 1) * PER_PAGE
            rows = db.get_all(status_filter=status or None, limit=PER_PAGE, offset=offset)
            total = db.count_all(status_filter=status or None)
            html = core.list_page(rows, total, status_filter=status, page=page,
                                  per_page=PER_PAGE, review_count=review_count)
        elif tab == "panel":
            import os
            url = os.getenv("PUBLIC_URL") or (
                "https://" + os.getenv("RAILWAY_PUBLIC_DOMAIN", "") if os.getenv("RAILWAY_PUBLIC_DOMAIN")
                else request.url.origin().human_repr())
            html = core.panel_link_page(url, review_count=review_count)
        else:
            html = core.dashboard_page(db.count_total(), db.count_today(), review_count,
                                       db.count_by_status("rejected"), db.get_recent(10), tab=tab)
        return web.Response(text=html, content_type="text/html")

    async def action(request):
        form = await request.post()
        row_id = _to_int(form.get("id"), 0)
        act = form.get("action", "")
        if act in ("verify", "reject") and db.get_by_id(row_id):
            db.set_status(row_id, "verified" if act == "verify" else "rejected")
            try:
                row = db.get_by_id(row_id)
                text = ("✅ Ishtirokingiz tasdiqlandi! Rahmat." if act == "verify"
                        else "❌ Skrinshot rad etildi. Iltimos, qayta yuboring.")
                await bot.send_message(row[1], text)
            except Exception:
                pass
        raise web.HTTPFound("/?tab=review")

    async def export(request):
        try:
            import export_excel
            with open(export_excel.make_excel_file(), "rb") as fh:
                data = fh.read()
            fname = time.strftime("votes_%Y%m%d_%H%M%S.xlsx")
            return web.Response(
                body=data,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f'attachment; filename="{fname}"'})
        except Exception as e:
            return web.Response(text=f"Xato: {e}", status=500)

    async def clear_test(request):
        db.delete_test_data()
        raise web.HTTPFound("/")

    app = web.Application(middlewares=[auth_mw])
    app.router.add_get("/health", health)
    app.router.add_get("/login", login_get)
    app.router.add_post("/auth", login_post)   # login formasi shu yerga yuboradi
    app.router.add_get("/auth", auth_get)      # botdagi magic havola
    app.router.add_get("/logout", logout)
    app.router.add_get("/", index)
    app.router.add_post("/action", action)
    app.router.add_get("/action", lambda r: web.HTTPFound("/"))
    app.router.add_get("/export", export)
    app.router.add_post("/clear", clear_test)
    app.router.add_get("/clear", lambda r: web.HTTPFound("/"))
    return app
