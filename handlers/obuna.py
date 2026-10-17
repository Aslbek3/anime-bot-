"""Majburiy obuna (FEATURE_OBUNA).

.env dagi OBUNA_KANALLAR ro'yxatidagi kanallarga a'zo bo'lmagan
foydalanuvchi botdan foydalana olmaydi. Tekshiruv middleware da,
"✅ Tekshirish" tugmasi esa shu moduldagi routerda.

Middleware `main.py` da dp.update.outer_middleware() ga qo'yiladi,
shuning uchun hamma routerlardan oldin ishlaydi.
"""
import logging
import time

from aiogram import BaseMiddleware, Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, TelegramObject, User

import ui
from config import ADMIN_ID, OBUNA_KANALLAR, OBUNA_KESH
from handlers.kino import show_main

router = Router(name="obuna")
log = logging.getLogger(__name__)

AZO_HOLATLAR = {"member", "administrator", "creator"}
_kesh: dict[int, tuple[float, bool]] = {}   # user_id -> (vaqt, a'zomi)


async def azomi(bot: Bot, user_id: int, keshsiz: bool = False) -> bool:
    """Barcha kanallarga a'zomi. Tekshirib bo'lmasa — o'tkazib yuboramiz."""
    yozuv = _kesh.get(user_id)
    if not keshsiz and yozuv and time.time() - yozuv[0] < OBUNA_KESH:
        return yozuv[1]

    natija = True
    for kanal in OBUNA_KANALLAR:
        try:
            azo = await bot.get_chat_member(kanal, user_id)
        except TelegramAPIError as xato:
            # bot kanalda admin emas / kanal topilmadi — hammani bloklab qo'ymaymiz
            log.warning("obuna tekshirilmadi (%s): %s", kanal, xato)
            continue
        if azo.status not in AZO_HOLATLAR:
            natija = False
            break

    _kesh[user_id] = (time.time(), natija)
    return natija


def kanal_havolasi(kanal: str) -> str:
    return f"https://t.me/{kanal.lstrip('@')}" if not kanal.startswith("-") else kanal


def sorov_matni() -> str:
    qatorlar = ["🔒 Botdan foydalanish uchun quyidagi kanal(lar)ga a'zo bo'ling:", ""]
    qatorlar += [f"👉 {kanal_havolasi(k)}" for k in OBUNA_KANALLAR]
    qatorlar += ["", "A'zo bo'lgach <b>✅ Tekshirish</b> tugmasini bosing."]
    return "\n".join(qatorlar)


class ObunaMiddleware(BaseMiddleware):
    """A'zo bo'lmaganni handlerlargacha qo'ymaydi."""

    async def __call__(self, handler, event: TelegramObject, data: dict):
        user: User | None = data.get("event_from_user")
        bot: Bot = data["bot"]
        if user is None or user.id == ADMIN_ID or not OBUNA_KANALLAR:
            return await handler(event, data)

        xabar = getattr(event, "message", None)
        matn = (getattr(xabar, "text", None) or "") if xabar else ""
        tekshirish = matn == ui.TEKSHIRISH

        if await azomi(bot, user.id, keshsiz=tekshirish):
            return await handler(event, data)

        await bot.send_message(
            user.id,
            sorov_matni(),
            disable_web_page_preview=True,
            reply_markup=ui.kb([ui.TEKSHIRISH]),
        )
        return None   # update shu yerda to'xtaydi


@router.message(F.text == ui.TEKSHIRISH)
async def tekshirildi(message: Message, state: FSMContext):
    # Bu yerga faqat a'zolik tasdiqlangandan keyin kelinadi
    await message.answer("✅ Rahmat! Endi botdan foydalanishingiz mumkin.")
    await show_main(message, state)
