"""Kuzatish / sevimlilar (FEATURE_KUZATISH).

Serial ekranidagi "🔔 Kuzatish" tugmasi serialni kuzatuvga qo'shadi.
Yangi qism chiqqanda bildirishnoma avvalo kuzatuvchilarga ketadi
(handlers/bildirishnoma.py shu moduldan ro'yxat oladi).
"""
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
import ui

router = Router(name="kuzatish")


async def tugma(user_id: int, serial_id: int) -> str:
    """Serial ekrani uchun tugma matni (holatga qarab)."""
    return ui.KUZATMA if await db.kuzatuv_bormi(user_id, serial_id) else ui.KUZATISH


@router.message(F.text.in_({ui.KUZATISH, ui.KUZATMA}), ui.ekran("serial", "episode"))
async def almashtirish(message: Message, state: FSMContext):
    malumot = await state.get_data()
    serial_id = malumot["nav_serial"]
    from handlers.kino import show_serial  # kech import: kino bu modulni chaqiradi

    yoqildi = await db.kuzatuv_almashtir(message.from_user.id, serial_id)
    await message.answer(
        "🔔 Kuzatuvga qo'shildi — yangi qism chiqsa xabar beraman."
        if yoqildi
        else "🔕 Kuzatuvdan olib tashlandi."
    )
    await show_serial(message, state, serial_id, malumot.get("nav_page", 0))


@router.message(F.text == ui.KUZATGANLARIM)
async def royxat(message: Message, state: FSMContext):
    seriallar = await db.kuzatganlarim(message.from_user.id)
    await state.set_state(None)
    await ui.set_nav(state, "kuzatganlarim")
    await ui.screen(
        message,
        state,
        f"🔔 <b>Kuzatganlarim</b> — {len(seriallar)} ta"
        if seriallar
        else "🔕 Hali hech narsani kuzatmayapsiz.\nSerial ichidagi 🔔 tugmasini bosing.",
        ui.kb(*[[ui.SERIAL_PREFIX + s["nom"]] for s in seriallar], [ui.HOME]),
    )
