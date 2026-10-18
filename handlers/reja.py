"""Rejalashtirilgan tarqatish (FEATURE_REJA).

Admin xabarni yuboradi, vaqtini yozadi ("2026-10-18 20:00" yoki "20:00"),
bot o'sha vaqtda hammaga tarqatadi. Fon vazifasi har 30 soniyada
vaqti kelgan rejalarni tekshiradi.
"""
import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

import db
import ui
from config import BROADCAST_CHUNK, BROADCAST_PAUSE
from middlewares import AdminOnly

router = Router(name="reja")
router.message.outer_middleware(AdminOnly())
log = logging.getLogger(__name__)

TEKSHIRISH_ORALIGI = 30
_ishchi: asyncio.Task | None = None


class Reja(StatesGroup):
    xabar = State()
    vaqt = State()


def vaqtni_oqi(matn: str) -> str | None:
    """"2026-10-18 20:00" yoki "20:00" -> bazaga yoziladigan satr."""
    matn = matn.strip()
    for naqsh in ("%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M"):
        try:
            return datetime.strptime(matn, naqsh).strftime("%Y-%m-%d %H:%M:00")
        except ValueError:
            continue
    try:
        soat = datetime.strptime(matn, "%H:%M").time()
    except ValueError:
        return None
    endi = datetime.now()
    nishon = endi.replace(hour=soat.hour, minute=soat.minute, second=0, microsecond=0)
    if nishon <= endi:
        nishon += timedelta(days=1)       # vaqt o'tib ketgan bo'lsa — ertaga
    return nishon.strftime("%Y-%m-%d %H:%M:00")


@router.message(F.text == ui.REJA)
async def royxat(message: Message, state: FSMContext):
    kutayotganlar = await db.rejalar()
    qatorlar = ["⏰ <b>Rejalashtirilgan tarqatishlar</b>", ""]
    if kutayotganlar:
        qatorlar += [f"#{r['id']} — {r['vaqt']}" for r in kutayotganlar]
    else:
        qatorlar.append("<i>reja yo'q</i>")
    await state.set_state(None)
    await ui.set_nav(state, "a_reja")
    await ui.screen(
        message, state, "\n".join(qatorlar), ui.kb([ui.REJA_YANGI], [ui.ADMIN_BACK], [ui.HOME])
    )


@router.message(F.text == ui.REJA_YANGI)
async def yangi(message: Message, state: FSMContext):
    await ui.set_nav(state, "a_reja")
    await ui.screen(
        message, state, "⏰ Tarqatiladigan xabarni yuboring:", ui.kb([ui.CANCEL], [ui.HOME])
    )
    await state.set_state(Reja.xabar)


@router.message(Reja.xabar)
async def xabar_qabul(message: Message, state: FSMContext):
    await state.update_data(reja_chat=message.chat.id, reja_msg=message.message_id)
    await ui.screen(
        message,
        state,
        "⏰ Qachon yuboray?\n<code>2026-10-18 20:00</code> yoki faqat <code>20:00</code>",
        ui.kb([ui.CANCEL], [ui.HOME]),
    )
    await state.set_state(Reja.vaqt)


@router.message(Reja.vaqt, F.text)
async def vaqt_qabul(message: Message, state: FSMContext):
    vaqt = vaqtni_oqi(message.text)
    if vaqt is None:
        await ui.screen(message, state, "⚠️ Vaqt tushunarsiz. Masalan: <code>20:00</code>", ui.kb([ui.CANCEL], [ui.HOME]))
        return
    malumot = await state.get_data()
    reja_id = await db.reja_qosh(malumot["reja_chat"], malumot["reja_msg"], vaqt)
    await state.set_state(None)
    await ui.screen(
        message,
        state,
        f"✅ Reja #{reja_id} saqlandi: <b>{vaqt}</b> da yuboriladi.",
        ui.kb([ui.REJA], [ui.ADMIN_BACK], [ui.HOME]),
    )


async def bajarish(bot: Bot, reja) -> None:
    users = await db.all_user_ids()
    yuborildi = bloklangan = xato = 0
    for i in range(0, len(users), BROADCAST_CHUNK):
        for user_id in users[i : i + BROADCAST_CHUNK]:
            try:
                await bot.copy_message(user_id, reja["chat_id"], reja["message_id"])
                yuborildi += 1
            except TelegramForbiddenError:
                bloklangan += 1
                await db.faol_belgila(user_id, False)
            except TelegramAPIError:
                xato += 1
            await asyncio.sleep(0.05)
        await asyncio.sleep(BROADCAST_PAUSE)

    natija = f"✅ {yuborildi} · 🚫 {bloklangan} · ⚠️ {xato}"
    await db.reja_holat(reja["id"], "yuborildi", natija)
    await bot.send_message(reja["chat_id"], f"⏰ Reja #{reja['id']} bajarildi\n{natija}")


async def _halqa(bot: Bot) -> None:
    while True:
        try:
            for reja in await db.reja_yetganlar():
                log.info("reja bajarilmoqda: #%s", reja["id"])
                await bajarish(bot, reja)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("reja ishchisida xato")
        await asyncio.sleep(TEKSHIRISH_ORALIGI)


@router.startup()
async def ishga_tushir(bot: Bot, **_) -> None:
    global _ishchi
    _ishchi = asyncio.create_task(_halqa(bot))
    log.info("reja moduli yoqildi")


@router.shutdown()
async def to_xtatish(**_) -> None:
    if _ishchi is not None:
        _ishchi.cancel()
