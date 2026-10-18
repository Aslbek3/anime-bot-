"""Qidiruv jurnali (FEATURE_QIDIRUV_JURNALI).

Har bir qidiruv yoziladi; admin panelidagi "🔎 So'ralganlar" bo'limida
topilmagan so'rovlar eng ko'p so'ralgani bo'yicha ko'rsatiladi — bu
to'g'ridan-to'g'ri kontent rejasi bo'lib xizmat qiladi.
Yozishni `handlers/qidiruv.py` chaqiradi.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
import ui
from middlewares import AdminOnly

router = Router(name="qidiruv_jurnali")
router.message.outer_middleware(AdminOnly())


async def yoz(soz: str, user_id: int, topildi: bool) -> None:
    await db.qidiruv_yoz(soz, user_id, topildi)


@router.message(F.text == ui.QIDIRUV_JURNALI)
async def royxat(message: Message, state: FSMContext):
    topilmagan = await db.topilmaganlar()
    mashhur = await db.mashhur_qidiruvlar(5)

    qatorlar = ["🔎 <b>So'ralgan, lekin topilmagan</b>", ""]
    if topilmagan:
        qatorlar += [f"{r['soni']}× — <b>{ui.esc(r['soz'])}</b>" for r in topilmagan]
    else:
        qatorlar.append("<i>hammasi topilgan</i>")
    if mashhur:
        qatorlar += ["", "<b>Eng ko'p qidirilganlar:</b>"]
        qatorlar += [f"{r['soni']}× — {ui.esc(r['soz'])}" for r in mashhur]

    await ui.set_nav(state, "a_qidiruv_jurnali")
    await ui.screen(message, state, "\n".join(qatorlar), ui.kb([ui.ADMIN_BACK], [ui.HOME]))
