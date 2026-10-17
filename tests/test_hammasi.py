"""Barcha qo'shimcha modullar yoqilgan holat.

Qamrov: janrlar, mening ro'yxatim, ulashish, qism raqami, bildirishnoma,
avtopost, zaxira, antiflood, majburiy obuna, qidiruv sahifalash va
"eskirgan ekran" tuzatishi.
"""
import asyncio
import contextlib
import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ChatMemberLeft, ChatMemberMember, Message, MessageId, Update, User

import db
import main as app
from config import ADMIN_ID, POST_CHANNEL_ID

USER = 555
MID = [0]
KLAVIATURA = {}
AZO = {"holat": True}


class FakeSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.log = []
        self._mid = 1000

    async def close(self):
        pass

    async def stream_content(self, *a, **kw):
        yield b""

    async def make_request(self, bot, method, timeout=None):
        nom = type(method).__name__
        self.log.append(method)
        self._mid += 1
        if nom == "GetMe":
            return User(id=1, is_bot=True, first_name="bot", username="b")
        if nom == "GetChatMember":
            kim = {"id": method.user_id, "is_bot": False, "first_name": "T"}
            turi = ChatMemberMember if AZO["holat"] else ChatMemberLeft
            holat = "member" if AZO["holat"] else "left"
            return turi.model_validate({"status": holat, "user": kim})
        if nom in {"SendMessage", "SendPhoto", "SendVideo"}:
            return Message.model_validate(
                {
                    "message_id": self._mid,
                    "date": int(time.time()),
                    "chat": {"id": method.chat_id, "type": "private"},
                    "text": getattr(method, "text", None) or getattr(method, "caption", None),
                },
                context={"bot": bot},
            )
        if nom == "CopyMessage":
            return MessageId(message_id=self._mid)
        return True


bot = Bot("42:TEST", session=FakeSession())
dp = Dispatcher(storage=MemoryStorage())


def raw(uid, text=None, **qoshimcha):
    MID[0] += 1
    xabar = {
        "message_id": MID[0],
        "date": int(time.time()),
        "chat": {"id": uid, "type": "private"},
        "from": {"id": uid, "is_bot": False, "first_name": "T", "username": "testchi"},
    }
    if text is not None:
        xabar["text"] = text
    xabar.update(qoshimcha)
    return xabar


async def tap(uid, text=None, **qoshimcha):
    bot.session.log.clear()
    upd = Update.model_validate(
        {"update_id": MID[0] + 1000, "message": raw(uid, text, **qoshimcha)}, context={"bot": bot}
    )
    await dp.feed_update(bot, upd)
    return bot.session.log


def yuborilgan(log):
    matn = chat = None
    for m in log:
        if type(m).__name__ in {"SendMessage", "SendPhoto", "CopyMessage"}:
            matn = getattr(m, "text", None) or getattr(m, "caption", None) or ""
            chat = m.chat_id
            if m.reply_markup is not None:
                KLAVIATURA[chat] = [[b.text for b in r] for r in m.reply_markup.keyboard]
    if matn is None:
        raise AssertionError("hech narsa yuborilmadi")
    return matn, KLAVIATURA.get(chat, [])


def chatga(log, chat_id):
    return [
        m for m in log
        if type(m).__name__ in {"SendMessage", "SendPhoto"} and m.chat_id == chat_id
    ]


def tekis(tugmalar):
    return [t for r in tugmalar for t in r]


async def run():
    await db.init_db()
    for m in app.ROUTERS:
        dp.include_router(m.router)
    from handlers import obuna
    from middlewares import ActivityMiddleware

    # Antiflood ataylab ulanmaydi: sinovdagi taplar millisekundlarda ketadi,
    # uni pastda alohida birlik sinovi bilan tekshiramiz.
    dp.update.outer_middleware(ActivityMiddleware())
    dp.update.outer_middleware(obuna.ObunaMiddleware())

    nomlar = [m.__name__ for m in app.ROUTERS]
    assert nomlar == [
        "handlers.obuna", "handlers.admin", "handlers.yuklash", "handlers.taklif",
        "handlers.janrlar", "handlers.ulashish", "handlers.kino", "handlers.royxatim",
        "handlers.qism_raqam", "handlers.zaxira", "handlers.murojat", "handlers.qidiruv",
    ], nomlar

    drama = await db.add_serial("Spartak", "tavsif", None, "drama", 2021)
    for q in range(1, 13):
        await db.add_episode(drama, q, None, 500 + q, 60)
    komediya = await db.add_serial("Kulgu", None, None, "komediya", 2022)
    await db.add_episode(komediya, 1, None, 900, 60)
    for i in range(10):
        await db.add_serial(f"Drama {i}", None, None, "drama", 2020)

    # ---------- MAJBURIY OBUNA
    AZO["holat"] = False
    log = await tap(USER, "/start")
    matn, tugmalar = yuborilgan(log)
    assert "a'zo bo'ling" in matn and "✅ Tekshirish" in tekis(tugmalar)
    assert "Assalomu alaykum" not in matn  # update to'xtatildi
    matn, _ = yuborilgan(await tap(USER, "✅ Tekshirish"))
    assert "a'zo bo'ling" in matn  # hali a'zo emas
    AZO["holat"] = True
    matn, tugmalar = yuborilgan(await tap(USER, "✅ Tekshirish"))
    assert "Assalomu alaykum" in matn

    # ---------- yangi tugmalar ko'rinadi
    matn, tugmalar = yuborilgan(await tap(USER, "/start"))
    for tugma in ("📺 Mening ro'yxatim", "🏷 Janrlar", "➕ Kino taklif qilish"):
        assert tugma in tekis(tugmalar), (tugma, tugmalar)

    # ---------- JANRLAR
    matn, tugmalar = yuborilgan(await tap(USER, "🏷 Janrlar"))
    assert "🏷 drama" in tekis(tugmalar) and "🏷 komediya" in tekis(tugmalar)
    matn, tugmalar = yuborilgan(await tap(USER, "🏷 drama"))
    assert "11 ta serial" in matn, matn
    assert "1/2" in tekis(tugmalar), tugmalar          # yangisidan boshlab sahifalanadi
    matn, tugmalar = yuborilgan(await tap(USER, "➡️"))
    assert "2/2" in tekis(tugmalar) and "🎬 Spartak" in tekis(tugmalar), tugmalar
    matn, tugmalar = yuborilgan(await tap(USER, "⬅️ Orqaga"))
    assert "Janrlar" in matn

    # ---------- ULASHISH (serial va qism ekranida)
    await tap(USER, "🏷 drama")
    matn, tugmalar = yuborilgan(await tap(USER, "🎬 Spartak"))
    assert "🔗 Ulashish" in tekis(tugmalar)
    matn, _ = yuborilgan(await tap(USER, "🔗 Ulashish"))
    assert f"https://t.me/b?start=serial_{drama}" in matn

    # ---------- QISM RAQAMI
    matn, tugmalar = yuborilgan(await tap(USER, "7"))
    assert "7-qism" in matn and "⬅️ Oldingi" in tekis(tugmalar)
    matn, _ = yuborilgan(await tap(USER, "99"))
    assert "99-qism yo'q" in matn and "1–12" in matn
    matn, _ = yuborilgan(await tap(USER, "🔗 Ulashish"))
    assert "7-qismga havola" in matn and f"start=qism_{drama}_7" in matn

    # ---------- MENING RO'YXATIM
    matn, tugmalar = yuborilgan(await tap(USER, "🏠 Asosiy menyu"))
    matn, tugmalar = yuborilgan(await tap(USER, "📺 Mening ro'yxatim"))
    assert "1 ta serial" in matn
    assert "▶️ Spartak · 7-qism" in tekis(tugmalar), tugmalar
    matn, _ = yuborilgan(await tap(USER, "▶️ Spartak · 7-qism"))
    assert "7-qism" in matn

    # ---------- QIDIRUV SAHIFALASH
    matn, tugmalar = yuborilgan(await tap(USER, "Drama"))
    assert "ta natija" in matn and "1/2" in tekis(tugmalar), (matn, tugmalar)
    matn, tugmalar = yuborilgan(await tap(USER, "➡️"))
    assert "2/2" in tekis(tugmalar) and "🎬 Drama 9" in tekis(tugmalar)

    # ---------- ESKIRGAN EKRAN (nav konteksti yo'qolgan)
    holat = dp.fsm.get_context(bot, USER, USER)
    await holat.set_data({})
    matnlar = [m.text or "" for m in chatga(await tap(USER, "➡️"), USER)]
    assert any("eskirgan" in t.lower() for t in matnlar), matnlar
    assert any("Assalomu alaykum" in t for t in matnlar), matnlar
    await holat.set_data({})
    matnlar = [m.text or "" for m in chatga(await tap(USER, "5-qism"), USER)]
    assert any("eskirgan" in t.lower() for t in matnlar), matnlar

    # ---------- BILDIRISHNOMA + AVTOPOST (admin qism qo'shganda)
    await tap(ADMIN_ID, "/admin")
    await tap(ADMIN_ID, "🎬 Qism qo'shish")
    await tap(ADMIN_ID, "🎬 Spartak")
    forward = {
        "forward_origin": {
            "type": "channel",
            "chat": {"id": -100123, "type": "channel", "title": "arxiv"},
            "message_id": 777,
            "date": int(time.time()),
        },
        "video": {"file_id": "v", "file_unique_id": "u", "width": 1, "height": 1, "duration": 42},
    }
    log = await tap(ADMIN_ID, None, **forward)
    await asyncio.sleep(0.2)  # fon vazifalari (bildirishnoma/avtopost) tugasin
    assert (await db.get_episode(drama, 13))["kanal_msg_id"] == 777

    hammasi = bot.session.log
    userga = chatga(hammasi, USER)
    assert any("13-qism chiqdi" in (m.text or "") for m in userga), [m.text for m in userga]
    kanalga = chatga(hammasi, POST_CHANNEL_ID)
    assert any("13-qism qo'shildi" in (m.text or "") for m in kanalga), POST_CHANNEL_ID
    assert any(f"start=qism_{drama}_13" in (m.text or "") for m in kanalga)

    # ---------- ZAXIRA
    from handlers import zaxira

    nusxa = await zaxira.bir_marta()
    assert nusxa.exists() and nusxa.stat().st_size > 0

    # ---------- ANTIFLOOD (ketma-ket bosish tashlab yuboriladi)
    from middlewares import AntifloodMiddleware

    mw = AntifloodMiddleware()

    async def handler(event, data):
        return "o'tdi"

    soxta = Message.model_validate(raw(USER, "x"), context={"bot": bot})
    data = {"event_from_user": soxta.from_user}
    assert await mw(handler, soxta, data) == "o'tdi"
    assert await mw(handler, soxta, data) is None  # darhol ikkinchisi — tashlandi

    print("E2E-HAMMASI OK")


async def main():
    kod = 0
    try:
        await run()
    except BaseException:
        traceback.print_exc()
        kod = 1
    with contextlib.suppress(Exception):
        await db.close_db()
    sys.stdout.flush()
    os._exit(kod)


asyncio.run(main())
