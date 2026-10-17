"""Reply-tugmali navigatsiyani soxta Telegram sessiyasi orqali uchidan-uchiga sinash."""
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
from config import ADMIN_ID, ARCHIVE_CHANNEL_ID

USER = 555
MID = [0]
OCHIRISHLAR = []


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
        if nom == "DeleteMessage":
            OCHIRISHLAR.append(method)
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
        "from": {"id": uid, "is_bot": False, "first_name": "T"},
    }
    if text is not None:
        xabar["text"] = text
    xabar.update(qoshimcha)
    return xabar


async def tap(uid, text=None, **qoshimcha):
    """Tugma bosish / xabar yuborish."""
    bot.session.log.clear()
    OCHIRISHLAR.clear()
    upd = Update.model_validate(
        {"update_id": MID[0] + 1000, "message": raw(uid, text, **qoshimcha)}, context={"bot": bot}
    )
    await dp.feed_update(bot, upd)
    return bot.session.log


KLAVIATURA = {}  # chat_id -> hozir ko'rinib turgan tugmalar (reply kb saqlanib qoladi)


def yuborilgan(log):
    """Oxirgi yuborilgan matn va o'sha chatda ko'rinib turgan tugmalar."""
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


def tekis(tugmalar):
    return [t for r in tugmalar for t in r]


def metodlar(log):
    return [type(m).__name__ for m in log]


async def run():
    await db.init_db()
    for m in app.ROUTERS:
        dp.include_router(m.router)
    from middlewares import ActivityMiddleware

    dp.update.outer_middleware(ActivityMiddleware())

    # --- ma'lumot
    for i in range(2, 11):
        await db.add_serial(f"Serial {i}", None, None, None, 2020)
    # ro'yxat yangisidan boshlanadi -> Spartak birinchi sahifada turadi
    sid = await db.add_serial("Spartak", "tavsif", None, "drama", 2021)
    for q in range(1, 13):
        await db.add_episode(sid, q, None, 500 + q, 1200)

    # --- /start: asosiy menyu
    matn, tugmalar = yuborilgan(await tap(USER, "/start"))
    assert "Assalomu alaykum" in matn, matn
    assert ["🎬 Spartak"] in tugmalar, tugmalar
    assert "➡️" in tekis(tugmalar) and "⬅️" not in tekis(tugmalar)
    assert "1/2" in tekis(tugmalar)
    assert "✍️ Adminga yozish" in tekis(tugmalar)
    assert "▶️ Davom ettirish" not in " ".join(tekis(tugmalar))

    # --- sahifalash
    _, tugmalar = yuborilgan(await tap(USER, "➡️"))
    assert "2/2" in tekis(tugmalar) and "➡️" not in tekis(tugmalar)
    _, tugmalar = yuborilgan(await tap(USER, "⬅️"))
    assert "1/2" in tekis(tugmalar)

    # --- serial kartochkasi
    log = await tap(USER, "🎬 Spartak")
    matn, tugmalar = yuborilgan(log)
    assert "Spartak" in matn and "📺 Qismlar: 12" in matn, matn
    assert "1-qism" in tekis(tugmalar) and "8-qism" in tekis(tugmalar)
    assert "9-qism" not in tekis(tugmalar)  # 8 tadan sahifalangan
    assert ["⬅️ Ro'yxatga", "🏠 Asosiy menyu"] in tugmalar
    assert "DeleteMessage" not in metodlar(log)  # hech narsa o'chirilmaydi

    # --- qism yuborish (arxiv kanaldan copy_message)
    log = await tap(USER, "1-qism")
    nusxa = [m for m in log if type(m).__name__ == "CopyMessage"][0]
    assert nusxa.from_chat_id == ARCHIVE_CHANNEL_ID and nusxa.message_id == 501
    matn, tugmalar = yuborilgan(log)
    assert "1-qism" in matn
    assert "⬅️ Oldingi" not in tekis(tugmalar)  # birinchi qism
    assert "Keyingi ➡️" in tekis(tugmalar) and "📋 Qismlar" in tekis(tugmalar)
    assert (await db.last_progress(USER))["oxirgi_qism"] == 1

    # --- keyingi / oldingi
    matn, tugmalar = yuborilgan(await tap(USER, "Keyingi ➡️"))
    assert "2-qism" in matn
    assert "⬅️ Oldingi" in tekis(tugmalar) and "Keyingi ➡️" in tekis(tugmalar)
    matn, _ = yuborilgan(await tap(USER, "⬅️ Oldingi"))
    assert "1-qism" in matn

    # --- oxirgi qismda "Keyingi" ko'rinmaydi
    await tap(USER, "📋 Qismlar")
    await tap(USER, "➡️")
    matn, tugmalar = yuborilgan(await tap(USER, "12-qism"))
    assert "12-qism" in matn
    assert "Keyingi ➡️" not in tekis(tugmalar) and "⬅️ Oldingi" in tekis(tugmalar)

    # --- qismlar ro'yxatiga qaytish: o'sha sahifa ochiladi
    matn, tugmalar = yuborilgan(await tap(USER, "📋 Qismlar"))
    assert "9-qism" in tekis(tugmalar) and "12-qism" in tekis(tugmalar)

    # --- davom ettirish tugmasi
    matn, tugmalar = yuborilgan(await tap(USER, "🏠 Asosiy menyu"))
    davom = [t for t in tekis(tugmalar) if t.startswith("▶️")]
    assert davom == ["▶️ Davom ettirish: Spartak 12-qism"], tugmalar
    matn, _ = yuborilgan(await tap(USER, davom[0]))
    assert "12-qism" in matn

    # --- qidiruv
    matn, tugmalar = yuborilgan(await tap(USER, "spart"))
    assert "1 ta natija" in matn and ["🎬 Spartak"] in tugmalar
    matn, tugmalar = yuborilgan(await tap(USER, "yoqbunaqa"))
    assert "topilmadi" in matn and "✍️ Adminga yozish" in tekis(tugmalar)

    # --- murojaat: user -> admin
    matn, _ = yuborilgan(await tap(USER, "✍️ Adminga yozish"))
    assert "bitta xabarda yozing" in matn
    log = await tap(USER, "qachon yangi qism chiqadi?")
    adminga = [m for m in log if type(m).__name__ == "SendMessage" and m.chat_id == ADMIN_ID][0]
    assert "#m1" in adminga.text and "qachon yangi qism" in adminga.text
    matn, _ = yuborilgan(log)
    assert "adminga yuborildi" in matn
    assert len(await db.unanswered_murojat()) == 1

    # --- admin reply -> user javob oladi
    bot_xabari = raw(ADMIN_ID, adminga.text)
    log = await tap(ADMIN_ID, "ertaga", reply_to_message=bot_xabari)
    userga = [m for m in log if type(m).__name__ == "SendMessage" and m.chat_id == USER][0]
    assert "Admin javobi" in userga.text and "ertaga" in userga.text
    assert await db.unanswered_murojat() == []

    # --- admin panel faqat adminga
    matn, tugmalar = yuborilgan(await tap(ADMIN_ID, "/admin"))
    assert "Admin panel" in matn and ["📊 Statistika", "📨 Tarqatish"] in tugmalar
    bot.session.log.clear()
    await tap(USER, "/admin")
    assert not [m for m in bot.session.log if type(m).__name__ == "SendMessage"]

    # --- admin: serial qo'shish FSM
    matn, tugmalar = yuborilgan(await tap(ADMIN_ID, "➕ Serial qo'shish"))
    assert "1/5" in matn
    assert "✖️ Bekor qilish" in tekis(tugmalar)
    matn, _ = yuborilgan(await tap(ADMIN_ID, "Yangi kino"))
    assert "2/5" in matn
    matn, tugmalar = yuborilgan(await tap(ADMIN_ID, "➖ O'tkazib yuborish"))
    assert "3/5" in matn and "➖ O'tkazib yuborish" in tekis(tugmalar)
    matn, _ = yuborilgan(await tap(ADMIN_ID, "➖ O'tkazib yuborish"))
    assert "4/5" in matn
    matn, _ = yuborilgan(await tap(ADMIN_ID, "komediya"))
    assert "5/5" in matn
    matn, _ = yuborilgan(await tap(ADMIN_ID, "notogri"))
    assert "raqam bilan" in matn
    matn, tugmalar = yuborilgan(await tap(ADMIN_ID, "2024"))
    assert "qo'shildi" in matn and "🎬 Qism qo'shish" in tekis(tugmalar)
    yangi = await db.get_serial_by_name("Yangi kino")
    assert yangi["yil"] == 2024 and yangi["janr"] == "komediya" and yangi["tavsif"] is None

    # --- admin: qism qo'shish (forward)
    matn, tugmalar = yuborilgan(await tap(ADMIN_ID, "🎬 Qism qo'shish"))
    assert "Qaysi serialga" in matn and ["🎬 Yangi kino"] in tugmalar
    matn, tugmalar = yuborilgan(await tap(ADMIN_ID, "🎬 Yangi kino"))
    assert "forward" in matn and "Keyingi qism raqami: <b>1</b>" in matn
    assert "✅ Tugatdim" in tekis(tugmalar)

    # boshqa kanaldan forward -> rad etiladi va kanal ID si ko'rsatiladi
    begona = {
        "forward_origin": {"type": "channel", "chat": {"id": -100999, "type": "channel", "title": "x"},
                           "message_id": 7, "date": int(time.time())},
        "video": {"file_id": "v", "file_unique_id": "u", "width": 1, "height": 1, "duration": 60},
    }
    matn, _ = yuborilgan(await tap(ADMIN_ID, None, **begona))
    assert "-100999" in matn and "boshqa kanaldan" in matn
    assert await db.count_episodes(yangi["id"]) == 0

    # to'g'ri kanaldan forward -> saqlanadi
    tugri = {
        "forward_origin": {"type": "channel",
                           "chat": {"id": ARCHIVE_CHANNEL_ID, "type": "channel", "title": "arxiv"},
                           "message_id": 77, "date": int(time.time())},
        "video": {"file_id": "v", "file_unique_id": "u", "width": 1, "height": 1, "duration": 90},
    }
    matn, _ = yuborilgan(await tap(ADMIN_ID, None, **tugri))
    assert "1-qism</b> saqlandi" in matn
    ep = await db.get_episode(yangi["id"], 1)
    assert ep["kanal_msg_id"] == 77 and ep["davomiyligi"] == 90
    matn, tugmalar = yuborilgan(await tap(ADMIN_ID, "✅ Tugatdim"))
    assert "Admin panel" in matn

    # --- admin: tahrirlash
    await tap(ADMIN_ID, "✏️ Tahrirlash / o'chirish")
    matn, tugmalar = yuborilgan(await tap(ADMIN_ID, "🎬 Yangi kino"))
    assert "Yangi kino" in matn and "🗑 Serialni o'chirish" in tekis(tugmalar)
    matn, _ = yuborilgan(await tap(ADMIN_ID, "✏️ Nom"))
    assert "yangi <b>nom</b>" in matn
    matn, _ = yuborilgan(await tap(ADMIN_ID, "Yangi kino 2"))
    assert "Yangi kino 2" in matn
    assert await db.get_serial_by_name("Yangi kino 2") is not None

    # qism o'chirish
    matn, tugmalar = yuborilgan(await tap(ADMIN_ID, "🗑 Qismlarni o'chirish"))
    assert "🗑 1" in tekis(tugmalar)
    matn, tugmalar = yuborilgan(await tap(ADMIN_ID, "🗑 1"))
    assert "Qismlar yo'q" in matn
    matn, _ = yuborilgan(await tap(ADMIN_ID, "⬅️ Orqaga"))
    assert "Qismlar: 0" in matn

    # serial o'chirish
    matn, tugmalar = yuborilgan(await tap(ADMIN_ID, "🗑 Serialni o'chirish"))
    assert "Davom etamizmi" in matn
    matn, _ = yuborilgan(await tap(ADMIN_ID, "⬅️ Yo'q"))
    assert "Yangi kino 2" in matn
    await tap(ADMIN_ID, "🗑 Serialni o'chirish")
    matn, _ = yuborilgan(await tap(ADMIN_ID, "🗑 Ha, o'chirilsin"))
    assert await db.get_serial_by_name("Yangi kino 2") is None

    # --- admin: statistika
    matn, tugmalar = yuborilgan(await tap(ADMIN_ID, "⬅️ Admin panel"))
    assert "Admin panel" in matn
    matn, _ = yuborilgan(await tap(ADMIN_ID, "📊 Statistika"))
    assert "Foydalanuvchilar: <b>2</b>" in matn and "Spartak" in matn

    # --- admin: tarqatish
    await tap(ADMIN_ID, "⬅️ Admin panel")
    matn, _ = yuborilgan(await tap(ADMIN_ID, "📨 Tarqatish"))
    assert "Tarqatiladigan xabarni" in matn
    matn, tugmalar = yuborilgan(await tap(ADMIN_ID, "Hammaga salom"))
    assert "2</b> ta foydalanuvchiga" in matn and "📨 Yuborish" in tekis(tugmalar)
    log = await tap(ADMIN_ID, "📨 Yuborish")
    nusxalar = [m for m in log if type(m).__name__ == "CopyMessage"]
    assert len(nusxalar) == 2, nusxalar
    matn, _ = yuborilgan(log)
    assert "Yuborildi: 2" in matn

    # --- admin: murojatlar ro'yxati
    mid = await db.add_murojat(USER, "salom admin")
    await tap(ADMIN_ID, "⬅️ Admin panel")
    matn, tugmalar = yuborilgan(await tap(ADMIN_ID, "💬 Murojatlar"))
    assert f"#{mid} · salom admin" in tekis(tugmalar)
    matn, _ = yuborilgan(await tap(ADMIN_ID, f"#{mid} · salom admin"))
    assert f"#m{mid}" in matn and "salom admin" in matn

    # --- admin asosiy menyuga qaytsa oddiy user ekranini ko'radi
    matn, tugmalar = yuborilgan(await tap(ADMIN_ID, "🏠 Asosiy menyu"))
    assert "Assalomu alaykum" in matn and "🎬 Spartak" in tekis(tugmalar)

    # --- bayroqlar o'chiq: yangi tugmalar umuman ko'rinmaydi
    _, tugmalar = yuborilgan(await tap(USER, "/start"))
    assert "➕ Kino taklif qilish" not in tekis(tugmalar), tugmalar
    _, tugmalar = yuborilgan(await tap(ADMIN_ID, "/admin"))
    assert "⬇️ Yuklash" not in tekis(tugmalar), tugmalar
    assert "📥 Takliflar" not in tekis(tugmalar), tugmalar
    from config import FEATURE_TAKLIF, FEATURE_YUKLASH
    assert not FEATURE_TAKLIF and not FEATURE_YUKLASH
    assert [m.__name__ for m in app.ROUTERS] == [
        "handlers.admin", "handlers.kino", "handlers.murojat", "handlers.qidiruv",
    ]

    # --- deeplink
    matn, _ = yuborilgan(await tap(USER, f"/start serial_{sid}"))
    assert "Spartak" in matn and "Qismlar: 12" in matn, matn
    matn, tugmalar = yuborilgan(await tap(USER, f"/start qism_{sid}_2"))
    assert "2-qism" in matn and "Keyingi ➡️" in tekis(tugmalar)
    matn, _ = yuborilgan(await tap(USER, "/start bunaqa_payload_yoq"))
    assert "Assalomu alaykum" in matn
    matn, _ = yuborilgan(await tap(USER, "/start serial_99999"))
    assert "Assalomu alaykum" in matn

    # admin: havola tugmasi
    await tap(ADMIN_ID, "/admin")
    await tap(ADMIN_ID, "✏️ Tahrirlash / o'chirish")
    matn, tugmalar = yuborilgan(await tap(ADMIN_ID, "🎬 Spartak"))
    assert "🔗 Havola" in tekis(tugmalar), tugmalar
    matn, _ = yuborilgan(await tap(ADMIN_ID, "🔗 Havola"))
    assert f"https://t.me/b?start=serial_{sid}" in matn, matn
    assert f"start=qism_{sid}_1" in matn
    matn, _ = yuborilgan(await tap(ADMIN_ID, "⬅️ Orqaga"))
    assert "Spartak" in matn and "Qismlar: 12" in matn

    assert not OCHIRISHLAR, "bot xabar o'chirmasligi kerak"
    print("E2E OK")


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
