"""Bot kirish nuqtasi."""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import db
from config import BOT_TOKEN, FEATURE_TAKLIF, FEATURE_YUKLASH
from handlers import admin, kino, murojat, qidiruv
from middlewares import ActivityMiddleware

# Yangi modul qo'shish: handlers/ ga fayl yarating, unda `router = Router(...)`
# e'lon qiling va shu ro'yxatga bitta qator qo'shing.
# Tartib muhim: tugmalar oddiy matn bo'lgani uchun admin birinchi turadi
# (uning ekranlari o'z tugmalarini oladi), qidiruv esa eng oxirida —
# u boshqa hech kim olmagan matnni o'ziga oladi.
ROUTERS = [admin]

# Bayroq o'chiq bo'lsa modul import ham qilinmaydi (og'ir bog'liqliklar yuklanmasin)
if FEATURE_YUKLASH:
    from handlers import yuklash

    ROUTERS.append(yuklash)
if FEATURE_TAKLIF:
    from handlers import taklif

    ROUTERS.append(taklif)

ROUTERS += [kino, murojat, qidiruv]


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    await db.init_db()

    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.outer_middleware(ActivityMiddleware())
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
