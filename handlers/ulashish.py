"""Ulashish tugmasi (FEATURE_ULASHISH).

Serial kartochkasidagi "🔗 Ulashish" — foydalanuvchiga shu serialning
deeplink havolasini beradi (do'stiga yuborishi uchun).
"""
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
import ui

router = Router(name="ulashish")


@router.message(F.text == ui.ULASHISH, ui.ekran("serial", "episode"))
async def ulash(message: Message, state: FSMContext, bot: Bot):
    malumot = await state.get_data()
    serial = await db.get_serial(malumot["nav_serial"])
    if serial is None:
        return

    serial_havola = await ui.havola(bot, f"serial_{serial['id']}")
    matn = f"🔗 <b>{ui.esc(serial['nom'])}</b>\n\n{serial_havola}"
    qism = malumot.get("nav_qism")
    if qism:
        qism_havola = await ui.havola(bot, f"qism_{serial['id']}_{qism}")
        matn += f"\n\n{qism}-qismga havola:\n{qism_havola}"

    # Klaviatura ataylab yuborilmaydi: foydalanuvchi o'sha ekranda qoladi
    await message.answer(matn, disable_web_page_preview=True)
