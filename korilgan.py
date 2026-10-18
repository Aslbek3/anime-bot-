"""Ko'rilgan qismga ✓ belgisi (FEATURE_KORILGAN).

Yangi jadval kerak emas: `progress.oxirgi_qism` dan foydalanamiz —
serialda N-qism ko'rilgan bo'lsa, undan oldingilari ham ko'rilgan deb
hisoblanadi. Agar kelajakda aniq ro'yxat kerak bo'lsa, shu modulga
alohida jadval qo'shiladi, qolgan kod o'zgarmaydi.
"""
import db

BELGI = "✓ "


async def chegara(user_id: int, serial_id: int) -> int:
    """Shu foydalanuvchi uchun oxirgi ko'rilgan qism raqami (yo'q bo'lsa 0)."""
    yozuv = await db.progress_bitta(user_id, serial_id)
    return yozuv["oxirgi_qism"] if yozuv else 0


def belgilash(qism_raqami: int, oxirgi: int) -> str:
    """Qism tugmasi matni: ko'rilgan bo'lsa ✓ bilan."""
    return BELGI if qism_raqami <= oxirgi else ""
