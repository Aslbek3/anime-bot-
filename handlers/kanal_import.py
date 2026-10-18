"""Arxiv kanaldan avtomatik import (FEATURE_KANAL_IMPORT).

Arxiv kanalga video tashlanadi, caption da serial nomi va qism raqami
bo'ladi — bot o'zi bazaga qo'shadi. FSM orqali bitta-bitta qo'shish
40 qismda charchatadi, bu esa vaqtni ancha tejaydi.

Caption formati:

    Spartak | 5          -> "Spartak" serialining 5-qismi
    Spartak | 2x5        -> 2-fasl, 5-qism
    Spartak | 5 | Nomi   -> qismning o'z nomi bilan

Serial topilmasa, o'sha nom bilan yangi serial yaratiladi (poster/tavsifni
keyin admin panelidan to'ldirasiz). Caption formatga tushmasa — tegilmaydi.
"""
import logging
import re

from aiogram import Bot, F, Router
from aiogram.types import Message

import db
import ui
from config import (
    ARCHIVE_CHANNEL_ID,
    FEATURE_TUR,
    FEATURE_AVTOPOST,
    FEATURE_BILDIRISHNOMA,
    FEATURE_JURNAL,
)

router = Router(name="kanal_import")
log = logging.getLogger(__name__)

bildirishnoma = avtopost = jurnal = None
if FEATURE_BILDIRISHNOMA:
    from handlers import bildirishnoma
if FEATURE_AVTOPOST:
    from handlers import avtopost
if FEATURE_JURNAL:
    from handlers import jurnal

# "2x5" yoki "5"
RAQAM = re.compile(r"^(?:(\d{1,2})\s*[xXхХ*]\s*)?(\d{1,4})$")


def tahlil(caption: str | None) -> tuple[str, int, int, str | None] | None:
    """caption -> (nom, fasl, qism, qism_nomi). Mos kelmasa None."""
    if not caption:
        return None
    if "|" not in caption:
        # FEATURE_TUR yoqilgan bo'lsa: raqamsiz caption = kino (bitta qism)
        return (caption.strip(), 1, 1, None) if FEATURE_TUR and caption.strip() else None
    bolaklar = [b.strip() for b in caption.split("|")]
    if len(bolaklar) < 2 or not bolaklar[0]:
        return None
    moslik = RAQAM.match(bolaklar[1])
    if not moslik:
        return None
    fasl = int(moslik.group(1) or 1)
    qism = int(moslik.group(2))
    nomi = bolaklar[2] if len(bolaklar) > 2 and bolaklar[2] else None
    return bolaklar[0], fasl, qism, nomi


@router.channel_post(F.chat.id == ARCHIVE_CHANNEL_ID, F.video)
async def kelgan_video(message: Message, bot: Bot):
    natija = tahlil(message.caption)
    if natija is None:
        return
    nom, fasl, qism, qism_nomi = natija

    kino = FEATURE_TUR and "|" not in (message.caption or "")
    serial = await db.get_serial_by_name(nom)
    yangi_serial = serial is None
    if yangi_serial:
        serial_id = await db.add_serial(nom, None, None, None, None)
        if kino:
            await db.turi_belgila(serial_id, "kino")
        serial = await db.get_serial(serial_id)
        log.info("kanal import: yangi serial yaratildi — %s", nom)

    mavjud = await db.get_episode(serial["id"], qism, fasl)
    await db.add_episode(
        serial["id"], qism, qism_nomi, message.message_id, message.video.duration, fasl
    )

    xabar = (
        f"{'🆕 Yangi serial + ' if yangi_serial else ''}"
        f"{'♻️ yangilandi' if mavjud else '✅ qo''shildi'}: "
        f"<b>{ui.esc(nom)}</b> — {fasl}x{qism}"
    )
    log.info("kanal import: %s %sx%s", nom, fasl, qism)
    if jurnal:
        await jurnal.hodisa(bot, f"📥 Kanal import: {xabar}")

    if mavjud:
        return
    if bildirishnoma:
        await bildirishnoma.yangi_qism(bot, serial, qism)
    if avtopost:
        await avtopost.yangi_qism(bot, serial, qism)
