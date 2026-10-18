"""Tasodifiy va yangi qo'shilganlar (FEATURE_KASHFIYOT).

Asosiy menyudagi "🎲 Tasodifiy" va "🆕 Yangilar" tugmalari.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
import ui

router = Router(name="kashfiyot")

YANGI_KUN = 14


@router.message(F.text == ui.TASODIFIY)
async def tasodifiy(message: Message, state: FSMContext):
    from handlers.kino import show_main, show_serial

    serial = await db.tasodifiy_serial()
    if serial is None:
        await show_main(message, state)
        return
    await show_serial(message, state, serial["id"])


@router.message(F.text == ui.YANGILAR)
async def yangilar(message: Message, state: FSMContext):
    seriallar = await db.yangi_seriallar(YANGI_KUN)
    await state.set_state(None)
    await ui.set_nav(state, "yangilar")
    await ui.screen(
        message,
        state,
        f"🆕 <b>So'nggi {YANGI_KUN} kunda qo'shilganlar</b> — {len(seriallar)} ta"
        if seriallar
        else f"🆕 So'nggi {YANGI_KUN} kunda yangi serial qo'shilmadi.",
        ui.kb(*[[ui.SERIAL_PREFIX + s["nom"]] for s in seriallar], [ui.HOME]),
    )
