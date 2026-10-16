"""
export_excel.py — bazadagi ma'lumotlarni Excel faylga aylantiradi.
"""

from openpyxl import Workbook
import database as db


def make_excel_file(path: str = "royxat.xlsx") -> str:
    rows = db.get_all()
    wb = Workbook()
    ws = wb.active
    ws.title = "Ro'yxat"
    ws.append(["ID", "Telegram ID", "Ism", "Raqam", "Holati", "Vaqti", "Belgilar"])
    for row in rows:
        # id, telegram_id, full_name, phone, file_id, status, created_at, unique_id, flags
        flags = row[8] if len(row) > 8 else ""
        ws.append([row[0], row[1], row[2], row[3], row[5], row[6], flags or ""])
    wb.save(path)
    return path
