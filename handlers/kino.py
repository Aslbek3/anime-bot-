"""Asosiy menyu, serial kartochkasi va qism yuborish (reply tugmalar)."""
from contextlib import suppress

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
import ui
from config import ARCHIVE_CHANNEL_ID, EPISODES_PER_PAGE, SERIALS_PER_PAGE

router = Router(name="kino")

SALOM = (
    "👋 Assalomu alaykum!\n\n"
    "Kerakli serialni tugmalardan tanlang yoki nomini yozib qidiring."
)


# ------------------------------------------------------------------ ekranlar

async def show_main(message: Message, state: FSMContext, page: int = 0) -> None:
    jami = await db.count_serials()
    serials = await db.list_serials(page * SERIALS_PER_PAGE, SERIALS_PER_PAGE)
    davom = await db.last_progress(message.from_user.id)
    matn = SALOM if jami else "📭 Hozircha serial qo'shilmagan."
    await state.set_state(None)
    await ui.set_nav(state, "serials", nav_page=page)
    await ui.screen(message, state, matn, ui.main_menu_kb(serials, page, jami, davom))


async def show_serial(message: Message, state: FSMContext, serial_id: int, page: int = 0) -> bool:
    serial = await db.get_serial(serial_id)
    if serial is None:
        return False

    jami = await db.count_episodes(serial_id)
    episodes = await db.list_episodes(serial_id, page * EPISODES_PER_PAGE, EPISODES_PER_PAGE)

    qatorlar = [f"🎬 <b>{ui.esc(serial['nom'])}</b>"]
    belgilar = [b for b in (ui.esc(serial["janr"]), serial["yil"] and str(serial["yil"])) if b]
    if belgilar:
        qatorlar.append(" · ".join(belgilar))
    if serial["tavsif"]:
        qatorlar += ["", ui.esc(serial["tavsif"])]
    qatorlar += ["", f"📺 Qismlar: {jami}" if jami else "📭 Qismlar hali qo'shilmagan."]

    await state.set_state(None)
    await ui.set_nav(state, "serial", nav_serial=serial_id, nav_page=page)
    await ui.screen(
        message,
        state,
        "\n".join(qatorlar),
        ui.serial_kb(episodes, page, jami),
        serial["poster_file_id"],
    )
    return True


async def send_episode(message: Message, state: FSMContext, bot: Bot, serial_id: int, qism: int) -> None:
    serial = await db.get_serial(serial_id)
    episode = await db.get_episode(serial_id, qism)
    if serial is None or episode is None:
        await message.answer("⚠️ Bu qism topilmadi.")
        await show_main(message, state)
        return

    oldingi, keyingi = await db.prev_next_episode(serial_id, qism)
    sarlavha = f"🎬 <b>{ui.esc(serial['nom'])}</b>\n{qism}-qism"
    if episode["nom"]:
        sarlavha += f" — {ui.esc(episode['nom'])}"

    await ui.wipe(message, state)
    try:
        # video arxiv kanaldan ko'chiriladi (file_id bot tokeniga bog'liq bo'lgani uchun)
        yangi = await bot.copy_message(
            chat_id=message.chat.id,
            from_chat_id=ARCHIVE_CHANNEL_ID,
            message_id=episode["kanal_msg_id"],
            caption=sarlavha,
            reply_markup=ui.episode_kb(oldingi, keyingi),
        )
    except TelegramAPIError:
        await message.answer("⚠️ Videoni yuborib bo'lmadi. Admin bilan bog'laning.")
        await show_serial(message, state, serial_id)
        return

    await state.set_state(None)
    await ui.set_nav(state, "episode", nav_serial=serial_id, nav_qism=qism, nav_msg=yangi.message_id)
    await db.save_progress(message.from_user.id, serial_id, qism)


# ------------------------------------------------------------------ handlerlar

@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await show_main(message, state)


@router.message(F.text == ui.HOME)
async def home(message: Message, state: FSMContext):
    await show_main(message, state)


@router.message(F.text == ui.TO_LIST)
async def to_list(message: Message, state: FSMContext):
    malumot = await state.get_data()
    await show_main(message, state, malumot.get("nav_serials_page", 0))


@router.message(F.text.in_({ui.PREV, ui.NEXT}), ui.ekran("serials", "serial"))
async def pager(message: Message, state: FSMContext):
    malumot = await state.get_data()
    page = malumot.get("nav_page", 0) + (1 if message.text == ui.NEXT else -1)
    page = max(0, page)
    if malumot.get("nav_ekran") == "serials":
        await show_main(message, state, page)
    else:
        await show_serial(message, state, malumot["nav_serial"], page)


@router.message(F.text.startswith(ui.SERIAL_PREFIX))
async def open_serial(message: Message, state: FSMContext):
    nom = message.text[len(ui.SERIAL_PREFIX):].strip()
    serial = await db.get_serial_by_name(nom)
    if serial is None:
        await message.answer("⚠️ Bu serial topilmadi.")
        await show_main(message, state)
        return
    # ro'yxatning qaysi sahifasidan kelganini eslab qolamiz
    malumot = await state.get_data()
    if malumot.get("nav_ekran") == "serials":
        await state.update_data(nav_serials_page=malumot.get("nav_page", 0))
    await show_serial(message, state, serial["id"])


@router.message(F.text.startswith(ui.DAVOM_PREFIX))
async def davom(message: Message, state: FSMContext, bot: Bot):
    oxirgi = await db.last_progress(message.from_user.id)
    if oxirgi is None:
        await show_main(message, state)
        return
    await send_episode(message, state, bot, oxirgi["serial_id"], oxirgi["oxirgi_qism"])


@router.message(F.text.regexp(r"^\d+-qism$"), ui.ekran("serial", "episode"))
async def open_episode(message: Message, state: FSMContext, bot: Bot):
    malumot = await state.get_data()
    qism = int(message.text.split("-")[0])
    await send_episode(message, state, bot, malumot["nav_serial"], qism)


@router.message(F.text.in_({ui.PREV_EP, ui.NEXT_EP}), ui.ekran("episode"))
async def episode_nav(message: Message, state: FSMContext, bot: Bot):
    malumot = await state.get_data()
    serial_id, qism = malumot["nav_serial"], malumot["nav_qism"]
    oldingi, keyingi = await db.prev_next_episode(serial_id, qism)
    keyingisi = oldingi if message.text == ui.PREV_EP else keyingi
    if keyingisi is None:
        with suppress(TelegramAPIError):
            await message.delete()
        return
    await send_episode(message, state, bot, serial_id, keyingisi)


@router.message(F.text == ui.EPISODES, ui.ekran("episode"))
async def episode_list(message: Message, state: FSMContext):
    malumot = await state.get_data()
    serial_id, qism = malumot["nav_serial"], malumot["nav_qism"]
    page = await db.episode_page(serial_id, qism, EPISODES_PER_PAGE)
    await show_serial(message, state, serial_id, page)
