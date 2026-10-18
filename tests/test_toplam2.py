"""Ikkinchi to'plam modullari yoqilgan holat.

Qamrov: kanal import, chidamli qidiruv, ko'rilgan ✓, kuzatish, baho,
fasl, kino/serial turi, qidiruv jurnali, manba, qism almashtirish,
rejalashtirilgan tarqatish, CSV, til, inline, buyruqlar menyusi,
xatolar jurnali va SQLite FSM storage.
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
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent, Message, MessageId, Update, User

import db
import main as app
from config import ADMIN_ID, ARCHIVE_CHANNEL_ID, LOG_CHANNEL_ID

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
        if nom in {"SendMessage", "SendPhoto", "SendVideo", "SendDocument"}:
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


def _klaviaturani_yoz(log):
    """Har bir tapdan keyin chaqiriladi: reply klaviatura chatda saqlanib qoladi."""
    for m in log:
        if type(m).__name__.startswith("Send") and getattr(m, "reply_markup", None) is not None:
            KLAVIATURA[m.chat_id] = [[b.text for b in r] for r in m.reply_markup.keyboard]


async def tap(uid, text=None, **qoshimcha):
    bot.session.log.clear()
    upd = Update.model_validate(
        {"update_id": MID[0] + 5000, "message": raw(uid, text, **qoshimcha)}, context={"bot": bot}
    )
    await dp.feed_update(bot, upd)
    _klaviaturani_yoz(bot.session.log)
    return bot.session.log


async def kanalga(caption, msg_id, davomiyligi=60):
    """Arxiv kanalga video tashlanishini taqlid qiladi."""
    bot.session.log.clear()
    upd = Update.model_validate(
        {
            "update_id": MID[0] + 9000,
            "channel_post": {
                "message_id": msg_id,
                "date": int(time.time()),
                "chat": {"id": ARCHIVE_CHANNEL_ID, "type": "channel", "title": "arxiv"},
                "caption": caption,
                "video": {
                    "file_id": "v",
                    "file_unique_id": "u",
                    "width": 1,
                    "height": 1,
                    "duration": davomiyligi,
                },
            },
        },
        context={"bot": bot},
    )
    await dp.feed_update(bot, upd)
    _klaviaturani_yoz(bot.session.log)
    return bot.session.log


def yuborilgan(log):
    matn = chat = None
    for m in log:
        if type(m).__name__ in {"SendMessage", "SendPhoto", "CopyMessage"}:
            matn = getattr(m, "text", None) or getattr(m, "caption", None) or ""
            chat = m.chat_id
    if matn is None:
        raise AssertionError("hech narsa yuborilmadi")
    return matn, KLAVIATURA.get(chat, [])


def chatga(log, chat_id):
    return [m for m in log if type(m).__name__.startswith("Send") and m.chat_id == chat_id]


def turlari(log):
    return [type(m).__name__ for m in log]


def tekis(tugmalar):
    return [t for r in tugmalar for t in r]


async def run():
    await db.init_db()
    for m in app.ROUTERS:
        dp.include_router(m.router)
    from middlewares import ActivityMiddleware

    dp.update.outer_middleware(ActivityMiddleware())

    nomlar = [m.__name__.split(".")[-1] for m in app.ROUTERS]
    for kerak in (
        "kanal_import", "qidiruv_jurnali", "manba", "qism_almash", "reja", "csv_almash",
        "kuzatish", "baho", "fasl", "tur", "til", "inline", "jurnal", "buyruqlar", "kashfiyot",
    ):
        assert kerak in nomlar, (kerak, nomlar)

    # ---------- BUYRUQLAR (setMyCommands startupda)
    bot.session.log.clear()
    await dp.emit_startup(bot=bot)
    assert "SetMyCommands" in turlari(bot.session.log)

    # ---------- KANAL IMPORT
    log = await kanalga("Spartak | 1", 601)
    assert (await db.get_serial_by_name("Spartak")) is not None
    spartak = await db.get_serial_by_name("Spartak")
    assert (await db.get_episode(spartak["id"], 1))["kanal_msg_id"] == 601
    await kanalga("Spartak | 2", 602)
    await kanalga("Spartak | 2x1", 603)          # 2-fasl
    assert await db.fasllar(spartak["id"]) == [1, 2]
    await kanalga("tushunarsiz caption", 604)    # FEATURE_TUR: kino bo'lib qo'shiladi
    avatar = await db.get_serial_by_name("tushunarsiz caption")
    assert avatar is not None and avatar["turi"] == "kino"

    # ---------- TUR: kino kartochkasida qismlar ro'yxati yo'q
    await tap(USER, "/start")
    matn, tugmalar = yuborilgan(await tap(USER, "🎞 Kinolar"))
    assert "Kinolar" in matn and "🎬 tushunarsiz caption" in tekis(tugmalar)
    matn, tugmalar = yuborilgan(await tap(USER, "🎬 tushunarsiz caption"))
    assert "🎞 Kino" in matn and "Qismlar:" not in matn, matn
    assert "▶️ Ko'rish" in tekis(tugmalar) and "1-qism" not in tekis(tugmalar)
    log = await tap(USER, "▶️ Ko'rish")
    assert [m for m in log if type(m).__name__ == "CopyMessage"]

    # ---------- FASL
    matn, tugmalar = yuborilgan(await tap(USER, "🎬 Spartak"))
    assert "📂 1-fasl" in tekis(tugmalar) and "📂 2-fasl" in tekis(tugmalar), tugmalar
    matn, tugmalar = yuborilgan(await tap(USER, "📂 2-fasl"))
    assert "2-fasl" in matn and "1-qism" in tekis(tugmalar)
    matn, tugmalar = yuborilgan(await tap(USER, "📂 1-fasl"))
    assert "2-qism" in tekis(tugmalar)

    # ---------- KO'RILGAN ✓
    await tap(USER, "1-qism")
    matn, tugmalar = yuborilgan(await tap(USER, "📋 Qismlar"))
    assert "✓ 1-qism" in tekis(tugmalar), tugmalar
    assert "2-qism" in tekis(tugmalar)
    matn, _ = yuborilgan(await tap(USER, "✓ 1-qism"))   # ✓ bilan ham ochiladi
    assert "1-qism" in matn

    # ---------- KUZATISH
    await tap(USER, "🎬 Spartak")
    log = await tap(USER, "🔔 Kuzatish")
    assert any("Kuzatuvga qo'shildi" in (m.text or "") for m in chatga(log, USER))
    assert await db.kuzatuv_bormi(USER, spartak["id"])
    _, tugmalar = yuborilgan(log)
    assert "🔕 Kuzatmaslik" in tekis(tugmalar)
    matn, tugmalar = yuborilgan(await tap(USER, "🔔 Kuzatganlarim"))
    assert "🎬 Spartak" in tekis(tugmalar)

    # ---------- BAHO
    await tap(USER, "🎬 Spartak")
    log = await tap(USER, "👍 0")
    _, tugmalar = yuborilgan(log)
    assert "👍 1" in tekis(tugmalar), tugmalar
    matn, tugmalar = yuborilgan(await tap(USER, "⭐ Eng yaxshilar"))
    assert "Spartak" in matn and "+1" in matn

    # ---------- CHIDAMLI QIDIRUV
    await db.add_serial("Spider-Man", None, None, None, 2021)
    matn, tugmalar = yuborilgan(await tap(USER, "spaydermen"))
    assert "Shulardan birini" in matn, matn
    assert "🎬 Spider-Man" in tekis(tugmalar)

    # ---------- QIDIRUV JURNALI
    await tap(USER, "yoqbunaqakino")
    matn, _ = yuborilgan(await tap(ADMIN_ID, "/admin"))
    matn, _ = yuborilgan(await tap(ADMIN_ID, "🔎 So'ralganlar"))
    assert "yoqbunaqakino" in matn, matn

    # ---------- MANBA
    await tap(USER, "/start ref_instagram")
    assert (await db.manba_statistika())[0]["manba"] == "instagram"
    await tap(ADMIN_ID, "⬅️ Admin panel")
    matn, _ = yuborilgan(await tap(ADMIN_ID, "📈 Manbalar"))
    assert "instagram" in matn

    # ---------- QISM ALMASHTIRISH
    await tap(ADMIN_ID, "⬅️ Admin panel")
    matn, _ = yuborilgan(await tap(ADMIN_ID, "♻️ Qismni almashtirish"))
    assert "Qaysi serialda" in matn
    matn, _ = yuborilgan(await tap(ADMIN_ID, "🎬 Spartak"))
    assert "Qaysi qismni" in matn
    matn, _ = yuborilgan(await tap(ADMIN_ID, "1"))
    assert "forward qiling" in matn
    forward = {
        "forward_origin": {
            "type": "channel",
            "chat": {"id": ARCHIVE_CHANNEL_ID, "type": "channel", "title": "arxiv"},
            "message_id": 999,
            "date": int(time.time()),
        },
        "video": {"file_id": "v", "file_unique_id": "u", "width": 1, "height": 1, "duration": 77},
    }
    matn, _ = yuborilgan(await tap(ADMIN_ID, None, **forward))
    assert "almashtirildi" in matn
    yangilangan = await db.get_episode(spartak["id"], 1)
    assert yangilangan["kanal_msg_id"] == 999 and yangilangan["davomiyligi"] == 77

    # ---------- REJALASHTIRILGAN TARQATISH
    await tap(ADMIN_ID, "⬅️ Admin panel")
    matn, tugmalar = yuborilgan(await tap(ADMIN_ID, "⏰ Rejalashtirilgan"))
    assert "Rejalashtirilgan" in matn and "➕ Yangi reja" in tekis(tugmalar)
    await tap(ADMIN_ID, "➕ Yangi reja")
    await tap(ADMIN_ID, "Hammaga xabar")
    matn, _ = yuborilgan(await tap(ADMIN_ID, "2020-01-01 10:00"))   # o'tgan vaqt
    assert "saqlandi" in matn
    from handlers import reja as reja_moduli

    yetganlar = await db.reja_yetganlar()
    assert len(yetganlar) == 1
    bot.session.log.clear()
    await reja_moduli.bajarish(bot, yetganlar[0])
    assert len([m for m in bot.session.log if type(m).__name__ == "CopyMessage"]) == 2
    assert (await db.rejalar("yuborildi"))[0]["natija"].startswith("✅ 2")

    # ---------- CSV
    await tap(ADMIN_ID, "⬅️ Admin panel")
    matn, _ = yuborilgan(await tap(ADMIN_ID, "🗂 CSV"))
    log = await tap(ADMIN_ID, "⬇️ Eksport")
    hujjatlar = [m for m in log if type(m).__name__ == "SendDocument"]
    assert len(hujjatlar) == 2
    mazmun = hujjatlar[0].document.data.decode("utf-8-sig")
    assert "nom;tavsif" in mazmun and "Spartak" in mazmun

    # ---------- TIL
    matn, tugmalar = yuborilgan(await tap(USER, "🏠 Asosiy menyu"))
    assert "🌐 Til" in tekis(tugmalar), (matn, tugmalar)
    await tap(USER, "🌐 Til")
    log = await tap(USER, "🇷🇺 Русский")
    assert any("Здравствуйте" in (m.text or "") for m in chatga(log, USER)), [
        m.text for m in chatga(log, USER)
    ]
    assert await db.til_ol(USER) == "ru"
    await tap(USER, "🌐 Til")
    await tap(USER, "🇺🇿 O'zbekcha")

    # ---------- INLINE REJIM
    bot.session.log.clear()
    upd = Update.model_validate(
        {
            "update_id": MID[0] + 7000,
            "inline_query": {
                "id": "1",
                "from": {"id": USER, "is_bot": False, "first_name": "T"},
                "query": "Spartak",
                "offset": "",
            },
        },
        context={"bot": bot},
    )
    await dp.feed_update(bot, upd)
    javoblar = [m for m in bot.session.log if type(m).__name__ == "AnswerInlineQuery"]
    assert javoblar and javoblar[0].results
    assert "start=serial_" in javoblar[0].results[0].input_message_content.message_text

    # ---------- XATOLAR JURNALI
    from handlers import jurnal

    soxta = Message.model_validate(raw(USER, "xato"), context={"bot": bot})
    bot.session.log.clear()
    await jurnal.tutuvchi(
        ErrorEvent(update=Update(update_id=1, message=soxta), exception=ValueError("sinov")),
        bot,
    )
    jurnalga = chatga(bot.session.log, LOG_CHANNEL_ID)
    assert jurnalga and "ValueError" in jurnalga[0].text
    assert any("Kutilmagan xatolik" in (m.text or "") for m in chatga(bot.session.log, USER))

    # ---------- SQLITE FSM STORAGE
    from storage import SQLiteStorage

    saqlagich = SQLiteStorage()
    kalit = StorageKey(bot_id=1, chat_id=USER, user_id=USER)
    await saqlagich.set_state(kalit, "sinov:holat")
    await saqlagich.set_data(kalit, {"nav_ekran": "serial", "nav_serial": 7})
    assert await saqlagich.get_state(kalit) == "sinov:holat"
    assert (await saqlagich.get_data(kalit))["nav_serial"] == 7
    boshqa = SQLiteStorage()          # "restart"
    assert (await boshqa.get_data(kalit))["nav_ekran"] == "serial"

    print("E2E-TOPLAM2 OK")


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
