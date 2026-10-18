"""Inline rejim (FEATURE_INLINE).

Boshqa chatda `@botingiz spiderman` yozilsa, natijalar ro'yxati chiqadi.
Tanlangan natija deeplink bilan xabar yuboradi — do'sti bosganda bot
ochiladi va serial kartochkasi ko'rinadi.

Video to'g'ridan-to'g'ri yuborilmaydi: qismlar yopiq arxiv kanalda yotadi
va ularning `file_id` si bazada saqlanmaydi (ataylab — CLAUDE.md ga qarang).
"""
import logging

from aiogram import Bot, Router
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

import db
import ui

router = Router(name="inline")
log = logging.getLogger(__name__)

LIMIT = 20
KESH = 60


@router.inline_query()
async def qidir(so_rov: InlineQuery, bot: Bot):
    soz = so_rov.query.strip()
    seriallar = await db.search_page(soz, 0, LIMIT) if len(soz) >= 2 else await db.list_serials(0, LIMIT)

    natijalar = []
    for serial in seriallar:
        havola = await ui.havola(bot, f"serial_{serial['id']}")
        belgilar = " · ".join(
            b for b in (serial["janr"], serial["yil"] and str(serial["yil"])) if b
        )
        natijalar.append(
            InlineQueryResultArticle(
                id=str(serial["id"]),
                title=serial["nom"],
                description=belgilar or (serial["tavsif"] or "")[:60],
                input_message_content=InputTextMessageContent(
                    message_text=f"🎬 <b>{ui.esc(serial['nom'])}</b>\n{havola}",
                    parse_mode="HTML",
                ),
            )
        )

    await so_rov.answer(
        natijalar,
        cache_time=KESH,
        is_personal=False,
        switch_pm_text="🔎 Botda qidirish" if not natijalar else None,
        switch_pm_parameter="inline" if not natijalar else None,
    )
