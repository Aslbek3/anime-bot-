"""Qism raqamini yozib o'tish (FEATURE_RAQAM).

Serial yoki qism ekranida foydalanuvchi shunchaki "45" deb yozsa,
45-qism yuboriladi — 100 qismli serialda varaqlab o'tirmaslik uchun.

Router `kino` dan keyin, `qidiruv` dan oldin ulanadi: faqat serial/qism
ekranidagi sof raqam ushlanadi, qolgan matn qidiruvga ketaveradi.
"""
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
import ui
from handlers.kino import send_episode

router = Router(name="qism_raqam")


@router.message(F.text.regexp(r"^\d{1,4}$"), ui.ekran("serial", "episode"))
async def raqam(message: Message, state: FSMContext, bot: Bot):
    malumot = await state.get_data()
    serial_id = malumot["nav_serial"]
    qism = int(message.text)

    if await db.get_episode(serial_id, qism) is None:
        jami = await db.count_episodes(serial_id)
        await message.answer(f"⚠️ {qism}-qism yo'q. Mavjud qismlar: 1–{jami}.")
        return

    await send_episode(message, state, bot, serial_id, qism)
