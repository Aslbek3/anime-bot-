"""Qism videosini almashtirish (FEATURE_QISM_ALMASH).

Video xato chiqsa yoki sifatini yaxshilasangiz: admin panel -> "♻️ Qismni
almashtirish" -> serial -> qism raqami -> arxiv kanaldan yangi videoni
forward qilasiz. Qism raqami va nomi o'zgarmaydi, faqat `kanal_msg_id`.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

import db
import ui
from config import ARCHIVE_CHANNEL_ID
from handlers.admin import forward_manba, show_picker
from middlewares import AdminOnly

router = Router(name="qism_almash")
router.message.outer_middleware(AdminOnly())


class Almash(StatesGroup):
    raqam = State()
    video = State()


@router.message(F.text == ui.QISM_ALMASH)
async def boshlash(message: Message, state: FSMContext):
    await show_picker(message, state, "almash")


@router.message(F.text.startswith(ui.SERIAL_PREFIX), ui.ekran("a_pick"))
async def serial_tanlandi(message: Message, state: FSMContext):
    malumot = await state.get_data()
    if malumot.get("nav_maqsad") != "almash":
        return
    serial = await db.get_serial_by_name(message.text[len(ui.SERIAL_PREFIX):].strip())
    if serial is None:
        await show_picker(message, state, "almash")
        return
    jami = await db.count_episodes(serial["id"])
    await ui.set_nav(state, "a_almash", nav_serial=serial["id"])
    await ui.screen(
        message,
        state,
        f"♻️ <b>{ui.esc(serial['nom'])}</b>\nQaysi qismni almashtiramiz? Raqamini yozing (1–{jami}).",
        ui.kb([ui.ADMIN_BACK], [ui.HOME]),
    )
    await state.set_state(Almash.raqam)


@router.message(Almash.raqam, F.text)
async def raqam_qabul(message: Message, state: FSMContext):
    malumot = await state.get_data()
    raqam = message.text.strip()
    if not raqam.isdigit() or await db.get_episode(malumot["nav_serial"], int(raqam)) is None:
        await ui.screen(message, state, "⚠️ Bunday qism yo'q. Raqamni qaytadan yozing:", ui.kb([ui.ADMIN_BACK], [ui.HOME]))
        return
    await state.update_data(almash_qism=int(raqam))
    await ui.screen(
        message,
        state,
        f"♻️ {raqam}-qism uchun <b>yangi videoni arxiv kanaldan forward qiling</b>.",
        ui.kb([ui.ADMIN_BACK], [ui.HOME]),
    )
    await state.set_state(Almash.video)


@router.message(Almash.video)
async def video_qabul(message: Message, state: FSMContext):
    manba = forward_manba(message)
    if manba is None or manba[0] != ARCHIVE_CHANNEL_ID:
        await message.answer("Videoni <b>arxiv kanaldan forward</b> qiling.")
        return

    malumot = await state.get_data()
    qism = malumot["almash_qism"]
    davomiyligi = message.video.duration if message.video else None
    await db.episode_yangila(malumot["nav_serial"], qism, manba[1], davomiyligi)
    await state.set_state(None)
    await ui.screen(
        message,
        state,
        f"✅ {qism}-qism videosi almashtirildi.",
        ui.kb([ui.QISM_ALMASH], [ui.ADMIN_BACK], [ui.HOME]),
    )
