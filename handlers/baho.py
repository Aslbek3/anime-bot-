"""Baho va "Eng yaxshilar" (FEATURE_BAHO).

Serial ekranida 👍 / 👎, asosiy menyuda "⭐ Eng yaxshilar".
Bitta foydalanuvchi bitta serialga bitta baho qo'yadi (qayta bossa almashadi).
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
import ui

router = Router(name="baho")


async def qator(serial_id: int) -> list[str]:
    """Serial ekrani uchun baho tugmalari qatori (sanoq bilan)."""
    yoqdi, yoqmadi = await db.baho_sanoq(serial_id)
    return [f"{ui.YOQDI} {yoqdi}", f"{ui.YOQMADI} {yoqmadi}"]


def _baho(matn: str) -> int | None:
    if matn.startswith(ui.YOQDI):
        return 1
    if matn.startswith(ui.YOQMADI):
        return -1
    return None


def baho_tugmasi(message: Message) -> dict | bool:
    qiymat = _baho(message.text or "")
    return {"baho": qiymat} if qiymat else False


@router.message(baho_tugmasi, ui.ekran("serial", "episode"))
async def qoyish(message: Message, state: FSMContext, baho: int):
    from handlers.kino import show_serial

    malumot = await state.get_data()
    serial_id = malumot["nav_serial"]
    await db.baho_qoy(message.from_user.id, serial_id, baho)
    await message.answer("👍 Bahoyingiz yozildi." if baho > 0 else "👎 Bahoyingiz yozildi.")
    await show_serial(message, state, serial_id, malumot.get("nav_page", 0))


@router.message(F.text == ui.ENG_YAXSHI)
async def eng_yaxshilar(message: Message, state: FSMContext):
    seriallar = await db.eng_yaxshilar()
    qatorlar = ["⭐ <b>Eng yaxshilar</b>", ""]
    qatorlar += [f"{i}. {ui.esc(s['nom'])} — {s['ball']:+d}" for i, s in enumerate(seriallar, 1)]
    await state.set_state(None)
    await ui.set_nav(state, "eng_yaxshi")
    await ui.screen(
        message,
        state,
        "\n".join(qatorlar) if seriallar else "⭐ Hali baho qo'yilmagan.",
        ui.kb(*[[ui.SERIAL_PREFIX + s["nom"]] for s in seriallar], [ui.HOME]),
    )
