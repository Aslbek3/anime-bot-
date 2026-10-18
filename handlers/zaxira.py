"""Bazani avtomatik zaxiralash (FEATURE_ZAXIRA).

Har ZAXIRA_SOAT soatda bazadan izchil nusxa oladi (SQLite backup API —
bot ishlab turganda ham xavfsiz) va eng so'nggi ZAXIRA_SAQLASH tasini
qoldirib, eskilarini o'chiradi.

Routerda handler yo'q: faqat startup ilgagi uchun kerak.
"""
import asyncio
import logging
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Router
from aiogram.types import FSInputFile

import db
from config import ADMIN_ID, ZAXIRA_ADMINGA, ZAXIRA_DIR, ZAXIRA_SAQLASH, ZAXIRA_SOAT

router = Router(name="zaxira")
log = logging.getLogger(__name__)

_vazifa: asyncio.Task | None = None


async def bir_marta(bot: Bot | None = None) -> Path:
    papka = Path(ZAXIRA_DIR)
    papka.mkdir(parents=True, exist_ok=True)
    nishon = papka / f"qogoz-{datetime.now():%Y%m%d-%H%M}.db"
    await db.zaxira_ol(str(nishon))
    eskilarini_ochir(papka)
    log.info("zaxira olindi: %s", nishon.name)
    if bot is not None and ZAXIRA_ADMINGA:
        try:
            await bot.send_document(
                ADMIN_ID, FSInputFile(nishon), caption=f"🗄 Zaxira: {nishon.name}"
            )
        except Exception as xato:
            log.warning("zaxira adminga yuborilmadi: %s", xato)
    return nishon


def eskilarini_ochir(papka: Path) -> None:
    nusxalar = sorted(papka.glob("qogoz-*.db"), key=lambda f: f.stat().st_mtime, reverse=True)
    for eski in nusxalar[ZAXIRA_SAQLASH:]:
        eski.unlink(missing_ok=True)


async def _halqa(bot: Bot) -> None:
    while True:
        try:
            await bir_marta(bot)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("zaxira olishda xato")
        await asyncio.sleep(ZAXIRA_SOAT * 3600)


@router.startup()
async def ishga_tushir(bot: Bot, **_) -> None:
    global _vazifa
    _vazifa = asyncio.create_task(_halqa(bot))
    log.info("zaxira moduli yoqildi: har %s soatda", ZAXIRA_SOAT)


@router.shutdown()
async def to_xtatish(**_) -> None:
    if _vazifa is not None:
        _vazifa.cancel()
