"""Manba kuzatuvi (FEATURE_MANBA).

`t.me/<bot>?start=ref_instagram` ko'rinishidagi havolalar qayerdan
kelganini sanaydi. Yozishni `handlers/kino.py` dagi deeplink handleri
chaqiradi, statistikani admin panelidagi "📈 Manbalar" ko'rsatadi.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
import ui
from middlewares import AdminOnly

router = Router(name="manba")
router.message.outer_middleware(AdminOnly())

PREFIKS = "ref_"


async def yoz(payload: str, user_id: int) -> bool:
    """`ref_<manba>` bo'lsa yozib qo'yadi."""
    if not payload.startswith(PREFIKS):
        return False
    manba = payload[len(PREFIKS):].strip()[:64]
    if manba:
        await db.manba_yoz(manba, user_id)
    return True


@router.message(F.text == ui.MANBALAR)
async def statistika(message: Message, state: FSMContext):
    satrlar = await db.manba_statistika()
    qatorlar = ["📈 <b>Manbalar</b>", "", "Havola: <code>?start=ref_&lt;manba&gt;</code>", ""]
    if satrlar:
        qatorlar += [
            f"{r['manba']} — {r['soni']} o'tish, {r['odamlar']} kishi" for r in satrlar
        ]
    else:
        qatorlar.append("<i>hali o'tishlar yo'q</i>")
    await ui.set_nav(state, "a_manba")
    await ui.screen(message, state, "\n".join(qatorlar), ui.kb([ui.ADMIN_BACK], [ui.HOME]))
