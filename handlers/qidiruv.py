"""Qidiruv: tugma bosilmagan oddiy matn serial nomi deb qabul qilinadi.

Bu router eng oxirida ulanadi — hamma tugma, buyruq va FSM holatlaridan keyin.
Natijalar sahifalanadi: nav kontekstida qidiruv so'zi va sahifa saqlanadi.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
import ui
from config import FEATURE_FUZZY, FEATURE_QIDIRUV_JURNALI, SERIALS_PER_PAGE

fuzzy = jurnal = None
if FEATURE_FUZZY:
    import fuzzy
if FEATURE_QIDIRUV_JURNALI:
    from handlers import qidiruv_jurnali as jurnal

router = Router(name="qidiruv")


async def natijalar(message: Message, state: FSMContext, soz: str, page: int = 0) -> None:
    jami = await db.search_count(soz)
    topilgan = await db.search_page(soz, page * SERIALS_PER_PAGE, SERIALS_PER_PAGE)
    await ui.set_nav(state, "qidiruv", nav_soz=soz, nav_page=page)
    await ui.screen(
        message,
        state,
        f"🔎 <b>{ui.esc(soz)}</b> bo'yicha {jami} ta natija:",
        ui.kb(
            *[[ui.SERIAL_PREFIX + t["nom"]] for t in topilgan],
            ui.page_row(page, jami, SERIALS_PER_PAGE),
            [ui.HOME],
        ),
    )


@router.message(F.text.in_({ui.PREV, ui.NEXT}), ui.ekran("qidiruv"))
async def sahifa(message: Message, state: FSMContext):
    malumot = await state.get_data()
    page = max(0, malumot.get("nav_page", 0) + (1 if message.text == ui.NEXT else -1))
    await natijalar(message, state, malumot["nav_soz"], page)


@router.message(F.text, ~F.text.startswith("/"))
async def qidir(message: Message, state: FSMContext):
    soz = message.text.strip()
    if len(soz) < 2:
        await ui.screen(
            message, state, "🔎 Qidirish uchun kamida 2 ta harf yozing.", ui.simple_kb()
        )
        return

    topildi = await db.search_count(soz)
    if jurnal:
        await jurnal.yoz(soz, message.from_user.id, bool(topildi))

    if not topildi and fuzzy:
        # LIKE topmadi — xatoga chidamli qidiruvga o'tamiz
        yaqinlar = await fuzzy.yaqinlari(soz)
        if yaqinlar:
            await ui.set_nav(state, "qidiruv_bosh")
            await ui.screen(
                message,
                state,
                f"🤔 <b>{ui.esc(soz)}</b> topilmadi. Shulardan birini qidirdingizmi?",
                ui.kb(*[[ui.SERIAL_PREFIX + y["nom"]] for y in yaqinlar], [ui.HOME]),
            )
            return

    if not topildi:
        await ui.set_nav(state, "qidiruv_bosh")
        await ui.screen(
            message,
            state,
            f"😕 <b>{ui.esc(soz)}</b> bo'yicha hech narsa topilmadi.\n"
            "Nomini boshqacha yozib ko'ring yoki adminga murojaat qiling.",
            ui.simple_kb(ui.MUROJAT),
        )
        return

    await natijalar(message, state, soz)
