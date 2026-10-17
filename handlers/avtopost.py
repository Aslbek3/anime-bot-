"""Kanalga avtopost (FEATURE_AVTOPOST).

Yangi serial yoki qism qo'shilganda POST_CHANNEL_ID kanaliga deeplink
bilan e'lon yuboradi. Routeri yo'q — `handlers/admin.py` chaqiradi.
"""
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

import ui
from config import POST_CHANNEL_ID

log = logging.getLogger(__name__)


async def _yubor(bot: Bot, matn: str, poster: str | None = None) -> None:
    if not POST_CHANNEL_ID:
        log.warning("avtopost yoqilgan, lekin POST_CHANNEL_ID ko'rsatilmagan")
        return
    try:
        if poster:
            await bot.send_photo(POST_CHANNEL_ID, poster, caption=matn)
        else:
            await bot.send_message(POST_CHANNEL_ID, matn, disable_web_page_preview=True)
    except TelegramAPIError as xato:
        log.warning("avtopost yuborilmadi: %s", xato)


async def yangi_serial(bot: Bot, serial) -> None:
    havola = await ui.havola(bot, f"serial_{serial['id']}")
    belgilar = " · ".join(b for b in (serial["janr"], serial["yil"] and str(serial["yil"])) if b)
    matn = f"🆕 <b>{ui.esc(serial['nom'])}</b>\n"
    if belgilar:
        matn += f"{ui.esc(belgilar)}\n"
    if serial["tavsif"]:
        matn += f"\n{ui.esc(serial['tavsif'])}\n"
    matn += f"\n▶️ Ko'rish: {havola}"
    await _yubor(bot, matn, serial["poster_file_id"])


async def yangi_qism(bot: Bot, serial, qism: int) -> None:
    havola = await ui.havola(bot, f"qism_{serial['id']}_{qism}")
    await _yubor(
        bot,
        f"🎬 <b>{ui.esc(serial['nom'])}</b> — {qism}-qism qo'shildi!\n\n▶️ Ko'rish: {havola}",
    )
