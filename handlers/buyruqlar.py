"""Telegram "/" menyusi (FEATURE_BUYRUQLAR).

Startupda setMyCommands chaqiriladi: oddiy foydalanuvchiga umumiy buyruqlar,
adminga qo'shimcha /admin. Klaviaturaga tegmaydi.
"""
import logging

from aiogram import Bot, Router
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from config import ADMIN_IDS

router = Router(name="buyruqlar")
log = logging.getLogger(__name__)

UMUMIY = [
    BotCommand(command="start", description="Asosiy menyu"),
    BotCommand(command="murojat", description="Adminga yozish"),
]

ADMIN = UMUMIY + [BotCommand(command="admin", description="Admin panel")]


@router.startup()
async def ornat(bot: Bot, **_) -> None:
    await bot.set_my_commands(UMUMIY, scope=BotCommandScopeDefault())
    for admin_id in ADMIN_IDS:
        try:
            await bot.set_my_commands(ADMIN, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as xato:  # admin hali botga yozmagan bo'lishi mumkin
            log.info("admin buyruqlari o'rnatilmadi (%s): %s", admin_id, xato)
    log.info("buyruqlar menyusi o'rnatildi")
