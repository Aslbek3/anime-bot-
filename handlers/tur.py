"""Kino va serialni ajratish (FEATURE_TUR).

Bazada hamma narsa `serials` jadvalida yotadi — farq faqat `turi`
ustunida: 'serial' (standart) yoki 'kino'. Migratsiya ustunni o'zi
qo'shadi, shuning uchun mavjud yozuvlar serial bo'lib qolaveradi.

Farqi foydalanuvchi tomonida ko'rinadi:
- serial -> qismlar ro'yxati (+ fasllar, agar FEATURE_FASL yoqilgan bo'lsa);
- kino   -> qismlar ro'yxati yo'q, bitta "▶️ Ko'rish" tugmasi.

Asosiy menyuda "🎞 Kinolar" va "📺 Seriallar" ro'yxatlari ham bor.
"""
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
import ui
from config import SERIALS_PER_PAGE
from middlewares import AdminOnly

router = Router(name="tur")
admin_router = Router(name="tur_admin")
admin_router.message.outer_middleware(AdminOnly())
router.include_router(admin_router)

KINO = "kino"
SERIAL = "serial"


def kinomi(serial) -> bool:
    return (serial["turi"] or SERIAL) == KINO


async def royxat_ekrani(message: Message, state: FSMContext, turi: str, page: int = 0):
    jami = await db.turi_sanoq(turi)
    seriallar = await db.turi_royxati(turi, page * SERIALS_PER_PAGE, SERIALS_PER_PAGE)
    sarlavha = "🎞 <b>Kinolar</b>" if turi == KINO else "📺 <b>Seriallar</b>"
    await state.set_state(None)
    await ui.set_nav(state, "tur_royxat", nav_turi=turi, nav_page=page)
    await ui.screen(
        message,
        state,
        f"{sarlavha} — {jami} ta" if jami else f"{sarlavha}\n\n📭 Hozircha yo'q.",
        ui.kb(
            *[[ui.SERIAL_PREFIX + s["nom"]] for s in seriallar],
            ui.page_row(page, jami, SERIALS_PER_PAGE),
            [ui.HOME],
        ),
    )


@router.message(F.text == ui.KINOLAR)
async def kinolar(message: Message, state: FSMContext):
    await royxat_ekrani(message, state, KINO)


@router.message(F.text == ui.SERIALLAR)
async def seriallar(message: Message, state: FSMContext):
    await royxat_ekrani(message, state, SERIAL)


@router.message(F.text.in_({ui.PREV, ui.NEXT}), ui.ekran("tur_royxat"))
async def sahifa(message: Message, state: FSMContext):
    malumot = await state.get_data()
    page = max(0, malumot.get("nav_page", 0) + (1 if message.text == ui.NEXT else -1))
    await royxat_ekrani(message, state, malumot["nav_turi"], page)


@router.message(F.text == ui.KORISH, ui.ekran("serial"))
async def korish(message: Message, state: FSMContext, bot: Bot):
    """Kino kartochkasidagi yagona tugma — birinchi (va yagona) qismni yuboradi."""
    from handlers.kino import send_episode

    malumot = await state.get_data()
    serial_id = malumot["nav_serial"]
    qismlar = await db.list_episodes(serial_id, 0, 1)
    if not qismlar:
        await message.answer("⚠️ Bu kino hali yuklanmagan.")
        return
    await send_episode(message, state, bot, serial_id, qismlar[0]["qism_raqami"])


# ------------------------------------------------------ admin tomoni

@admin_router.message(F.text == ui.TUR_ALMASH, ui.ekran("a_edit"))
async def almashtirish(message: Message, state: FSMContext):
    from handlers.admin import show_edit

    malumot = await state.get_data()
    serial = await db.get_serial(malumot["nav_serial"])
    if serial is None:
        return
    yangi = SERIAL if kinomi(serial) else KINO
    await db.turi_belgila(serial["id"], yangi)
    await message.answer(f"✅ Turi: <b>{yangi}</b>")
    await show_edit(message, state, serial["id"])
