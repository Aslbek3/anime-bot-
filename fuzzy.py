"""Xatoga chidamli qidiruv (FEATURE_FUZZY).

LIKE qidiruv hech narsa topmaganda ishga tushadi: nomlarni normallashtirib
(katta-kichik harf, apostrof, bo'shliq, tinish belgilari tashlanadi) va
o'xshashlik koeffitsiyenti bo'yicha solishtirib, eng yaqinlarini qaytaradi.
"spaydermen" -> "Spider-Man" shu yo'l bilan topiladi.
"""
import re
from difflib import SequenceMatcher

import db
from config import FUZZY_CHEGARA

# Uzbek lotinidagi ko'p uchraydigan yozilish farqlari
ALMASHTIRISH = (
    ("ʼ", ""), ("'", ""), ("`", ""), ("’", ""),
    ("sh", "s"), ("ch", "c"), ("ng", "n"),
    ("x", "h"), ("q", "k"), ("w", "v"), ("y", "i"), ("j", "z"),
)


def normalla(matn: str) -> str:
    matn = (matn or "").lower()
    for eski, yangi in ALMASHTIRISH:
        matn = matn.replace(eski, yangi)
    return re.sub(r"[^a-z0-9а-я]", "", matn)


def oxshashlik(a: str, b: str) -> float:
    a, b = normalla(a), normalla(b)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


async def yaqinlari(soz: str, limit: int = 8):
    """Eng o'xshash seriallar (chegaradan yuqorilari), o'xshashligi bo'yicha."""
    natija = []
    for serial_id, nom in await db.serial_nomlari():
        ball = oxshashlik(soz, nom)
        if ball >= FUZZY_CHEGARA:
            natija.append((ball, serial_id))
    natija.sort(reverse=True)
    return [await db.get_serial(sid) for _, sid in natija[:limit]]
