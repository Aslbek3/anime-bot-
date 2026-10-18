"""Bot kirish nuqtasi."""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import db
from config import (
    BOT_TOKEN,
    FEATURE_ANTIFLOOD,
    FEATURE_BAHO,
    FEATURE_BUYRUQLAR,
    FEATURE_CSV,
    FEATURE_FASL,
    FEATURE_INLINE,
    FEATURE_JURNAL,
    FEATURE_KANAL_IMPORT,
    FEATURE_KASHFIYOT,
    FEATURE_KUZATISH,
    FEATURE_MANBA,
    FEATURE_QIDIRUV_JURNALI,
    FEATURE_QISM_ALMASH,
    FEATURE_REJA,
    FEATURE_SQLITE_FSM,
    FEATURE_TIL,
    FEATURE_TUR,
    FEATURE_ULASHISH,
    FEATURE_JANR,
    FEATURE_OBUNA,
    FEATURE_RAQAM,
    FEATURE_ROYXATIM,
    FEATURE_TAKLIF,
    FEATURE_ULASHISH,
    FEATURE_YUKLASH,
    FEATURE_ZAXIRA,
)
from handlers import admin, kino, murojat, qidiruv
from middlewares import ActivityMiddleware, AntifloodMiddleware

# Yangi modul qo'shish: handlers/ ga fayl yarating, unda `router = Router(...)`
# e'lon qiling va shu ro'yxatga bitta qator qo'shing.
# Tartib muhim: tugmalar oddiy matn bo'lgani uchun admin birinchi turadi
# (uning ekranlari o'z tugmalarini oladi), qidiruv esa eng oxirida —
# u boshqa hech kim olmagan matnni o'ziga oladi.
# Bayroq o'chiq bo'lsa modul import ham qilinmaydi (og'ir bog'liqliklar yuklanmasin).
# Tartib: obuna -> admin va admin modullari -> user modullari -> kino -> qidiruv.
ROUTERS = []

if FEATURE_OBUNA:
    from handlers import obuna

    ROUTERS.append(obuna)          # "✅ Tekshirish" tugmasi hammadan oldin

ROUTERS.append(admin)

if FEATURE_YUKLASH:
    from handlers import yuklash

    ROUTERS.append(yuklash)
if FEATURE_TAKLIF:
    from handlers import taklif

    ROUTERS.append(taklif)
if FEATURE_QISM_ALMASH:
    from handlers import qism_almash

    ROUTERS.append(qism_almash)    # admin dan keyin: "a_pick" ekranini bo'lishadi
if FEATURE_QIDIRUV_JURNALI:
    from handlers import qidiruv_jurnali

    ROUTERS.append(qidiruv_jurnali)
if FEATURE_MANBA:
    from handlers import manba

    ROUTERS.append(manba)
if FEATURE_REJA:
    from handlers import reja

    ROUTERS.append(reja)
if FEATURE_CSV:
    from handlers import csv_almash

    ROUTERS.append(csv_almash)
if FEATURE_KANAL_IMPORT:
    from handlers import kanal_import

    ROUTERS.append(kanal_import)   # kanal postlarini ushlaydi
if FEATURE_JANR:
    from handlers import janrlar

    ROUTERS.append(janrlar)
if FEATURE_ULASHISH:
    from handlers import ulashish

    ROUTERS.append(ulashish)
if FEATURE_KUZATISH:
    from handlers import kuzatish

    ROUTERS.append(kuzatish)
if FEATURE_BAHO:
    from handlers import baho

    ROUTERS.append(baho)
if FEATURE_FASL:
    from handlers import fasl

    ROUTERS.append(fasl)
if FEATURE_KASHFIYOT:
    from handlers import kashfiyot

    ROUTERS.append(kashfiyot)
if FEATURE_TUR:
    from handlers import tur

    ROUTERS.append(tur)
if FEATURE_TIL:
    from handlers import til

    ROUTERS.append(til)
if FEATURE_INLINE:
    from handlers import inline

    ROUTERS.append(inline)
if FEATURE_JURNAL:
    from handlers import jurnal

    ROUTERS.append(jurnal)         # xatolarni tutadi
if FEATURE_BUYRUQLAR:
    from handlers import buyruqlar

    ROUTERS.append(buyruqlar)      # faqat startup ilgagi

ROUTERS.append(kino)

if FEATURE_ROYXATIM:
    from handlers import royxatim

    ROUTERS.append(royxatim)       # kino dan keyin: "▶️ Davom ettirish" uniki emas
if FEATURE_RAQAM:
    from handlers import qism_raqam

    ROUTERS.append(qism_raqam)     # qidiruvdan oldin: sof raqamni ushlaydi
if FEATURE_ZAXIRA:
    from handlers import zaxira

    ROUTERS.append(zaxira)         # handlersiz, faqat startup ilgagi uchun

ROUTERS += [murojat, qidiruv]


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    await db.init_db()

    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    saqlagich = MemoryStorage()
    if FEATURE_SQLITE_FSM:
        from storage import SQLiteStorage

        saqlagich = SQLiteStorage()   # restartdan keyin ham kontekst saqlanadi
    dp = Dispatcher(storage=saqlagich)
    if FEATURE_ANTIFLOOD:
        dp.update.outer_middleware(AntifloodMiddleware())
    dp.update.outer_middleware(ActivityMiddleware())
    if FEATURE_OBUNA:
        dp.update.outer_middleware(obuna.ObunaMiddleware())
    for modul in ROUTERS:
        dp.include_router(modul.router)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await db.close_db()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi")
