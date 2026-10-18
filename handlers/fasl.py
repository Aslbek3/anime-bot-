"""Fasl (season) qo'llab-quvvatlash (FEATURE_FASL).

`episodes.fasl` ustuni migratsiya bilan qo'shiladi, standart qiymati 1 —
shuning uchun bayroq o'chiq bo'lsa hamma narsa avvalgidek ishlaydi.

- Foydalanuvchi: serialda bir nechta fasl bo'lsa, kartochkada
  "📂 1-fasl / 📂 2-fasl" qatori chiqadi.
- Admin: tahrirlash ekranidagi "📂 Fasl belgilash" — qismlar oralig'iga
  fasl raqamini beradi, masalan `13-24 = 2`.
"""
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

import db
import ui
from middlewares import AdminOnly

router = Router(name="fasl")
admin_router = Router(name="fasl_admin")
admin_router.message.outer_middleware(AdminOnly())
router.include_router(admin_router)

ORALIQ = re.compile(r"^(\d{1,4})\s*(?:-\s*(\d{1,4}))?\s*=\s*(\d{1,2})$")


class FaslBelgilash(StatesGroup):
    oraliq = State()


def tugma(raqam: int) -> str:
    return f"{ui.FASL_PREFIX}{raqam}-fasl"


async def qator(serial_id: int) -> list[str]:
    """Serial kartochkasi uchun fasl tugmalari (bitta fasl bo'lsa — bo'sh)."""
    nomlar = await db.fasllar(serial_id)
    return [tugma(f) for f in nomlar] if len(nomlar) > 1 else []


@router.message(F.text.startswith(ui.FASL_PREFIX), ui.ekran("serial", "episode"))
async def tanlash(message: Message, state: FSMContext):
    from handlers.kino import show_serial

    malumot = await state.get_data()
    raqam = message.text[len(ui.FASL_PREFIX):].split("-")[0]
    if not raqam.isdigit():
        return
    await state.update_data(nav_fasl=int(raqam))
    await show_serial(message, state, malumot["nav_serial"], 0)


# ------------------------------------------------------ admin tomoni

@admin_router.message(F.text == ui.FASL_BELGILASH, ui.ekran("a_edit"))
async def sorash(message: Message, state: FSMContext):
    malumot = await state.get_data()
    fasllar = await db.fasllar(malumot["nav_serial"])
    await ui.screen(
        message,
        state,
        "📂 <b>Fasl belgilash</b>\n\n"
        "Qaysi qismlar qaysi faslga tegishli?\n"
        "Masalan: <code>13-24 = 2</code> yoki <code>7 = 3</code>\n\n"
        f"Hozirgi fasllar: {', '.join(str(f) for f in fasllar) or '1'}",
        ui.kb([ui.CANCEL], [ui.HOME]),
    )
    await state.set_state(FaslBelgilash.oraliq)


@admin_router.message(FaslBelgilash.oraliq, F.text)
async def belgilash(message: Message, state: FSMContext):
    from handlers.admin import show_edit

    moslik = ORALIQ.match(message.text.replace(" ", ""))
    if not moslik:
        await ui.screen(
            message, state, "⚠️ Format: <code>13-24 = 2</code>", ui.kb([ui.CANCEL], [ui.HOME])
        )
        return

    boshi = int(moslik.group(1))
    oxiri = int(moslik.group(2) or boshi)
    fasl = int(moslik.group(3))
    malumot = await state.get_data()
    serial_id = malumot["nav_serial"]

    sanoq = otkazildi = 0
    for qism in range(boshi, oxiri + 1):
        if await db.get_episode(serial_id, qism) is None:
            continue
        if await db.get_episode(serial_id, qism, fasl) is not None:
            otkazildi += 1       # o'sha faslda bu raqam band
            continue
        await db.episode_fasl(serial_id, qism, fasl)
        sanoq += 1

    await state.set_state(None)
    xabar = f"✅ {sanoq} ta qism {fasl}-faslga belgilandi."
    if otkazildi:
        xabar += f"\n↩️ {otkazildi} tasi o'tkazildi: {fasl}-faslda bunday raqam bor."
    await message.answer(xabar)
    await show_edit(message, state, serial_id)
