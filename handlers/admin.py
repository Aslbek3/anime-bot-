"""Admin panel (reply tugmalar). Faqat .env dagi ADMIN_ID uchun — AdminOnly middleware."""
import asyncio
import re

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

import db
import ui
from config import (
    ARCHIVE_CHANNEL_ID,
    FEATURE_AVTOPOST,
    FEATURE_BILDIRISHNOMA,
    FEATURE_TAKLIF,
    FEATURE_YUKLASH,
    BROADCAST_CHUNK,
    BROADCAST_PAUSE,
    EPISODES_PER_PAGE,
    SERIALS_PER_PAGE,
)
from handlers.kino import show_main
from middlewares import AdminOnly

router = Router(name="admin")
router.message.outer_middleware(AdminOnly())

# Bayroqli modullar: o'chiq bo'lsa import ham qilinmaydi
bildirishnoma = None
avtopost = None
if FEATURE_BILDIRISHNOMA:
    from handlers import bildirishnoma
if FEATURE_AVTOPOST:
    from handlers import avtopost

_fon: set[asyncio.Task] = set()


def fonda(korutina) -> None:
    """Uzoq cho'ziladigan ishni fonga beradi — admin ekrani kutib qolmasin."""
    vazifa = asyncio.create_task(korutina)
    _fon.add(vazifa)
    vazifa.add_done_callback(_fon.discard)

# --- tugma matnlari ---
ADD = "➕ Serial qo'shish"
EP_ADD = "🎬 Qism qo'shish"
EDIT = "✏️ Tahrirlash / o'chirish"
STAT = "📊 Statistika"
BC = "📨 Tarqatish"
MUR = "💬 Murojatlar"
SKIP = ui.SKIP
DEL_SERIAL = "🗑 Serialni o'chirish"
DEL_EPISODES = "🗑 Qismlarni o'chirish"
DEL_YES = "🗑 Ha, o'chirilsin"
DEL_NO = "⬅️ Yo'q"
BC_SEND = "📨 Yuborish"
MAYDONLAR = {
    "✏️ Nom": "nom",
    "✏️ Tavsif": "tavsif",
    "✏️ Janr": "janr",
    "✏️ Yil": "yil",
    "🖼 Poster": "poster_file_id",
}

MENU_MATN = "🛠 <b>Admin panel</b>\nKerakli bo'limni tanlang."


class SerialAdd(StatesGroup):
    nom = State()
    tavsif = State()
    poster = State()
    janr = State()
    yil = State()


class EpisodeAdd(StatesGroup):
    forward = State()


class SerialEdit(StatesGroup):
    qiymat = State()


class Broadcast(StatesGroup):
    xabar = State()


def menu_kb():
    # modul tugmalari faqat bayroq yoqilganda chiziladi
    return ui.kb(
        [ADD],
        [EP_ADD],
        [EDIT],
        [ui.YUKLASH] if FEATURE_YUKLASH else [],
        [ui.TAKLIFLAR] if FEATURE_TAKLIF else [],
        [STAT, BC],
        [MUR],
        [ui.HOME],
    )


def step_kb(skip: bool = False):
    """FSM qadamlari uchun: bekor qilish har doim ko'rinib turadi."""
    return ui.kb([SKIP] if skip else [], [ui.CANCEL], [ui.HOME])


async def show_menu(message: Message, state: FSMContext):
    await state.set_state(None)
    await ui.set_nav(state, "a_menu")
    await ui.screen(message, state, MENU_MATN, menu_kb())


async def show_picker(message: Message, state: FSMContext, maqsad: str, page: int = 0):
    """Serial tanlash ro'yxati (sahifalangan). maqsad: 'eps' yoki 'edit'."""
    jami = await db.count_serials()
    serials = await db.list_serials(page * SERIALS_PER_PAGE, SERIALS_PER_PAGE)
    sarlavha = {
        "eps": "🎬 Qaysi serialga qism qo'shamiz?",
        "edit": "✏️ Qaysi serialni tahrirlaymiz?",
    }[maqsad]
    await state.set_state(None)
    await ui.set_nav(state, "a_pick", nav_page=page, nav_maqsad=maqsad)
    await ui.screen(
        message,
        state,
        sarlavha if jami else "📭 Hali serial yo'q. Avval serial qo'shing.",
        ui.kb(
            *[[ui.SERIAL_PREFIX + s["nom"]] for s in serials],
            ui.page_row(page, jami, SERIALS_PER_PAGE),
            [ui.ADMIN_BACK, ui.HOME],
        ),
    )


# ------------------------------------------------- umumiy navigatsiya

@router.message(Command("admin"))
async def admin_buyruq(message: Message, state: FSMContext):
    await show_menu(message, state)


@router.message(F.text.in_({ui.CANCEL, ui.ADMIN_BACK, ui.DONE}))
async def bekor(message: Message, state: FSMContext):
    await show_menu(message, state)


@router.message(F.text == ui.HOME)
async def asosiy(message: Message, state: FSMContext):
    await show_main(message, state)


@router.message(F.text.in_({ui.PREV, ui.NEXT}), ui.ekran("a_pick", "a_epdel"))
async def pager(message: Message, state: FSMContext):
    malumot = await state.get_data()
    page = max(0, malumot.get("nav_page", 0) + (1 if message.text == ui.NEXT else -1))
    if malumot["nav_ekran"] == "a_pick":
        await show_picker(message, state, malumot["nav_maqsad"], page)
    else:
        await show_episode_delete(message, state, malumot["nav_serial"], page)


# --------------------------------------------------- serial qo'shish

@router.message(F.text == ADD)
async def add_start(message: Message, state: FSMContext):
    await ui.set_nav(state, "a_add")
    await ui.screen(message, state, "➕ <b>Yangi serial</b>\n\n1/5 — serial nomini yuboring:", step_kb())
    await state.set_state(SerialAdd.nom)


@router.message(SerialAdd.nom, F.text)
async def add_nom(message: Message, state: FSMContext):
    await state.update_data(yangi_nom=message.text.strip())
    await ui.screen(message, state, "2/5 — tavsifni yuboring:", step_kb(skip=True))
    await state.set_state(SerialAdd.tavsif)


@router.message(SerialAdd.tavsif, F.text)
async def add_tavsif(message: Message, state: FSMContext):
    await state.update_data(yangi_tavsif=bosh(message.text))
    await ui.screen(message, state, "3/5 — poster rasmini yuboring:", step_kb(skip=True))
    await state.set_state(SerialAdd.poster)


@router.message(SerialAdd.poster, F.photo | F.text)
async def add_poster(message: Message, state: FSMContext):
    poster = message.photo[-1].file_id if message.photo else None
    if poster is None and bosh(message.text) is not None:
        await ui.screen(message, state, "Rasm yuboring yoki o'tkazib yuboring:", step_kb(skip=True))
        return
    await state.update_data(yangi_poster=poster)
    await ui.screen(message, state, "4/5 — janrni yuboring:", step_kb(skip=True))
    await state.set_state(SerialAdd.janr)


@router.message(SerialAdd.janr, F.text)
async def add_janr(message: Message, state: FSMContext):
    await state.update_data(yangi_janr=bosh(message.text))
    await ui.screen(message, state, "5/5 — yilni yuboring:", step_kb(skip=True))
    await state.set_state(SerialAdd.yil)


@router.message(SerialAdd.yil, F.text)
async def add_yil(message: Message, state: FSMContext, bot: Bot):
    yil = bosh(message.text)
    if yil is not None and not yil.isdigit():
        await ui.screen(message, state, "Yilni raqam bilan yozing, masalan 2024:", step_kb(skip=True))
        return

    malumot = await state.get_data()
    serial_id = await db.add_serial(
        malumot["yangi_nom"],
        malumot.get("yangi_tavsif"),
        malumot.get("yangi_poster"),
        malumot.get("yangi_janr"),
        int(yil) if yil else None,
    )
    await state.set_state(None)
    if avtopost:
        fonda(avtopost.yangi_serial(bot, await db.get_serial(serial_id)))
    await ui.set_nav(state, "a_menu", nav_serial=serial_id)
    await ui.screen(
        message,
        state,
        f"✅ <b>{ui.esc(malumot['yangi_nom'])}</b> qo'shildi (id: {serial_id}).\n"
        f"Endi qism qo'shishingiz mumkin.",
        ui.kb([EP_ADD], [ui.ADMIN_BACK], [ui.HOME]),
    )


def bosh(matn: str | None) -> str | None:
    """O'tkazib yuborilgan qadam -> None."""
    matn = (matn or "").strip()
    return None if matn in {"", "-", SKIP} else matn


# ----------------------------------------------------- qism qo'shish

@router.message(F.text == EP_ADD)
async def eps_picker(message: Message, state: FSMContext):
    await show_picker(message, state, "eps")


@router.message(F.text.startswith(ui.SERIAL_PREFIX), ui.ekran("a_pick"))
async def picker_tanlov(message: Message, state: FSMContext):
    nom = message.text[len(ui.SERIAL_PREFIX):].strip()
    serial = await db.get_serial_by_name(nom)
    malumot = await state.get_data()
    if serial is None:
        await show_picker(message, state, malumot["nav_maqsad"])
        return
    if malumot["nav_maqsad"] == "eps":
        await eps_start(message, state, serial)
    else:
        await show_edit(message, state, serial["id"])


async def eps_start(message: Message, state: FSMContext, serial):
    keyingi = await db.next_episode_number(serial["id"])
    await ui.set_nav(state, "a_eps", nav_serial=serial["id"])
    await ui.screen(
        message,
        state,
        f"🎬 <b>{ui.esc(serial['nom'])}</b>\n\n"
        f"Arxiv kanaldan videolarni shu yerga <b>forward</b> qiling.\n"
        f"Keyingi qism raqami: <b>{keyingi}</b>. Bir nechta videoni ketma-ket yuborsangiz ham bo'ladi.",
        ui.kb([ui.DONE], [ui.HOME]),
    )
    await state.set_state(EpisodeAdd.forward)


def forward_manba(message: Message) -> tuple[int, int] | None:
    """Forward qilingan xabarning asl kanali va message_id si."""
    manba = getattr(message, "forward_origin", None)
    if manba is not None and getattr(manba, "chat", None) is not None:
        return manba.chat.id, manba.message_id
    if message.forward_from_chat is not None:
        return message.forward_from_chat.id, message.forward_from_message_id
    return None


@router.message(EpisodeAdd.forward)
async def eps_add(message: Message, state: FSMContext, bot: Bot):
    manba = forward_manba(message)
    if manba is None:
        await message.answer("Videoni <b>arxiv kanaldan forward</b> qiling (oddiy yuklash emas).")
        return

    kanal_id, msg_id = manba
    if kanal_id != ARCHIVE_CHANNEL_ID:
        await message.answer(
            f"⚠️ Bu xabar boshqa kanaldan: <code>{kanal_id}</code>\n"
            f".env dagi ARCHIVE_CHANNEL_ID esa <code>{ARCHIVE_CHANNEL_ID}</code>."
        )
        return

    malumot = await state.get_data()
    serial_id = malumot["nav_serial"]
    qism = await db.next_episode_number(serial_id)
    davomiyligi = message.video.duration if message.video else None
    nom = (message.caption or "").strip() or None
    await db.add_episode(serial_id, qism, nom, msg_id, davomiyligi)
    await message.answer(f"✅ <b>{qism}-qism</b> saqlandi. Keyingisini yuboravering.")

    serial = await db.get_serial(serial_id)
    if bildirishnoma:
        fonda(bildirishnoma.yangi_qism(bot, serial, qism))
    if avtopost:
        fonda(avtopost.yangi_qism(bot, serial, qism))


# ------------------------------------------------ tahrirlash / o'chirish

@router.message(F.text == EDIT)
async def edit_picker(message: Message, state: FSMContext):
    await show_picker(message, state, "edit")


async def show_edit(message: Message, state: FSMContext, serial_id: int):
    serial = await db.get_serial(serial_id)
    if serial is None:
        await show_picker(message, state, "edit")
        return
    qismlar = await db.count_episodes(serial_id)
    matn = (
        f"✏️ <b>{ui.esc(serial['nom'])}</b>\n"
        f"Janr: {ui.esc(serial['janr']) or '—'} · Yil: {serial['yil'] or '—'}\n"
        f"Qismlar: {qismlar}\n\n"
        f"{ui.esc(serial['tavsif']) or '<i>tavsif yo`q</i>'}"
    )
    await state.set_state(None)
    await ui.set_nav(state, "a_edit", nav_serial=serial_id)
    await ui.screen(
        message,
        state,
        matn,
        ui.kb(
            ["✏️ Nom", "✏️ Tavsif"],
            ["✏️ Janr", "✏️ Yil", "🖼 Poster"],
            [ui.HAVOLA],
            [DEL_EPISODES],
            [DEL_SERIAL],
            [ui.ADMIN_BACK, ui.HOME],
        ),
        serial["poster_file_id"],
    )


@router.message(F.text.in_(MAYDONLAR), ui.ekran("a_edit"))
async def edit_field(message: Message, state: FSMContext):
    maydon = MAYDONLAR[message.text]
    await state.update_data(tahrir_maydon=maydon)
    nima = "yangi poster rasmini" if maydon == "poster_file_id" else f"yangi <b>{maydon}</b> qiymatini"
    await ui.screen(message, state, f"✏️ {nima} yuboring:", step_kb())
    await state.set_state(SerialEdit.qiymat)


@router.message(SerialEdit.qiymat, F.text | F.photo)
async def edit_save(message: Message, state: FSMContext):
    malumot = await state.get_data()
    serial_id, maydon = malumot["nav_serial"], malumot["tahrir_maydon"]

    if maydon == "poster_file_id":
        if not message.photo:
            await ui.screen(message, state, "Rasm yuboring:", step_kb())
            return
        qiymat = message.photo[-1].file_id
    else:
        qiymat = message.text.strip()
        if maydon == "yil":
            if not qiymat.isdigit():
                await ui.screen(message, state, "Yilni raqam bilan yozing:", step_kb())
                return
            qiymat = int(qiymat)

    await db.update_serial(serial_id, maydon, qiymat)
    await show_edit(message, state, serial_id)


@router.message(F.text == ui.HAVOLA, ui.ekran("a_edit"))
async def havola(message: Message, state: FSMContext, bot: Bot):
    malumot = await state.get_data()
    serial_id = malumot["nav_serial"]
    serial = await db.get_serial(serial_id)
    if serial is None:
        await show_picker(message, state, "edit")
        return
    serial_havola = await ui.havola(bot, f"serial_{serial_id}")
    qism_havola = await ui.havola(bot, f"qism_{serial_id}_1")
    await ui.screen(
        message,
        state,
        f"🔗 <b>{ui.esc(serial['nom'])}</b> havolalari\n\n"
        f"Serial: <code>{serial_havola}</code>\n"
        f"1-qism: <code>{qism_havola}</code>\n\n"
        f"<i>Qism raqamini almashtirib istalgan qismga havola olasiz.</i>",
        ui.kb([ui.BACK], [ui.ADMIN_BACK, ui.HOME]),
    )


@router.message(F.text == ui.BACK, ui.ekran("a_edit"))
async def havoladan_orqaga(message: Message, state: FSMContext):
    malumot = await state.get_data()
    await show_edit(message, state, malumot["nav_serial"])


@router.message(F.text == DEL_SERIAL, ui.ekran("a_edit"))
async def delete_confirm(message: Message, state: FSMContext):
    malumot = await state.get_data()
    serial = await db.get_serial(malumot["nav_serial"])
    if serial is None:
        await show_picker(message, state, "edit")
        return
    await ui.set_nav(state, "a_del", nav_serial=serial["id"])
    await ui.screen(
        message,
        state,
        f"🗑 <b>{ui.esc(serial['nom'])}</b> va uning barcha qismlari o'chiriladi. Davom etamizmi?",
        ui.kb([DEL_YES], [DEL_NO], [ui.HOME]),
    )


@router.message(F.text == DEL_YES, ui.ekran("a_del"))
async def delete_serial(message: Message, state: FSMContext):
    malumot = await state.get_data()
    await db.delete_serial(malumot["nav_serial"])
    await show_picker(message, state, "edit")


@router.message(F.text == DEL_NO, ui.ekran("a_del"))
async def delete_cancel(message: Message, state: FSMContext):
    malumot = await state.get_data()
    await show_edit(message, state, malumot["nav_serial"])


async def show_episode_delete(message: Message, state: FSMContext, serial_id: int, page: int = 0):
    jami = await db.count_episodes(serial_id)
    episodes = await db.list_episodes(serial_id, page * EPISODES_PER_PAGE, EPISODES_PER_PAGE)
    await ui.set_nav(state, "a_epdel", nav_serial=serial_id, nav_page=page)
    await ui.screen(
        message,
        state,
        "🗑 O'chirish uchun qism raqamini bosing." if jami else "📭 Qismlar yo'q.",
        ui.kb(
            *ui.rows([f"{ui.OCHIR_PREFIX}{e['qism_raqami']}" for e in episodes], 4),
            ui.page_row(page, jami, EPISODES_PER_PAGE),
            [ui.BACK, ui.HOME],
        ),
    )


@router.message(F.text == DEL_EPISODES, ui.ekran("a_edit"))
async def episode_delete_list(message: Message, state: FSMContext):
    malumot = await state.get_data()
    await show_episode_delete(message, state, malumot["nav_serial"])


@router.message(F.text == ui.BACK, ui.ekran("a_epdel"))
async def episode_delete_back(message: Message, state: FSMContext):
    malumot = await state.get_data()
    await show_edit(message, state, malumot["nav_serial"])


@router.message(F.text.regexp(r"^🗑 \d+$"), ui.ekran("a_epdel"))
async def episode_delete(message: Message, state: FSMContext):
    malumot = await state.get_data()
    serial_id, page = malumot["nav_serial"], malumot.get("nav_page", 0)
    qism = int(message.text[len(ui.OCHIR_PREFIX):])
    episode = await db.get_episode(serial_id, qism)
    if episode is not None:
        await db.delete_episode(episode["id"])
    await show_episode_delete(message, state, serial_id, page)


# -------------------------------------------------------- statistika

@router.message(F.text == STAT)
async def statistika(message: Message, state: FSMContext):
    qatorlar = [
        "📊 <b>Statistika</b>",
        "",
        f"👥 Foydalanuvchilar: <b>{await db.count_users()}</b>",
        f"🔥 Bugun faol: <b>{await db.count_active_today()}</b>",
        f"🚫 Bloklagan: <b>{await db.count_users() - await db.count_faol()}</b>",
        f"🎬 Seriallar: <b>{await db.count_serials()}</b>",
        "",
        "<b>Top 10 ko'rilgan:</b>",
    ]
    top = await db.top_serials(10)
    if top:
        qatorlar += [f"{i}. {ui.esc(r['nom'])} — {r['tomoshabin']}" for i, r in enumerate(top, 1)]
    else:
        qatorlar.append("<i>hozircha ma'lumot yo'q</i>")

    await ui.set_nav(state, "a_stat")
    await ui.screen(message, state, "\n".join(qatorlar), ui.kb([ui.ADMIN_BACK], [ui.HOME]))


# ---------------------------------------------------------- tarqatish

@router.message(F.text == BC)
async def broadcast_start(message: Message, state: FSMContext):
    await ui.set_nav(state, "a_bc")
    await ui.screen(
        message,
        state,
        "📨 Tarqatiladigan xabarni yuboring (matn, rasm, video — nusxasi jo'natiladi).",
        step_kb(),
    )
    await state.set_state(Broadcast.xabar)


@router.message(Broadcast.xabar)
async def broadcast_preview(message: Message, state: FSMContext):
    await state.update_data(bc_chat=message.chat.id, bc_msg=message.message_id)
    jami = await db.count_users()
    await ui.set_nav(state, "a_bc")
    await ui.screen(
        message,
        state,
        f"👆 Shu xabar <b>{jami}</b> ta foydalanuvchiga yuboriladi. Tasdiqlaysizmi?",
        ui.kb([BC_SEND], [ui.CANCEL], [ui.HOME]),
    )
    await state.set_state(None)


@router.message(F.text == BC_SEND, ui.ekran("a_bc"))
async def broadcast_send(message: Message, state: FSMContext, bot: Bot):
    malumot = await state.get_data()
    if "bc_msg" not in malumot:
        await show_menu(message, state)
        return

    await ui.screen(message, state, "📨 Tarqatilmoqda…", ui.kb([ui.HOME]))

    users = await db.all_user_ids()
    yuborildi = bloklangan = xato = 0
    for i in range(0, len(users), BROADCAST_CHUNK):
        for user_id in users[i : i + BROADCAST_CHUNK]:
            try:
                await bot.copy_message(user_id, malumot["bc_chat"], malumot["bc_msg"])
                yuborildi += 1
            except TelegramForbiddenError:
                bloklangan += 1
                await db.faol_belgila(user_id, False)
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
                try:
                    await bot.copy_message(user_id, malumot["bc_chat"], malumot["bc_msg"])
                    yuborildi += 1
                except TelegramAPIError:
                    xato += 1
            except TelegramAPIError:
                xato += 1
            await asyncio.sleep(0.05)
        await asyncio.sleep(BROADCAST_PAUSE)

    await ui.set_nav(state, "a_menu")
    await ui.screen(
        message,
        state,
        f"📨 <b>Tarqatish tugadi</b>\n"
        f"✅ Yuborildi: {yuborildi}\n"
        f"🚫 Bloklagan: {bloklangan}\n"
        f"⚠️ Xato: {xato}",
        menu_kb(),
    )


# ---------------------------------------------------------- murojatlar

@router.message(F.text == MUR)
async def murojatlar(message: Message, state: FSMContext):
    royxat = await db.unanswered_murojat()
    tugmalar = [[f"#{m['id']} · {m['matn'][:28]}".replace("\n", " ")] for m in royxat]
    await ui.set_nav(state, "a_mur")
    await ui.screen(
        message,
        state,
        "💬 <b>Javob berilmagan murojatlar</b>" if royxat else "✅ Javob berilmagan murojaat yo'q.",
        ui.kb(*tugmalar, [ui.ADMIN_BACK, ui.HOME]),
    )


def murojat_tugmasi(message: Message) -> dict | bool:
    """"#12 · matn" tugmasidan murojaat id sini ajratadi."""
    topildi = re.match(r"^#(\d+)", message.text or "")
    return {"murojat_id": int(topildi.group(1))} if topildi else False


@router.message(murojat_tugmasi, ui.ekran("a_mur"))
async def murojat_detail(message: Message, state: FSMContext, murojat_id: int):
    m = await db.get_murojat(murojat_id)
    if m is None:
        await murojatlar(message, state)
        return
    await ui.set_nav(state, "a_mur")
    await ui.screen(
        message,
        state,
        f"📩 <b>Murojaat</b> #m{m['id']}\n"
        f"👤 <code>{m['user_id']}</code> · {ui.esc(m['created_at'])}\n\n"
        f"{ui.esc(m['matn'])}\n\n"
        f"<i>Javob berish uchun shu xabarga reply qiling.</i>",
        ui.kb([MUR], [ui.ADMIN_BACK, ui.HOME]),
    )
