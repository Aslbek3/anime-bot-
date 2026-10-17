"""Middleware'lar: foydalanuvchini ro'yxatga olish va admin filtri."""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.dispatcher.event.bases import UNHANDLED
from aiogram.types import TelegramObject, User

import db
from config import ADMIN_ID


class ActivityMiddleware(BaseMiddleware):
    """Har bir update'da userni saqlaydi / oxirgi faollikni yangilaydi."""

    async def __call__(self, handler, event: TelegramObject, data: dict[str, Any]):
        user: User | None = data.get("event_from_user")
        if user and not user.is_bot:
            await db.save_user(user.id, user.username, user.full_name)
        return await handler(event, data)


class AdminOnly(BaseMiddleware):
    """Admin bo'lmaganlarni o'tkazmaydi.

    UNHANDLED qaytaradi — shunda update keyingi routerlarga (qidiruv, murojat)
    o'tib ketadi, oddiy user admin panelni umuman sezmaydi.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ):
        user: User | None = data.get("event_from_user")
        if user and user.id == ADMIN_ID:
            return await handler(event, data)
        return UNHANDLED
