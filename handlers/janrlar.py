"""Janr bo'yicha ro'yxat (FEATURE_JANR).

Asosiy menyudagi "🏷 Janrlar" -> janrlar ro'yxati -> tanlangan janrdagi
seriallar (sahifalangan). Serial tugmasini `kino` moduli oladi.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
import ui
from config import SERIALS_PER_PAGE

router = Router(name="janrlar")


@router.message(F.text == ui.JANRLAR)
async def royxat(message: Message, state: FSMContext):
    nomlar = await db.janrlar()
    await state.set_state(None)
    await ui.set_nav(state, "janrlar")
    await ui.screen(
        message,
        state,
        "🏷 <b>Janrlar</b>\nKerakli janrni tanlang:" if nomlar else "📭 Janrlar hali belgilanmagan.",
        ui.kb(*ui.rows([ui.JANR_PREFIX + n for n in nomlar], 2), [ui.HOME]),
    )


async def janr_ekrani(message: Message, state: FSMContext, janr: str, page: int = 0):
    jami = await db.janr_sanoq(janr)
    seriallar = await db.janr_seriallari(janr, page * SERIALS_PER_PAGE, SERIALS_PER_PAGE)
    await ui.set_nav(state, "janr", nav_janr=janr, nav_page=page)
    await ui.screen(
        message,
        state,
        f"🏷 <b>{ui.esc(janr)}</b> — {jami} ta serial" if jami else f"📭 {ui.esc(janr)} bo'yicha serial yo'q.",
        ui.kb(
            *[[ui.SERIAL_PREFIX + s["nom"]] for s in seriallar],
            ui.page_row(page, jami, SERIALS_PER_PAGE),
            [ui.BACK, ui.HOME],
        ),
    )


@router.message(F.text.startswith(ui.JANR_PREFIX), ui.ekran("janrlar"))
async def janr_tanlash(message: Message, state: FSMContext):
    await janr_ekrani(message, state, message.text[len(ui.JANR_PREFIX):].strip())


@router.message(F.text.in_({ui.PREV, ui.NEXT}), ui.ekran("janr"))
async def sahifa(message: Message, state: FSMContext):
    malumot = await state.get_data()
    page = max(0, malumot.get("nav_page", 0) + (1 if message.text == ui.NEXT else -1))
    await janr_ekrani(message, state, malumot["nav_janr"], page)


@router.message(F.text == ui.BACK, ui.ekran("janr"))
async def orqaga(message: Message, state: FSMContext):
    await royxat(message, state)
