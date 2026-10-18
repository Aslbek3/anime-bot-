"""Xatolar va hodisalar jurnali (FEATURE_JURNAL).

- Botdagi har qanday ushlanmagan xato log kanaliga (yoki adminga) tushadi,
  foydalanuvchi esa chiroyli xabar ko'radi.
- Muhim hodisalarni (`hodisa()`) boshqa modullar ham yozishi mumkin.
"""
import html
import logging
import traceback

from aiogram import Bot, Router
from aiogram.types import ErrorEvent

from config import ADMIN_ID, LOG_CHANNEL_ID

router = Router(name="jurnal")
log = logging.getLogger(__name__)

QAYERGA = LOG_CHANNEL_ID or ADMIN_ID
USERGA = "⚠️ Kutilmagan xatolik yuz berdi. Admin xabardor qilindi, /start bilan qaytadan urinib ko'ring."


async def hodisa(bot: Bot, matn: str) -> None:
    """Muhim hodisani jurnalga yozadi (xato bo'lsa jimgina o'tadi)."""
    try:
        await bot.send_message(QAYERGA, matn, disable_web_page_preview=True)
    except Exception as xato:
        log.warning("jurnalga yozilmadi: %s", xato)


@router.errors()
async def tutuvchi(hodisa_obj: ErrorEvent, bot: Bot) -> bool:
    xato = hodisa_obj.exception
    log.exception("ushlanmagan xato", exc_info=xato)

    izoh = "".join(traceback.format_exception(type(xato), xato, xato.__traceback__))[-2500:]
    xabar = getattr(hodisa_obj.update, "message", None)
    kim = xabar.from_user.id if xabar and xabar.from_user else "—"
    matn = xabar.text if xabar else "—"

    await hodisa(
        bot,
        f"🔥 <b>Xato</b>: {html.escape(type(xato).__name__)}\n"
        f"👤 <code>{kim}</code> · <code>{html.escape(str(matn))[:100]}</code>\n\n"
        f"<pre>{html.escape(izoh)}</pre>",
    )

    if xabar is not None:
        try:
            await xabar.answer(USERGA)
        except Exception:
            pass
    return True
