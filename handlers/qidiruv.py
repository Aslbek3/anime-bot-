"""Qidiruv: tugma bosilmagan oddiy matn serial nomi deb qabul qilinadi.

Bu router eng oxirida ulanadi — hamma tugma, buyruq va FSM holatlaridan keyin.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
import ui

router = Router(name="qidiruv")


@router.message(F.text, ~F.text.startswith("/"))
async def qidir(message: Message, state: FSMContext):
    soz = message.text.strip()
    if len(soz) < 2:
        await ui.screen(
            message, state, "🔎 Qidirish uchun kamida 2 ta harf yozing.", ui.simple_kb()
        )
        return

    topilgan = await db.search_serials(soz)
    if not topilgan:
        await ui.set_nav(state, "qidiruv")
        await ui.screen(
            message,
            state,
            f"😕 <b>{ui.esc(soz)}</b> bo'yicha hech narsa topilmadi.\n"
            "Nomini boshqacha yozib ko'ring yoki adminga murojaat qiling.",
            ui.simple_kb(ui.MUROJAT),
        )
        return

    await ui.set_nav(state, "qidiruv")
    await ui.screen(
        message,
        state,
        f"🔎 <b>{ui.esc(soz)}</b> bo'yicha {len(topilgan)} ta natija:",
        ui.kb(*[[ui.SERIAL_PREFIX + s["nom"]] for s in topilgan], [ui.HOME]),
    )
