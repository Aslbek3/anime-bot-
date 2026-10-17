"""FEATURE_YUKLASH=true va FEATURE_TAKLIF=true holatidagi uchidan-uchiga sinov."""
import asyncio
import contextlib
import os
import sys
import time
from pathlib import Path
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, MessageId, Update, User

import db
import main as app
from config import ADMIN_ID, FEATURE_TAKLIF, FEATURE_YUKLASH

USER = 555
MID = [0]
KLAVIATURA = {}


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


def adminga(log):
    return [m for m in log if type(m).__name__ == "SendMessage" and m.chat_id == ADMIN_ID]


def userga(log, uid=USER):
    return [m for m in log if type(m).__name__ == "SendMessage" and m.chat_id == uid]


def tekis(tugmalar):
    return [t for r in tugmalar for t in r]


async def run():
    assert FEATURE_YUKLASH and FEATURE_TAKLIF, "bayroqlar yoqilmagan"
    await db.init_db()
    for m in app.ROUTERS:
        dp.include_router(m.router)
    from middlewares import ActivityMiddleware

    dp.update.outer_middleware(ActivityMiddleware())
    assert [m.__name__ for m in app.ROUTERS] == [
        "handlers.admin", "handlers.yuklash", "handlers.taklif",
        "handlers.kino", "handlers.murojat", "handlers.qidiruv",
    ], [m.__name__ for m in app.ROUTERS]

    sid = await db.add_serial("Spartak", "tavsif", None, "drama", 2021)
    await db.add_episode(sid, 1, None, 501, 60)

    # ---------- tugmalar bayroq yoqilganda ko'rinadi
    matn, tugmalar = yuborilgan(await tap(USER, "/start"))
    assert "➕ Kino taklif qilish" in tekis(tugmalar), tugmalar
    matn, tugmalar = yuborilgan(await tap(ADMIN_ID, "/admin"))
    assert "⬇️ Yuklash" in tekis(tugmalar) and "📥 Takliflar" in tekis(tugmalar), tugmalar

    # ---------- TAKLIF: user oqimi
    matn, tugmalar = yuborilgan(await tap(USER, "➕ Kino taklif qilish"))
    assert "1/3" in matn
    matn, _ = yuborilgan(await tap(USER, "Interstellar"))
    assert "2/3" in matn
    matn, _ = yuborilgan(await tap(USER, "➖ O'tkazib yuborish"))
    assert "3/3" in matn
    log = await tap(USER, "https://example.com/film")
    assert "Yangi taklif" in adminga(log)[0].text
    matn, _ = yuborilgan(log)
    assert "taklifingiz qabul qilindi" in matn

    taklif = (await db.takliflar())[0]
    assert taklif["nom"] == "Interstellar" and taklif["holat"] == "kutilmoqda"
    assert taklif["qoshgan_user_id"] == USER and taklif["manba_url"] == "https://example.com/film"
    assert taklif["tavsif"] is None

    # tasdiqlanmagan taklif userga KO'RINMAYDI
    assert await db.count_serials() == 1
    matn, tugmalar = yuborilgan(await tap(USER, "/start"))
    assert "🎬 Interstellar" not in tekis(tugmalar), tugmalar
    matn, _ = yuborilgan(await tap(USER, "Interstellar"))
    assert "topilmadi" in matn
    assert await db.get_serial_by_name("Interstellar") is None  # nom bo'yicha ham ochilmaydi
    matn, _ = yuborilgan(await tap(USER, f"/start serial_{(await db.takliflar())[0]['id']}"))
    assert "Assalomu alaykum" in matn  # tasdiqlanmagan taklif deeplink bilan ham ochilmaydi

    # ---------- TAKLIF: bekor qilish FSM ni uzadi
    await tap(USER, "➕ Kino taklif qilish")
    matn, _ = yuborilgan(await tap(USER, "✖️ Bekor qilish"))
    assert "Assalomu alaykum" in matn
    matn, _ = yuborilgan(await tap(USER, "bu endi qidiruv"))
    assert "topilmadi" in matn  # FSM uzildi, matn qidiruvga ketdi

    # ---------- TAKLIF: kunlik limit (3 ta)
    await db.taklif_qosh("Ikkinchi", None, None, USER)
    await db.taklif_qosh("Uchinchi", None, None, USER)
    assert await db.bugungi_takliflar(USER) == 3
    matn, _ = yuborilgan(await tap(USER, "➕ Kino taklif qilish"))
    assert "ortiq taklif yuborib bo'lmaydi" in matn

    # ---------- TAKLIF: admin tasdiqlaydi
    matn, tugmalar = yuborilgan(await tap(ADMIN_ID, "📥 Takliflar"))
    assert f"#{taklif['id']} · Interstellar" in tekis(tugmalar), tugmalar
    matn, tugmalar = yuborilgan(await tap(ADMIN_ID, f"#{taklif['id']} · Interstellar"))
    assert "Taklif" in matn and "@testchi" in matn
    assert "✅ Tasdiqlash" in tekis(tugmalar) and "❌ Rad etish" in tekis(tugmalar)

    log = await tap(ADMIN_ID, "✅ Tasdiqlash")
    assert "qabul qilindi" in userga(log)[0].text  # taklif egasiga xabar ketdi
    assert (await db.get_serial(taklif["id"]))["holat"] == "tasdiqlangan"

    # endi ro'yxatda ko'rinadi va kartochkada muallif bor
    matn, tugmalar = yuborilgan(await tap(USER, "/start"))
    assert "🎬 Interstellar" in tekis(tugmalar)
    matn, _ = yuborilgan(await tap(USER, "🎬 Interstellar"))
    assert "➕ qo'shdi: @testchi" in matn, matn

    # ---------- TAKLIF: admin rad etadi
    rad = await db.taklif_qosh("Keraksiz", None, None, USER)
    await tap(ADMIN_ID, "📥 Takliflar")
    await tap(ADMIN_ID, f"#{rad} · Keraksiz")
    log = await tap(ADMIN_ID, "❌ Rad etish")
    assert "qabul qilinmadi" in userga(log)[0].text
    assert await db.get_serial(rad) is None

    # ---------- YUKLASH: navbat va kesh
    matn, tugmalar = yuborilgan(await tap(ADMIN_ID, "⬅️ Admin panel"))
    matn, tugmalar = yuborilgan(await tap(ADMIN_ID, "⬇️ Yuklash"))
    assert "Yuklash" in matn and "🔗 Link yuborish" in tekis(tugmalar)
    matn, _ = yuborilgan(await tap(ADMIN_ID, "🔗 Link yuborish"))
    assert "havolani yuboring" in matn

    matn, _ = yuborilgan(await tap(ADMIN_ID, "shunchaki matn"))
    assert "havolaga o'xshamaydi" in matn

    matn, _ = yuborilgan(await tap(ADMIN_ID, "https://sayt.uz/kino/1"))
    assert "Navbatga qo'shildi: #1" in matn
    matn, _ = yuborilgan(await tap(ADMIN_ID, "https://sayt.uz/kino/1"))
    assert "allaqachon navbatda" in matn  # dublikat qo'shilmaydi
    assert len(await db.navbat_royxat("navbatda", 10)) == 1

    matn, _ = yuborilgan(await tap(ADMIN_ID, "📋 Navbat holati"))
    assert "Navbatda: <b>1</b>" in matn

    # ---------- YUKLASH: fon vazifasi (namuna parser xato beradi, navbat to'xtamaydi)
    from handlers import yuklash

    vazifa = await db.navbat_keyingi()
    bot.session.log.clear()
    await yuklash.bajarish(bot, vazifa)
    satr = (await db.navbat_royxat("xato", 5))[0]
    assert satr["id"] == vazifa["id"] and "NotImplementedError" in satr["xato_matni"]
    assert satr["tugagan_at"] is not None
    assert "Xato #1" in adminga(bot.session.log)[0].text
    assert await db.navbat_keyingi() is None  # navbat bo'shadi

    matn, _ = yuborilgan(await tap(ADMIN_ID, "⚠️ Xatolar"))
    assert "NotImplementedError" in matn and "sayt.uz/kino/1" in matn

    # ---------- YUKLASH: kesh (tayyor yozuv qayta yuklanmaydi)
    tayyor = await db.navbat_qosh("https://sayt.uz/kino/9")
    await db.navbat_holat(tayyor, "tayyor", kanal_msg_id=4242)
    await tap(ADMIN_ID, "🔗 Link yuborish")
    matn, _ = yuborilgan(await tap(ADMIN_ID, "https://sayt.uz/kino/9"))
    assert "avval yuklangan" in matn and "4242" in matn
    assert len(await db.navbat_royxat("navbatda", 10)) == 0  # navbatga tushmadi

    # ---------- eski funksiyalar buzilmagan
    matn, tugmalar = yuborilgan(await tap(USER, "/start"))
    assert "Assalomu alaykum" in matn and "🎬 Spartak" in tekis(tugmalar)
    matn, _ = yuborilgan(await tap(USER, "🎬 Spartak"))
    assert "Qismlar: 1" in matn
    log = await tap(USER, "1-qism")
    assert [m for m in log if type(m).__name__ == "CopyMessage"]
    matn, _ = yuborilgan(await tap(USER, "✍️ Adminga yozish"))
    assert "bitta xabarda yozing" in matn

    print("E2E-ON OK")


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
