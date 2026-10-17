"""Parser shartnomasi.

Har bir sayt uchun shu fayldagi ikkita funksiyani takrorlaydigan modul
yoziladi (masalan `parsers/kinoteatr.py`). Modul `handlers/yuklash.py`
dagi bitta importda almashtiriladi — boshqa joyga tegilmaydi.

Shartnoma:

    qidir(nom: str) -> list[Topilma]
        Sayt bo'yicha nom qidiradi. Topilmasa bo'sh ro'yxat.

    yuklab_ol(url: str, fayl_yoli: str) -> str
        Videoni `fayl_yoli` ga yuklaydi va yakuniy fayl yo'lini qaytaradi.
        Bu funksiya SINXRON — `asyncio.to_thread` ichida chaqiriladi,
        shuning uchun event loop ni bloklamaydi.
        Xatoda oddiy Exception ko'taradi: navbat uni ushlab, yozuvni
        holat='xato' qilib qo'yadi va keyingisiga o'tadi.
"""
from dataclasses import dataclass


@dataclass
class Topilma:
    """Qidiruv natijasi."""

    nom: str
    url: str
    yil: int | None = None
    poster_url: str | None = None


def qidir(nom: str) -> list[Topilma]:
    raise NotImplementedError("parser `qidir` funksiyasini yozmagan")


def yuklab_ol(url: str, fayl_yoli: str) -> str:
    raise NotImplementedError("parser `yuklab_ol` funksiyasini yozmagan")
