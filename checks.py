"""
checks.py — telefon raqamini tekshirish va "shubhali" belgilarni aniqlash.
(Telegram'ga bog'liq emas, shuning uchun alohida sinab ko'rish mumkin.)
"""

import re

SRC_OWN = "o'z raqami (Telegram tasdiqlagan)"
SRC_OTHER = "boshqa kontakt"
SRC_MANUAL = "qo'lda kiritilgan"
FLAG_FAST = "juda tez yuborilgan"
FLAG_FORWARD = "forward qilingan rasm"


def normalize_phone(raw):
    """+998XXXXXXXXX ko'rinishiga keltiradi, noto'g'ri bo'lsa None qaytaradi."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 9:
        digits = "998" + digits
    if len(digits) == 12 and digits.startswith("998"):
        return "+" + digits
    return None


def phone_source(contact_user_id, sender_id, via_contact: bool) -> str:
    """Raqam qanday kelgani: Telegram kontakt tugmasi (o'ziniki yoki boshqaniki) yoki qo'lda."""
    if not via_contact:
        return SRC_MANUAL
    if contact_user_id is not None and contact_user_id == sender_id:
        return SRC_OWN
    return SRC_OTHER


def compute_flags(source: str, elapsed, forwarded: bool, min_seconds: int):
    """
    Belgilar matnini va qo'lda tekshirish kerakmi-yo'qligini qaytaradi.
    Faqat "juda tez" va "forward" holatlari tekshiruvga yuboriladi;
    raqam manbai shunchaki ma'lumot uchun yoziladi.
    """
    flags = [source]
    review = False
    if elapsed is not None and elapsed < min_seconds:
        flags.append(FLAG_FAST)
        review = True
    if forwarded:
        flags.append(FLAG_FORWARD)
        review = True
    return "; ".join(flags), review
