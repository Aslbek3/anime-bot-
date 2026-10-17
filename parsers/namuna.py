"""NAMUNA parser — ishlaydigan parser EMAS, faqat struktura ko'rsatkichi.

Aniq sayt uchun shu faylni nusxalab, `qidir()` va `yuklab_ol()` ichini
to'ldiring, so'ng `handlers/yuklash.py` dagi importni almashtiring:

    from parsers import namuna as parser   ->   from parsers import <sizniki> as parser

Hozircha ikkala funksiya ham NotImplementedError ko'taradi: navbat buni
xato deb yozadi va to'xtamay keyingi vazifaga o'tadi.
"""
from parsers.base import Topilma

NOMI = "namuna"


def qollab_quvvatlaydi(url: str) -> bool:
    """Shu parser berilgan havolani oladimi."""
    return False


def qidir(nom: str) -> list[Topilma]:
    # Haqiqiy parserda: saytga so'rov -> HTML/JSON dan natijalarni yig'ish
    raise NotImplementedError("namuna parser: qidir() yozilmagan")


def yuklab_ol(url: str, fayl_yoli: str) -> str:
    """Videoni yuklab, yakuniy fayl yo'lini qaytaradi (sinxron).

    Haqiqiy parserda odatda yt-dlp ishlatiladi:

        import yt_dlp
        sozlama = {"outtmpl": fayl_yoli, "format": "best[ext=mp4]/best", "quiet": True}
        with yt_dlp.YoutubeDL(sozlama) as ydl:
            malumot = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(malumot)
    """
    raise NotImplementedError("namuna parser: yuklab_ol() yozilmagan")
