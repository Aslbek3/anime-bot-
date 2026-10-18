"""Til tanlash (FEATURE_TIL).

`users.til` ustuni allaqachon bor edi — shu modul uni ishlatadi.

MUHIM CHEKLOV: bu to'liq i18n emas. Tugma matnlari (`ui.py`) o'zbekcha
qoladi, chunki routing aynan o'sha matnlar bo'yicha ketadi — ularni
tarjima qilish butun navigatsiyani sindiradi. Hozircha foydalanuvchi
ko'radigan asosiy xabarlar tarjima qilinadi. To'liq i18n qilinadigan
bo'lsa: tugmalarni kalit bo'yicha yo'naltirish (matn -> kalit lug'ati)
kerak, bu alohida ish.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
import ui

router = Router(name="til")

TILLAR = {ui.TIL_UZ: "uz", ui.TIL_RU: "ru"}

TARJIMA = {
    "salom": {
        "uz": "👋 Assalomu alaykum!\n\nKerakli serialni tugmalardan tanlang yoki nomini yozib qidiring.",
        "ru": "👋 Здравствуйте!\n\nВыберите сериал кнопками или напишите название для поиска.",
    },
    "bosh": {
        "uz": "📭 Hozircha serial qo'shilmagan.",
        "ru": "📭 Пока сериалов нет.",
    },
    "qismlar": {"uz": "📺 Qismlar", "ru": "📺 Серии"},
    "qism_yoq": {"uz": "📭 Qismlar hali qo'shilmagan.", "ru": "📭 Серии пока не добавлены."},
    "topilmadi": {
        "uz": "😕 Hech narsa topilmadi.",
        "ru": "😕 Ничего не найдено.",
    },
    "tanlandi": {"uz": "✅ Til o'zgartirildi.", "ru": "✅ Язык изменён."},
}


async def t(user_id: int, kalit: str) -> str:
    """Foydalanuvchi tilidagi matn."""
    return TARJIMA.get(kalit, {}).get(await db.til_ol(user_id), TARJIMA[kalit]["uz"])


@router.message(F.text == ui.TIL)
async def tanlash(message: Message, state: FSMContext):
    await state.set_state(None)
    await ui.set_nav(state, "til")
    joriy = await db.til_ol(message.from_user.id)
    await ui.screen(
        message,
        state,
        f"🌐 <b>Til / Язык</b>\nHozirgi: <b>{joriy}</b>",
        ui.kb([ui.TIL_UZ, ui.TIL_RU], [ui.HOME]),
    )


@router.message(F.text.in_(TILLAR), ui.ekran("til"))
async def belgilash(message: Message, state: FSMContext):
    from handlers.kino import show_main

    await db.til_belgila(message.from_user.id, TILLAR[message.text])
    await message.answer(await t(message.from_user.id, "tanlandi"))
    await show_main(message, state)
