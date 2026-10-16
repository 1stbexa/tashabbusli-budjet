"""
bot.py — ovoz-ishtirok boti (v2).

Oqim:
1. /start -> yo'riqnoma + "Ovoz berish" tugmasi
2. Ism -> telefon raqami (tekshiriladi) -> rasmiy havola
3. Foydalanuvchi o'zi ovoz beradi va skrinshot yuboradi -> yozuv saqlanadi
4. Takroriy yuborish (bir xil Telegram ID yoki raqam) qabul qilinmaydi
5. Admin: /admin menyusi (statistika, oxirgi ovozlar, qidiruv, Excel, tozalash)
"""

import asyncio
import logging
import os
import re

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove,
)
from dotenv import load_dotenv

import database as db
import sheets

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PROJECT_LINK = os.getenv("PROJECT_LINK", "https://openbudget.uz")
PROJECT_NAME = os.getenv("PROJECT_NAME", "Bizning loyiha")

if not BOT_TOKEN:
    raise SystemExit("XATO: BOT_TOKEN topilmadi. Railway Variables (yoki .env) ga BOT_TOKEN qo'shing.")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class VotingFlow(StatesGroup):
    waiting_name = State()
    waiting_phone = State()
    waiting_screenshot = State()


class AdminFlow(StatesGroup):
    waiting_search = State()


def normalize_phone(raw):
    """+998XXXXXXXXX ko'rinishiga keltiradi, noto'g'ri bo'lsa None qaytaradi."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 9:
        digits = "998" + digits
    if len(digits) == 12 and digits.startswith("998"):
        return "+" + digits
    return None


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def fmt_row(row) -> str:
    # row: id, telegram_id, full_name, phone, screenshot_file_id, status, created_at
    return f"#{row[0]} | {row[2]} | {row[3]} | {row[5]} | {str(row[6])[:16].replace('T', ' ')}"


# ============ Oddiy foydalanuvchi buyruqlari ============
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    text = (
        f"Assalomu alaykum!\n\n"
        f"Bu bot \"{PROJECT_NAME}\" loyihasiga ovoz berish ishtirokini hisobga olish uchun.\n\n"
        f"Tartib:\n"
        f"1. Ismingiz va telefon raqamingizni qoldirasiz\n"
        f"2. Sizga loyiha havolasi yuboriladi\n"
        f"3. O'sha yerda o'zingiz shaxsan ovoz berasiz\n"
        f"4. Ovoz berganingizni ko'rsatuvchi skrinshotni shu yerga yuborasiz\n\n"
        f"Ma'lumotlaringiz faqat ishtirokni hisobga olish uchun ishlatiladi."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗳 Ovoz berish", callback_data="start_voting")]
    ])
    await message.answer(text, reply_markup=kb)


# ============ Admin buyruqlari (state handlerlardan OLDIN turishi kerak) ============
def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="adm_stats"),
         InlineKeyboardButton(text="🕘 Oxirgi 10 ta", callback_data="adm_recent")],
        [InlineKeyboardButton(text="🔍 Raqam bo'yicha qidirish", callback_data="adm_search")],
        [InlineKeyboardButton(text="📥 Excel yuklab olish", callback_data="adm_export")],
        [InlineKeyboardButton(text="🗑 Test ma'lumotlarini tozalash", callback_data="adm_clear")],
    ])


@dp.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("Admin menyu:", reply_markup=admin_menu_kb())


@dp.message(Command("royxat"))
async def cmd_royxat(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(f"📊 Jami: {db.count_total()}\nBugun: {db.count_today()}")


@dp.message(Command("export"))
async def cmd_export(message: Message):
    if not is_admin(message.from_user.id):
        return
    await send_excel(message)


async def send_excel(message: Message):
    from export_excel import make_excel_file
    path = make_excel_file()
    await message.answer_document(document=FSInputFile(path))


async def send_rows(chat_id: int, rows):
    if not rows:
        await bot.send_message(chat_id, "Hech narsa topilmadi.")
        return
    for row in rows:
        try:
            await bot.send_photo(chat_id, row[4], caption=fmt_row(row))
        except Exception:
            await bot.send_message(chat_id, fmt_row(row))


@dp.callback_query(F.data.startswith("adm_"))
async def admin_callbacks(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    action = callback.data
    chat_id = callback.message.chat.id

    if action == "adm_stats":
        await callback.message.answer(f"📊 Jami: {db.count_total()}\nBugun: {db.count_today()}")
    elif action == "adm_recent":
        await send_rows(chat_id, db.get_recent(10))
    elif action == "adm_search":
        await state.set_state(AdminFlow.waiting_search)
        await callback.message.answer("Qidirish uchun raqamning bir qismini yozing (masalan 901234567):")
    elif action == "adm_export":
        await send_excel(callback.message)
    elif action == "adm_clear":
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Ha, hammasini o'chir", callback_data="adm_clear_yes"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="adm_clear_no"),
        ]])
        await callback.message.answer(
            f"Diqqat! Bazadagi {db.count_total()} ta yozuv butunlay o'chiriladi. Davom etamizmi?",
            reply_markup=kb,
        )
    elif action == "adm_clear_yes":
        n = db.clear_all()
        await callback.message.answer(f"🗑 {n} ta yozuv o'chirildi.")
    elif action == "adm_clear_no":
        await callback.message.answer("Bekor qilindi.")
    await callback.answer()


@dp.message(AdminFlow.waiting_search)
async def admin_search(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await send_rows(message.chat.id, db.find_by_phone(message.text or ""))


# ============ Ovoz berish oqimi ============
@dp.callback_query(F.data == "start_voting")
async def start_voting(callback: CallbackQuery, state: FSMContext):
    if db.exists_for_user(callback.from_user.id):
        await callback.message.answer("Siz allaqachon ishtirok etgansiz. Rahmat! ✅")
        await callback.answer()
        return
    await callback.message.answer("Ismingiz va familiyangizni yozing:")
    await state.set_state(VotingFlow.waiting_name)
    await callback.answer()


@dp.message(VotingFlow.waiting_name, F.text)
async def get_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Iltimos, ismingizni to'liq yozing.")
        return
    await state.update_data(full_name=name)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Raqamni yuborish", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True,
    )
    await message.answer(
        "Telefon raqamingizni yuboring (tugmani bosing yoki +998901234567 ko'rinishida yozing):",
        reply_markup=kb,
    )
    await state.set_state(VotingFlow.waiting_phone)


@dp.message(VotingFlow.waiting_phone)
async def get_phone(message: Message, state: FSMContext):
    raw = message.contact.phone_number if message.contact else message.text
    phone = normalize_phone(raw)
    if not phone:
        await message.answer("Raqam noto'g'ri. Iltimos, +998901234567 ko'rinishida yozing yoki tugmani bosing.")
        return
    if db.exists_for_phone(phone):
        await state.clear()
        await message.answer("Bu raqam allaqachon ro'yxatda bor. Rahmat! ✅", reply_markup=ReplyKeyboardRemove())
        return
    await state.update_data(phone=phone)
    await message.answer(
        f"Rahmat! Endi quyidagi havola orqali o'zingiz ovoz bering:\n\n{PROJECT_LINK}\n\n"
        f"Ovoz berib bo'lgach, tasdiq sifatida sahifaning skrinshotini shu yerga yuboring.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(VotingFlow.waiting_screenshot)


@dp.message(VotingFlow.waiting_screenshot, F.photo)
async def get_screenshot(message: Message, state: FSMContext):
    data = await state.get_data()
    full_name, phone = data.get("full_name"), data.get("phone")
    file_id = message.photo[-1].file_id

    if db.exists_for_user(message.from_user.id) or db.exists_for_phone(phone):
        await state.clear()
        await message.answer("Siz allaqachon ishtirok etgansiz. Rahmat! ✅")
        return

    vote_id = db.add_vote(message.from_user.id, full_name, phone, file_id)
    await state.clear()
    await message.answer("Rahmat! Skrinshotingiz qabul qilindi va ro'yxatga qo'shildi. ✅")

    row = db.get_vote(vote_id)
    # Google Sheet'ga yuborish (alohida oqimda, bot to'xtab qolmasligi uchun)
    asyncio.create_task(asyncio.to_thread(
        sheets.append_row, vote_id, message.from_user.id, full_name, phone, "submitted", row[6]
    ))

    try:
        await bot.send_photo(ADMIN_ID, file_id, caption=f"Yangi ishtirokchi:\n{fmt_row(row)}")
    except Exception as e:
        logging.warning("Adminga yuborib bo'lmadi: %s", e)


@dp.message(VotingFlow.waiting_screenshot)
async def wrong_content(message: Message):
    await message.answer("Iltimos, skrinshotni rasm (surat) ko'rinishida yuboring.")


async def main():
    db.init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
