"""Yangi qism bildirishnomasi (FEATURE_BILDIRISHNOMA).

Admin qism qo'shganda shu serialni ko'rayotganlarga (progress yozuvi
borlarga) xabar yuboradi. Routeri yo'q — `handlers/admin.py` chaqiradi.
"""
import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramRetryAfter

import db
import ui
from config import BROADCAST_CHUNK, BROADCAST_PAUSE

log = logging.getLogger(__name__)


async def yangi_qism(bot: Bot, serial, qism: int) -> int:
    """Tomoshabinlarga xabar beradi, yuborilganlar sonini qaytaradi."""
    tomoshabinlar = await db.serial_tomoshabinlari(serial["id"])
    if not tomoshabinlar:
        return 0

    havola = await ui.havola(bot, f"qism_{serial['id']}_{qism}")
    matn = (
        f"🆕 <b>{ui.esc(serial['nom'])}</b> — {qism}-qism chiqdi!\n\n"
        f"Ko'rish: {havola}"
    )

    yuborildi = 0
    for i in range(0, len(tomoshabinlar), BROADCAST_CHUNK):
        for user_id in tomoshabinlar[i : i + BROADCAST_CHUNK]:
            try:
                await bot.send_message(user_id, matn, disable_web_page_preview=True)
                yuborildi += 1
            except TelegramForbiddenError:
                await db.faol_belgila(user_id, False)
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
            except TelegramAPIError as xato:
                log.info("bildirishnoma yetmadi (%s): %s", user_id, xato)
            await asyncio.sleep(0.05)
        await asyncio.sleep(BROADCAST_PAUSE)

    log.info("yangi qism bildirishnomasi: %s ta", yuborildi)
    return yuborildi
