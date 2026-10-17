"""
webpanel.py — brauzerda (va Telegram ichida) ochiladigan oddiy admin panel.
Bot bilan bir jarayonda, aiohttp orqali ishlaydi.
"""

import io
import time
from urllib.parse import urlencode

from aiohttp import web

import database as db
import panel_core as core

SESSION_TTL = 7 * 24 * 3600
_failed = {}  # ip -> [vaqtlar]


def build_app(bot, secret: bytes, password: str) -> web.Application:
    @web.middleware
    async def auth_mw(request, handler):
        if request.path in ("/login", "/auth", "/health"):
            return await handler(request)
        if not core.verify(secret, "session", request.cookies.get("sid", "")):
            raise web.HTTPFound("/login")
        return await handler(request)

    def start_session(resp: web.Response):
        token = core.sign(secret, "session", SESSION_TTL)
        resp.set_cookie("sid", token, max_age=SESSION_TTL, httponly=True, secure=True, samesite="Lax")
        return resp

    async def health(request):
        return web.Response(text="ok")

    async def login_get(request):
        return web.Response(text=core.login_page(), content_type="text/html")

    async def login_post(request):
        ip = request.headers.get("X-Forwarded-For", request.remote or "?").split(",")[0].strip()
        now = time.time()
        recent = [t for t in _failed.get(ip, []) if now - t < 600]
        if len(recent) >= 5:
            return web.Response(text=core.login_page("Juda ko'p urinish. 10 daqiqadan keyin qayta urinib ko'ring."),
                                content_type="text/html", status=429)
        form = await request.post()
        import hmac
        if hmac.compare_digest(str(form.get("password", "")), password):
            _failed.pop(ip, None)
            return start_session(web.HTTPFound("/"))
        recent.append(now)
        _failed[ip] = recent
        return web.Response(text=core.login_page("Parol noto'g'ri."), content_type="text/html", status=401)

    async def magic(request):
        if core.verify(secret, "magic", request.query.get("t", "")):
            return start_session(web.HTTPFound("/"))
        return web.Response(text=core.login_page("Havola eskirgan. Botda /panel ni qayta yuboring yoki parol bilan kiring."),
                            content_type="text/html", status=401)

    async def logout(request):
        resp = web.HTTPFound("/login")
        resp.del_cookie("sid")
        return resp

    async def dashboard(request):
        q = request.query.get("q", "").strip()
        status = request.query.get("status", "")
        if status not in core.STATUS_LABELS:
            status = ""
        rows = db.search(q, status, 300)
        stats = {
            "Jami (rad etilmagan)": db.count_total(),
            "Bugun": db.count_today(),
            "Tekshirishda": db.count_by_status("review"),
            "Rad etilgan": db.count_by_status("rejected"),
        }
        qs = urlencode({k: v for k, v in (("q", q), ("status", status)) if v})
        return web.Response(text=core.dashboard_page(stats, rows, q, status, qs), content_type="text/html")

    async def set_status(request):
        form = await request.post()
        status = str(form.get("status", ""))
        try:
            vote_id = int(form.get("vote_id", ""))
        except ValueError:
            raise web.HTTPBadRequest()
        if status in ("verified", "rejected", "submitted") and db.get_vote(vote_id):
            db.set_status(vote_id, status)
        nxt = str(form.get("next", ""))
        raise web.HTTPFound("/" + ("?" + nxt if nxt else ""))

    async def photo(request):
        row = db.get_vote(int(request.match_info["vote_id"]))
        if not row or not row[4]:
            raise web.HTTPNotFound()
        try:
            f = await bot.get_file(row[4])
            buf = io.BytesIO()
            await bot.download_file(f.file_path, buf)
        except Exception:
            raise web.HTTPNotFound(text="Rasm topilmadi")
        return web.Response(body=buf.getvalue(), content_type="image/jpeg",
                            headers={"Cache-Control": "private, max-age=3600"})

    async def export(request):
        from export_excel import make_excel_file
        path = make_excel_file()
        with open(path, "rb") as fh:
            data = fh.read()
        return web.Response(
            body=data,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=royxat.xlsx"},
        )

    app = web.Application(middlewares=[auth_mw])
    app.add_routes([
        web.get("/health", health),
        web.get("/login", login_get), web.post("/login", login_post),
        web.get("/auth", magic), web.get("/logout", logout),
        web.get("/", dashboard), web.post("/status", set_status),
        web.get(r"/photo/{vote_id:\d+}", photo), web.get("/export.xlsx", export),
    ])
    return app
