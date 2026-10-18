"""
export_excel.py — bazadagi BARCHA yozuvlarni Excel faylga aylantiradi.
(Oldingi versiya database.get_all() ni limitsiz chaqirib, faqat 30 ta yozuvni olardi.)
"""

from openpyxl import Workbook
import database as db


def make_excel_file(path: str = "royxat.xlsx") -> str:
    rows = db.get_all(limit=1000000)
    wb = Workbook()
    ws = wb.active
    ws.title = "Ro'yxat"
    ws.append(["ID", "Telegram ID", "Ism", "Raqam", "Holati", "Vaqti (UTC)", "Belgilar"])
    for row in rows:
        # id, telegram_id, full_name, phone, file_id, status, created_at, unique_id, flags
        flags = row[8] if len(row) > 8 else ""
        ws.append([row[0], row[1], row[2], row[3], row[5], row[6], flags or ""])
    wb.save(path)
    return path
