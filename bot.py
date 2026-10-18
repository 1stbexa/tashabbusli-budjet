"""
bot.py — ovoz-ishtirok boti (v3).

Oqim:
1. /start -> yo'riqnoma + "Ovoz berish" tugmasi
2. Ism -> telefon raqami (tekshiriladi) -> rasmiy havola
3. Foydalanuvchi o'zi ovoz beradi va skrinshot yuboradi -> yozuv saqlanadi
4. Takroriy nazorat: bir xil RAQAM yoki bir xil SKRINSHOT qabul qilinmaydi
   (bitta Telegram akkaunt bir nechta turli odamni ro'yxatga ola oladi)
5. Juda tez yuborilgan yoki forward qilingan rasm "tekshirish kerak" ga tushadi,
   admin ✅/❌ bosadi
6. Admin: /admin menyusi
"""

import asyncio
import logging
import os
import time
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo,
)
from dotenv import load_dotenv

import checks
import database as db

db.DB_PATH = os.getenv("DB_PATH", db.DB_PATH)  # Railway Volume uchun: /data/votes.db

# Ixtiyoriy qismlar: yo'q bo'lsa ham bot asosiy ishini davom ettiradi (/diag sabab ko'rsatadi)
IMPORT_ERRORS = {}
try:
    import sheets
except Exception as e:
    sheets = None
    IMPORT_ERRORS["sheets"] = repr(e)
try:
    import panel_core
    import webpanel
    from aiohttp import web
except Exception as e:
    panel_core = webpanel = web = None
    IMPORT_ERRORS["panel"] = repr(e)
try:
    import diag
except Exception as e:
    diag = None
    IMPORT_ERRORS["diag"] = repr(e)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PROJECT_LINK = os.getenv("PROJECT_LINK", "https://openbudget.uz")
PROJECT_NAME = os.getenv("PROJECT_NAME", "Bizning loyiha")
MAX_PER_USER = int(os.getenv("MAX_PER_USER", "10"))   # bitta Telegram akkauntdan nechta odam
MIN_SECONDS = int(os.getenv("MIN_SECONDS", "25"))     # havoladan keyin eng kamida necha soniya

if not BOT_TOKEN:
    raise SystemExit("XATO: BOT_TOKEN topilmadi. Railway Variables (yoki .env) ga BOT_TOKEN qo'shing.")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- Veb panel sozlamalari ---
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
PORT = int(os.getenv("PORT", "8080"))
_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
PUBLIC_URL = (os.getenv("PUBLIC_URL") or (f"https://{_domain}" if _domain else "")).rstrip("/")
PANEL_SECRET = panel_core.make_secret(BOT_TOKEN, ADMIN_PASSWORD) if (ADMIN_PASSWORD and panel_core) else None


class VotingFlow(StatesGroup):
    waiting_name = State()
    waiting_phone = State()
    waiting_screenshot = State()


class AdminFlow(StatesGroup):
    waiting_search = State()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def fmt_row(row) -> str:
    # id, telegram_id, full_name, phone, file_id, status, created_at, unique_id, flags
    flags = row[8] if len(row) > 8 and row[8] else ""
    text = f"#{row[0]} | {row[2]} | {row[3]} | {row[5]} | {str(row[6])[:16].replace('T', ' ')}"
    if flags:
        text += f"\nBelgilar: {flags}"
    return text


# ============ Oddiy foydalanuvchi ============
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    text = (
        f"Assalomu alaykum!\n\n"
        f"Bu bot \"{PROJECT_NAME}\" loyihasiga ovoz berish ishtirokini hisobga olish uchun.\n\n"
        f"Tartib:\n"
        f"1. Ism va telefon raqamni qoldirasiz\n"
        f"2. Sizga loyiha havolasi yuboriladi\n"
        f"3. O'sha yerda ovoz beriladi (har kim o'z raqamidan, o'zi)\n"
        f"4. Ovoz berilganini ko'rsatuvchi skrinshotni shu yerga yuborasiz\n\n"
        f"Ma'lumotlar faqat ishtirokni hisobga olish uchun ishlatiladi."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗳 Ovoz berish", callback_data="start_voting")]
    ])
    await message.answer(text, reply_markup=kb)


# ============ Admin (state handlerlardan OLDIN turishi kerak) ============
def admin_menu_kb() -> InlineKeyboardMarkup:
    review_n = db.count_by_status("review")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="adm_stats"),
         InlineKeyboardButton(text="🕘 Oxirgi 10 ta", callback_data="adm_recent")],
        [InlineKeyboardButton(text=f"⚠️ Tekshirish kerak ({review_n})", callback_data="adm_review")],
        [InlineKeyboardButton(text="🔍 Raqam bo'yicha qidirish", callback_data="adm_search")],
        [InlineKeyboardButton(text="📥 Excel yuklab olish", callback_data="adm_export")],
        [InlineKeyboardButton(text="🖥 Veb panel", callback_data="adm_panel")],
        [InlineKeyboardButton(text="🗑 Test ma'lumotlarini tozalash", callback_data="adm_clear")],
    ])


def stats_text() -> str:
    return (
        f"📊 Jami (rad etilmagan): {db.count_total()}\n"
        f"Bugun: {db.count_today()}\n"
        f"⚠️ Tekshirishda: {db.count_by_status('review')}\n"
        f"❌ Rad etilgan: {db.count_by_status('rejected')}"
    )


@dp.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("Admin menyu:", reply_markup=admin_menu_kb())


@dp.message(Command("royxat"))
async def cmd_royxat(message: Message):
    if is_admin(message.from_user.id):
        await message.answer(stats_text())


@dp.message(Command("export"))
async def cmd_export(message: Message):
    if is_admin(message.from_user.id):
        await send_excel(message)


@dp.message(Command("diag"))
async def cmd_diag(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) > 1 and parts[1].strip() == "sheets":
        if not sheets:
            await message.answer(f"❌ sheets.py yuklanmagan: {IMPORT_ERRORS.get('sheets')}")
            return
        ok, info = await asyncio.to_thread(
            sheets.send_row, 0, 0, "DIAG TEST", "+998000000000", "test", datetime.now().isoformat(), "diag"
        )
        await message.answer(
            "✅ Sheet'ga 'DIAG TEST' qatori yozildi. Jadvalni tekshirib, qatorni o'chirib qo'ying."
            if ok else f"❌ Sheet'ga yozilmadi: {info}"
        )
        return
    if not diag:
        await message.answer(f"❌ diag.py GitHub'da yo'q yoki xato: {IMPORT_ERRORS.get('diag')}")
        return
    await message.answer(await asyncio.to_thread(diag.build_report, PUBLIC_URL, bool(PANEL_SECRET), IMPORT_ERRORS))


@dp.message(Command("panel"))
async def cmd_panel(message: Message):
    if is_admin(message.from_user.id):
        await send_panel_link(message)


async def send_panel_link(message: Message):
    if not panel_core or not webpanel:
        await message.answer("Veb panel fayllari (panel_core.py, webpanel.py) GitHub'da yo'q. /diag ni yuboring.")
        return
    if not PANEL_SECRET:
        await message.answer("Veb panel yoqilmagan: Railway Variables'ga ADMIN_PASSWORD qo'shing.")
        return
    if not PUBLIC_URL:
        await message.answer("Veb panel manzili yo'q: Railway'da Settings -> Networking -> Generate Domain ni bosing.")
        return
    url = f"{PUBLIC_URL}/auth?t={panel_core.sign(PANEL_SECRET, 'magic', 600)}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Telegram ichida ochish", web_app=WebAppInfo(url=url))],
        [InlineKeyboardButton(text="🌐 Brauzerda ochish", url=url)],
    ])
    await message.answer("Admin panel (havola 10 daqiqa amal qiladi):", reply_markup=kb)


async def send_excel(message: Message):
    from export_excel import make_excel_file
    await message.answer_document(document=FSInputFile(make_excel_file()))


def review_kb(vote_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"rv_ok_{vote_id}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"rv_no_{vote_id}"),
    ]])


async def send_rows(chat_id: int, rows, with_review_buttons=False):
    if not rows:
        await bot.send_message(chat_id, "Hech narsa topilmadi.")
        return
    for row in rows:
        kb = review_kb(row[0]) if with_review_buttons else None
        try:
            await bot.send_photo(chat_id, row[4], caption=fmt_row(row), reply_markup=kb)
        except Exception:
            await bot.send_message(chat_id, fmt_row(row), reply_markup=kb)


@dp.callback_query(F.data.startswith("adm_"))
async def admin_callbacks(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    action = callback.data
    chat_id = callback.message.chat.id

    if action == "adm_stats":
        await callback.message.answer(stats_text())
    elif action == "adm_recent":
        await send_rows(chat_id, db.get_recent(10))
    elif action == "adm_review":
        await send_rows(chat_id, db.get_by_status("review", 10), with_review_buttons=True)
    elif action == "adm_search":
        await state.set_state(AdminFlow.waiting_search)
        await callback.message.answer("Qidirish uchun raqamning bir qismini yozing (masalan 901234567):")
    elif action == "adm_export":
        await send_excel(callback.message)
    elif action == "adm_panel":
        await send_panel_link(callback.message)
    elif action == "adm_clear":
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Ha, hammasini o'chir", callback_data="adm_clear_yes"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="adm_clear_no"),
        ]])
        await callback.message.answer(
            f"Diqqat! Bazadagi {len(db.get_all(limit=1000000))} ta yozuv butunlay o'chiriladi. Davom etamizmi?",
            reply_markup=kb,
        )
    elif action == "adm_clear_yes":
        await callback.message.answer(f"🗑 {db.clear_all()} ta yozuv o'chirildi.")
    elif action == "adm_clear_no":
        await callback.message.answer("Bekor qilindi.")
    await callback.answer()


@dp.callback_query(F.data.startswith("rv_"))
async def review_callbacks(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    _, decision, vote_id = callback.data.split("_")
    vote_id = int(vote_id)
    new_status = "verified" if decision == "ok" else "rejected"
    db.set_status(vote_id, new_status)
    mark = "✅ TASDIQLANDI" if decision == "ok" else "❌ RAD ETILDI"
    try:
        old = callback.message.caption or callback.message.text or ""
        if callback.message.caption is not None:
            await callback.message.edit_caption(caption=f"{old}\n\n{mark}")
        else:
            await callback.message.edit_text(f"{old}\n\n{mark}")
    except Exception:
        pass
    await callback.answer("Saqlandi")


@dp.message(AdminFlow.waiting_search)
async def admin_search(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await send_rows(message.chat.id, db.find_by_phone(message.text or ""))


# ============ Ovoz berish oqimi ============
@dp.callback_query(F.data == "start_voting")
async def start_voting(callback: CallbackQuery, state: FSMContext):
    if db.count_for_user(callback.from_user.id) >= MAX_PER_USER:
        await callback.message.answer(
            f"Bitta akkauntdan eng ko'pi bilan {MAX_PER_USER} ta odamni ro'yxatga olish mumkin."
        )
        await callback.answer()
        return
    await callback.message.answer("Ro'yxatga olinadigan odamning ismi va familiyasini yozing:")
    await state.set_state(VotingFlow.waiting_name)
    await callback.answer()


@dp.message(VotingFlow.waiting_name, F.text)
async def get_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Iltimos, ismni to'liq yozing.")
        return
    await state.update_data(full_name=name)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Raqamni yuborish", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True,
    )
    await message.answer(
        "Shu odamning telefon raqamini yuboring (o'zingiznikini tugma bilan, boshqaniki bo'lsa "
        "+998901234567 ko'rinishida yozing):",
        reply_markup=kb,
    )
    await state.set_state(VotingFlow.waiting_phone)


@dp.message(VotingFlow.waiting_phone)
async def get_phone(message: Message, state: FSMContext):
    via_contact = message.contact is not None
    raw = message.contact.phone_number if via_contact else message.text
    phone = checks.normalize_phone(raw)
    if not phone:
        await message.answer("Raqam noto'g'ri. Iltimos, +998901234567 ko'rinishida yozing yoki tugmani bosing.")
        return
    if db.exists_for_phone(phone):
        await state.clear()
        await message.answer("Bu raqam allaqachon ro'yxatda bor. Rahmat! ✅", reply_markup=ReplyKeyboardRemove())
        return

    source = checks.phone_source(
        message.contact.user_id if via_contact else None, message.from_user.id, via_contact
    )
    await state.update_data(phone=phone, phone_source=source, link_sent_at=time.time())
    await message.answer(
        f"Rahmat! Endi quyidagi havola orqali ovoz bering (shu raqam egasining o'zi):\n\n{PROJECT_LINK}\n\n"
        f"Ovoz berib bo'lgach, tasdiq sifatida sahifaning skrinshotini shu yerga yuboring.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(VotingFlow.waiting_screenshot)


@dp.message(VotingFlow.waiting_screenshot, F.photo)
async def get_screenshot(message: Message, state: FSMContext):
    data = await state.get_data()
    full_name, phone = data.get("full_name"), data.get("phone")
    photo = message.photo[-1]

    # 1) Xuddi shu rasm avval yuborilganmi? (qayta ishlatishdan himoya)
    if db.exists_screenshot(photo.file_unique_id):
        await message.answer(
            "Bu skrinshot avval yuborilgan. Har bir odam uchun o'zining yangi skrinshotini yuboring."
        )
        return  # holat o'zgarmaydi — boshqa rasm yuborish mumkin

    # 2) Raqam shu orada ro'yxatga olinganmi?
    if db.exists_for_phone(phone):
        await state.clear()
        await message.answer("Bu raqam allaqachon ro'yxatda bor. Rahmat! ✅")
        return

    # 3) Shubhali belgilar
    elapsed = time.time() - data["link_sent_at"] if data.get("link_sent_at") else None
    flags, review = checks.compute_flags(
        data.get("phone_source", checks.SRC_MANUAL), elapsed,
        forwarded=message.forward_origin is not None, min_seconds=MIN_SECONDS,
    )
    status = "review" if review else "submitted"

    vote_id = db.add_vote(
        message.from_user.id, full_name, phone, photo.file_id,
        status=status, screenshot_unique_id=photo.file_unique_id, flags=flags,
    )
    await state.clear()

    if review:
        await message.answer("Rahmat! Skrinshotingiz qabul qilindi, qo'shimcha tekshiruvdan o'tadi. ⏳")
    else:
        await message.answer("Rahmat! Skrinshotingiz qabul qilindi va ro'yxatga qo'shildi. ✅")

    row = db.get_vote(vote_id)
    if sheets:
        asyncio.create_task(asyncio.to_thread(
            sheets.append_row, vote_id, message.from_user.id, full_name, phone, status, row[6], flags
        ))

    try:
        if review:
            await bot.send_photo(
                ADMIN_ID, photo.file_id,
                caption=f"⚠️ Tekshirish kerak:\n{fmt_row(row)}", reply_markup=review_kb(vote_id),
            )
        else:
            await bot.send_photo(ADMIN_ID, photo.file_id, caption=f"Yangi ishtirokchi:\n{fmt_row(row)}")
    except Exception as e:
        logging.warning("Adminga yuborib bo'lmadi: %s", e)


@dp.message(VotingFlow.waiting_screenshot)
async def wrong_content(message: Message):
    await message.answer("Iltimos, skrinshotni rasm (surat) ko'rinishida yuboring.")


async def main():
    os.makedirs(os.path.dirname(os.path.abspath(db.DB_PATH)), exist_ok=True)
    db.init_db()
    if PANEL_SECRET and webpanel and web:
        try:
            runner = web.AppRunner(webpanel.build_app(bot, PANEL_SECRET, ADMIN_PASSWORD))
            await runner.setup()
            await web.TCPSite(runner, "0.0.0.0", PORT).start()
            logging.info("Veb panel %s portda ishga tushdi", PORT)
        except Exception as e:
            IMPORT_ERRORS["panel_start"] = repr(e)
            logging.error("Veb panel ishga tushmadi: %s", e)
    try:
        persistent = os.path.ismount(os.path.dirname(os.path.abspath(db.DB_PATH)))
        issues = len(IMPORT_ERRORS)
        await bot.send_message(
            ADMIN_ID,
            f"✅ Bot ishga tushdi. Yozuvlar: {len(db.get_all(limit=1000000))}. "
            f"Baza: {'doimiy' if persistent else 'VAQTINCHALIK'}. "
            f"Muammolar: {issues}. Batafsil: /diag",
        )
    except Exception as e:
        logging.warning("Ishga tushish xabari yuborilmadi: %s", e)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
