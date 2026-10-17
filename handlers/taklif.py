"""Foydalanuvchi takliflari moduli (FEATURE_TAKLIF).

User yangi kino/serial taklif qiladi -> yozuv `serials` jadvaliga
holat='kutilmoqda' bilan tushadi (yangi jadval kerak emas) -> admin
tasdiqlagach holat='tasdiqlangan' bo'ladi va ro'yxatda ko'rina boshlaydi.

Routerning user qismi hamma uchun, admin qismi ichki routerda —
AdminOnly middleware bilan yopilgan.
"""
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

import db
import ui
from config import ADMIN_ID, TAKLIF_KUNLIK_LIMIT
from handlers.kino import show_main
from middlewares import AdminOnly

router = Router(name="taklif")
admin_router = Router(name="taklif_admin")
admin_router.message.outer_middleware(AdminOnly())
router.include_router(admin_router)

log = logging.getLogger(__name__)


class Taklif(StatesGroup):
    nom = State()
    tavsif = State()
    manba = State()


def qadam_kb():
    return ui.kb([ui.SKIP], [ui.CANCEL], [ui.HOME])


# ------------------------------------------------------- user tomoni

# Bekor qilish FSM qadamlaridan oldin turadi, aks holda tugma matni
# taklif nomi bo'lib yozilib qolardi.
@router.message(F.text.in_({ui.CANCEL, ui.HOME}))
async def bekor(message: Message, state: FSMContext):
    await show_main(message, state)


@router.message(F.text == ui.TAKLIF_QIL)
async def boshlash(message: Message, state: FSMContext):
    bugun = await db.bugungi_takliflar(message.from_user.id)
    if bugun >= TAKLIF_KUNLIK_LIMIT:
        await ui.screen(
            message,
            state,
            f"⏳ Kuniga {TAKLIF_KUNLIK_LIMIT} tadan ortiq taklif yuborib bo'lmaydi.\n"
            "Ertaga yana urinib ko'ring.",
            ui.kb([ui.HOME]),
        )
        return
    await ui.set_nav(state, "taklif")
    await ui.screen(
        message,
        state,
        "➕ <b>Kino taklif qilish</b>\n\n1/3 — kino yoki serial nomini yozing:",
        ui.kb([ui.CANCEL], [ui.HOME]),
    )
    await state.set_state(Taklif.nom)


@router.message(Taklif.nom, F.text)
async def nom_qabul(message: Message, state: FSMContext):
    await state.update_data(taklif_nom=message.text.strip())
    await ui.screen(message, state, "2/3 — qisqacha tavsif (ixtiyoriy):", qadam_kb())
    await state.set_state(Taklif.tavsif)


@router.message(Taklif.tavsif, F.text)
async def tavsif_qabul(message: Message, state: FSMContext):
    await state.update_data(taklif_tavsif=ixtiyoriy(message.text))
    await ui.screen(message, state, "3/3 — link yoki izoh (ixtiyoriy):", qadam_kb())
    await state.set_state(Taklif.manba)


@router.message(Taklif.manba, F.text)
async def saqlash(message: Message, state: FSMContext, bot: Bot):
    malumot = await state.get_data()
    manba = ixtiyoriy(message.text)
    await state.set_state(None)

    bugun = await db.bugungi_takliflar(message.from_user.id)
    if bugun >= TAKLIF_KUNLIK_LIMIT:
        await ui.screen(message, state, "⏳ Kunlik limit tugadi, ertaga urinib ko'ring.", ui.kb([ui.HOME]))
        return

    nom = malumot["taklif_nom"]
    serial_id = await db.taklif_qosh(nom, malumot.get("taklif_tavsif"), manba, message.from_user.id)

    user = message.from_user
    kim = f'<a href="tg://user?id={user.id}">{ui.esc(user.full_name)}</a>'
    if user.username:
        kim += f" (@{user.username})"
    await bot.send_message(
        ADMIN_ID,
        f"📥 <b>Yangi taklif</b> #{serial_id}\n"
        f"👤 {kim}\n\n"
        f"🎬 {ui.esc(nom)}\n"
        f"{ui.esc(malumot.get('taklif_tavsif')) or '<i>tavsifsiz</i>'}\n"
        f"{ui.esc(manba) or ''}\n\n"
        f"<i>Admin panel → {ui.TAKLIFLAR}</i>",
    )
    await ui.screen(
        message,
        state,
        f"✅ <b>{ui.esc(nom)}</b> taklifingiz qabul qilindi.\n"
        "Admin ko'rib chiqqach xabar beraman.",
        ui.kb([ui.HOME]),
    )


def ixtiyoriy(matn: str | None) -> str | None:
    matn = (matn or "").strip()
    return None if matn in {"", "-", ui.SKIP} else matn


# ------------------------------------------------------ admin tomoni

@admin_router.message(F.text == ui.TAKLIFLAR)
async def royxat(message: Message, state: FSMContext):
    kutayotganlar = await db.takliflar()
    tugmalar = [[f"#{t['id']} · {t['nom'][:28]}"] for t in kutayotganlar]
    await ui.set_nav(state, "t_list")
    await ui.screen(
        message,
        state,
        "📥 <b>Kutilayotgan takliflar</b>" if kutayotganlar else "✅ Yangi taklif yo'q.",
        ui.kb(*tugmalar, [ui.ADMIN_BACK, ui.HOME]),
    )


def taklif_tugmasi(message: Message) -> dict | bool:
    """"#12 · nom" tugmasidan taklif id sini ajratadi."""
    matn = (message.text or "").lstrip("#")
    raqam = matn.split(" ")[0]
    return {"taklif_id": int(raqam)} if message.text.startswith("#") and raqam.isdigit() else False


@admin_router.message(taklif_tugmasi, ui.ekran("t_list"))
async def tafsilot(message: Message, state: FSMContext, taklif_id: int):
    taklif = await db.get_serial(taklif_id)
    if taklif is None or taklif["holat"] != "kutilmoqda":
        await royxat(message, state)
        return
    muallif = await db.get_user(taklif["qoshgan_user_id"]) if taklif["qoshgan_user_id"] else None
    await ui.set_nav(state, "t_item", nav_taklif=taklif_id)
    await ui.screen(
        message,
        state,
        f"📥 <b>Taklif</b> #{taklif_id}\n"
        f"👤 {ui.esc(kim_nomi(muallif))}\n\n"
        f"🎬 <b>{ui.esc(taklif['nom'])}</b>\n"
        f"{ui.esc(taklif['tavsif']) or '<i>tavsifsiz</i>'}\n"
        f"{ui.esc(taklif['manba_url']) or ''}",
        ui.kb([ui.TASDIQLASH, ui.RAD_ETISH], [ui.BACK], [ui.HOME]),
    )


@admin_router.message(F.text == ui.BACK, ui.ekran("t_item"))
async def orqaga(message: Message, state: FSMContext):
    await royxat(message, state)


@admin_router.message(F.text == ui.TASDIQLASH, ui.ekran("t_item"))
async def tasdiqlash(message: Message, state: FSMContext, bot: Bot):
    malumot = await state.get_data()
    taklif = await db.get_serial(malumot["nav_taklif"])
    if taklif is None:
        await royxat(message, state)
        return
    await db.taklif_tasdiqla(taklif["id"])
    await xabar_ber(bot, taklif, f"✅ <b>{ui.esc(taklif['nom'])}</b> taklifingiz qabul qilindi, rahmat!")
    await royxat(message, state)


@admin_router.message(F.text == ui.RAD_ETISH, ui.ekran("t_item"))
async def rad_etish(message: Message, state: FSMContext, bot: Bot):
    malumot = await state.get_data()
    taklif = await db.get_serial(malumot["nav_taklif"])
    if taklif is None:
        await royxat(message, state)
        return
    await db.taklif_rad(taklif["id"])
    await xabar_ber(bot, taklif, f"❌ <b>{ui.esc(taklif['nom'])}</b> taklifingiz qabul qilinmadi.")
    await royxat(message, state)


async def xabar_ber(bot: Bot, taklif, matn: str) -> None:
    """Taklif egasiga natijani yetkazadi (bloklagan bo'lsa jim o'tamiz)."""
    if not taklif["qoshgan_user_id"]:
        return
    try:
        await bot.send_message(taklif["qoshgan_user_id"], matn)
    except Exception as xato:
        log.info("taklif egasiga xabar yetmadi: %s", xato)


def kim_nomi(user) -> str:
    if user is None:
        return "noma'lum"
    if user["username"]:
        return f"@{user['username']}"
    return user["ism"] or str(user["user_id"])
