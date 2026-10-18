"""Asosiy menyu, serial kartochkasi va qism yuborish (reply tugmalar)."""
from aiogram import Bot, F, Router
from aiogram.enums import ChatAction
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import re

import db
import ui
from config import (
    ARCHIVE_CHANNEL_ID,
    EPISODES_PER_PAGE,
    FEATURE_BAHO,
    FEATURE_FASL,
    FEATURE_KORILGAN,
    FEATURE_KUZATISH,
    FEATURE_MANBA,
    FEATURE_TIL,
    FEATURE_TUR,
    SERIALS_PER_PAGE,
)

# Bayroqli modullar: o'chiq bo'lsa import ham qilinmaydi
baho = fasl = korilgan = kuzatish = manba = til = tur = None
if FEATURE_BAHO:
    from handlers import baho
if FEATURE_FASL:
    from handlers import fasl
if FEATURE_KORILGAN:
    import korilgan
if FEATURE_KUZATISH:
    from handlers import kuzatish
if FEATURE_MANBA:
    from handlers import manba
if FEATURE_TIL:
    from handlers import til
if FEATURE_TUR:
    from handlers import tur

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
    if til:
        matn = await til.t(message.from_user.id, "salom" if jami else "bosh")
    else:
        matn = SALOM if jami else "📭 Hozircha serial qo'shilmagan."
    await state.set_state(None)
    await ui.set_nav(state, "serials", nav_page=page)
    await ui.screen(message, state, matn, ui.main_menu_kb(serials, page, jami, davom))


async def show_serial(message: Message, state: FSMContext, serial_id: int, page: int = 0) -> bool:
    serial = await db.get_serial(serial_id)
    # tasdiqlanmagan taklif foydalanuvchiga ochilmaydi (deeplink orqali ham)
    if serial is None or serial["holat"] not in (None, "", "tasdiqlangan"):
        return False

    malumot = await state.get_data()
    kino_turi = bool(tur and tur.kinomi(serial))
    fasl_raqami = None
    if kino_turi:
        jami, episodes = 0, []
    elif fasl:
        mavjud = await db.fasllar(serial_id) or [1]
        fasl_raqami = malumot.get("nav_fasl", mavjud[0])
        if fasl_raqami not in mavjud:
            fasl_raqami = mavjud[0]
        jami = await db.fasl_sanoq(serial_id, fasl_raqami)
        episodes = await db.fasl_episodes(
            serial_id, fasl_raqami, page * EPISODES_PER_PAGE, EPISODES_PER_PAGE
        )
    else:
        jami = await db.count_episodes(serial_id)
        episodes = await db.list_episodes(serial_id, page * EPISODES_PER_PAGE, EPISODES_PER_PAGE)

    qatorlar = [f"🎬 <b>{ui.esc(serial['nom'])}</b>"]
    belgilar = [b for b in (ui.esc(serial["janr"]), serial["yil"] and str(serial["yil"])) if b]
    if belgilar:
        qatorlar.append(" · ".join(belgilar))
    if serial["tavsif"]:
        qatorlar += ["", ui.esc(serial["tavsif"])]
    if fasl_raqami and fasl_raqami != 1:
        qatorlar.append(f"📂 {fasl_raqami}-fasl")
    if kino_turi:
        qatorlar.append("🎞 Kino")
    qismlar_yozuvi = await til.t(message.from_user.id, "qismlar") if til else "📺 Qismlar"
    yoq_yozuvi = (
        await til.t(message.from_user.id, "qism_yoq") if til else "📭 Qismlar hali qo'shilmagan."
    )
    if not kino_turi:
        qatorlar += ["", f"{qismlar_yozuvi}: {jami}" if jami else yoq_yozuvi]
    if serial["qoshgan_user_id"]:
        muallif = await db.get_user(serial["qoshgan_user_id"])
        if muallif:
            nomi = f"@{muallif['username']}" if muallif["username"] else (muallif["ism"] or "foydalanuvchi")
            qatorlar.append(f"➕ qo'shdi: {ui.esc(nomi)}")

    # modullar qo'shadigan tugma qatorlari
    qoshimcha = []
    if kino_turi:
        qoshimcha.append([ui.KORISH])
    if fasl:
        fasl_qatori = await fasl.qator(serial_id)
        if fasl_qatori:
            qoshimcha.append(fasl_qatori)
    if kuzatish:
        qoshimcha.append([await kuzatish.tugma(message.from_user.id, serial_id)])
    if baho:
        qoshimcha.append(await baho.qator(serial_id))
    chegara = await korilgan.chegara(message.from_user.id, serial_id) if korilgan else 0

    await state.set_state(None)
    await ui.set_nav(
        state, "serial", nav_serial=serial_id, nav_page=page, nav_fasl=fasl_raqami or 1
    )
    await ui.screen(
        message,
        state,
        "\n".join(qatorlar),
        ui.serial_kb(episodes, page, jami, qoshimcha, chegara),
        serial["poster_file_id"],
    )
    return True


async def send_episode(message: Message, state: FSMContext, bot: Bot, serial_id: int, qism: int) -> None:
    malumot = await state.get_data()
    fasl_raqami = malumot.get("nav_fasl") if fasl else None
    serial = await db.get_serial(serial_id)
    episode = await db.get_episode(serial_id, qism, fasl_raqami)
    if episode is None and fasl_raqami:
        episode = await db.get_episode(serial_id, qism)   # boshqa fasldan topilsa ham mayli
        fasl_raqami = episode["fasl"] if episode else None
    if serial is None or episode is None:
        await message.answer("⚠️ Bu qism topilmadi.")
        await show_main(message, state)
        return

    oldingi, keyingi = await db.prev_next_episode(serial_id, qism, fasl_raqami)
    sarlavha = f"🎬 <b>{ui.esc(serial['nom'])}</b>\n{qism}-qism"
    if episode["nom"]:
        sarlavha += f" — {ui.esc(episode['nom'])}"

    km = await ui.kb_if_new(state, ui.episode_kb(oldingi, keyingi))
    await bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)
    try:
        # video arxiv kanaldan ko'chiriladi (file_id bot tokeniga bog'liq bo'lgani uchun)
        await bot.copy_message(
            chat_id=message.chat.id,
            from_chat_id=ARCHIVE_CHANNEL_ID,
            message_id=episode["kanal_msg_id"],
            caption=sarlavha,
            reply_markup=km,
        )
    except TelegramAPIError:
        await message.answer("⚠️ Videoni yuborib bo'lmadi. Admin bilan bog'laning.")
        await show_serial(message, state, serial_id)
        return

    await state.set_state(None)
    await ui.set_nav(
        state, "episode", nav_serial=serial_id, nav_qism=qism, nav_fasl=fasl_raqami or 1
    )
    await db.save_progress(message.from_user.id, serial_id, qism)


# ------------------------------------------------------------------ handlerlar

# Deeplink: t.me/<bot>?start=serial_12 yoki ?start=qism_12_3
# CommandStart(deep_link=True) oddiy /start dan OLDIN turishi shart.
@router.message(CommandStart(deep_link=True))
async def start_havola(message: Message, state: FSMContext, command: CommandObject, bot: Bot):
    bolaklar = (command.args or "").split("_")
    ochildi = False
    if manba and await manba.yoz(command.args or "", message.from_user.id):
        bolaklar = [""]          # ref_ havolasi: faqat sanaymiz, menyuni ochamiz
    if bolaklar[0] == "serial" and len(bolaklar) == 2 and bolaklar[1].isdigit():
        ochildi = await show_serial(message, state, int(bolaklar[1]))
    elif bolaklar[0] == "qism" and len(bolaklar) == 3 and all(b.isdigit() for b in bolaklar[1:]):
        serial_id, qism = int(bolaklar[1]), int(bolaklar[2])
        if await show_serial(message, state, serial_id):
            await send_episode(message, state, bot, serial_id, qism)
            ochildi = True
    if not ochildi:
        await show_main(message, state)


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


@router.message(F.text.regexp(ui.QISM_NAQSH), ui.ekran("serial", "episode"))
async def open_episode(message: Message, state: FSMContext, bot: Bot):
    malumot = await state.get_data()
    qism = int(re.search(r"\d+", message.text).group())
    await send_episode(message, state, bot, malumot["nav_serial"], qism)


@router.message(F.text.in_({ui.PREV_EP, ui.NEXT_EP}), ui.ekran("episode"))
async def episode_nav(message: Message, state: FSMContext, bot: Bot):
    malumot = await state.get_data()
    serial_id, qism = malumot["nav_serial"], malumot["nav_qism"]
    oldingi, keyingi = await db.prev_next_episode(
        serial_id, qism, malumot.get("nav_fasl") if fasl else None
    )
    keyingisi = oldingi if message.text == ui.PREV_EP else keyingi
    if keyingisi is None:
        return
    await send_episode(message, state, bot, serial_id, keyingisi)


@router.message(F.text == ui.EPISODES, ui.ekran("episode"))
async def episode_list(message: Message, state: FSMContext):
    malumot = await state.get_data()
    serial_id, qism = malumot["nav_serial"], malumot["nav_qism"]
    page = await db.episode_page(
        serial_id, qism, EPISODES_PER_PAGE, malumot.get("nav_fasl") if fasl else None
    )
    await show_serial(message, state, serial_id, page)


# Bot qayta ishga tushsa nav konteksti (MemoryStorage) yo'qoladi. Shunda
# chatdagi eski tugmalar qidiruvga tushib "topilmadi" degan g'alati javob
# berardi — shu yerda ushlab, asosiy menyuni qaytaramiz.
@router.message(F.text.regexp(ui.QISM_NAQSH), ui.ekran_yoq())
@router.message(
    F.text.in_({ui.PREV, ui.NEXT, ui.EPISODES, ui.PREV_EP, ui.NEXT_EP, ui.TO_LIST}),
    ui.ekran_yoq(),
)
async def eskirgan_ekran(message: Message, state: FSMContext):
    await message.answer("ℹ️ Bu ekran eskirgan. Asosiy menyuni qaytadan ochdim.")
    await show_main(message, state)
