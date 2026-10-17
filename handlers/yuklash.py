"""Saytdan kino yuklash moduli (FEATURE_YUKLASH).

Admin link tashlaydi -> navbatga tushadi -> fon vazifasi birma-bir yuklaydi ->
arxiv kanalga yuboradi va `kanal_msg_id` ni saqlaydi. Bir xil link ikkinchi
marta yuklanmaydi: `yuklash_navbat` dagi 'tayyor' yozuv kesh bo'lib ishlaydi.

Butun modul admin uchun — router AdminOnly middleware bilan yopilgan.
Parserni almashtirish uchun pastdagi bitta import qatorini o'zgartiring.
"""
import asyncio
import logging
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile, Message

import db
import ui
from config import ADMIN_ID, ARCHIVE_CHANNEL_ID, TMP_DIR
from middlewares import AdminOnly
from parsers import namuna as parser  # <- aniq sayt parseri shu yerda almashtiriladi

router = Router(name="yuklash")
router.message.outer_middleware(AdminOnly())

log = logging.getLogger(__name__)

NAVBAT_KUTISH = 5  # navbat bo'sh bo'lsa shuncha soniya kutiladi
_ishchi: asyncio.Task | None = None

MENU_MATN = (
    "⬇️ <b>Yuklash</b>\n\n"
    "Link yuboring — navbatga tushadi va fon rejimida yuklanadi.\n"
    "Bir vaqtda bitta yuklash ketadi, bir xil link qayta yuklanmaydi."
)


class Yuklash(StatesGroup):
    link = State()


def menu_kb():
    return ui.kb([ui.LINK], [ui.NAVBAT, ui.XATOLAR], [ui.ADMIN_BACK, ui.HOME])


# ------------------------------------------------------------- ekranlar

@router.message(F.text == ui.YUKLASH)
async def menu(message: Message, state: FSMContext):
    await state.set_state(None)
    await ui.set_nav(state, "y_menu")
    await ui.screen(message, state, MENU_MATN, menu_kb())


@router.message(F.text == ui.LINK)
async def link_sorash(message: Message, state: FSMContext):
    await ui.set_nav(state, "y_link")
    await ui.screen(
        message,
        state,
        "🔗 Yuklash uchun havolani yuboring.\nKetma-ket bir nechta link yuborsangiz ham bo'ladi.",
        ui.kb([ui.NAVBAT, ui.XATOLAR], [ui.CANCEL], [ui.HOME]),
    )
    await state.set_state(Yuklash.link)


@router.message(F.text == ui.NAVBAT)
async def navbat_holati(message: Message, state: FSMContext):
    sanoq = await db.navbat_sanoq()
    qatorlar = [
        "📋 <b>Navbat holati</b>",
        "",
        f"⏳ Navbatda: <b>{sanoq.get('navbatda', 0)}</b>",
        f"⬇️ Yuklanmoqda: <b>{sanoq.get('yuklanmoqda', 0)}</b>",
        f"✅ Tayyor: <b>{sanoq.get('tayyor', 0)}</b>",
        f"⚠️ Xato: <b>{sanoq.get('xato', 0)}</b>",
    ]
    kutayotganlar = await db.navbat_royxat("navbatda", 5)
    if kutayotganlar:
        qatorlar += ["", "<b>Navbatdagilar:</b>"]
        qatorlar += [f"#{r['id']} · {ui.esc(r['manba_url'])}" for r in kutayotganlar]
    await ui.screen(message, state, "\n".join(qatorlar), menu_kb())


@router.message(F.text == ui.XATOLAR)
async def xatolar(message: Message, state: FSMContext):
    satrlar = await db.navbat_royxat("xato", 10)
    if satrlar:
        qatorlar = ["⚠️ <b>Oxirgi xatolar</b>", ""]
        for r in satrlar:
            qatorlar.append(f"#{r['id']} · {ui.esc(r['manba_url'])}")
            qatorlar.append(f"   <i>{ui.esc(r['xato_matni'])}</i>")
    else:
        qatorlar = ["✅ Xato yo'q."]
    await ui.screen(message, state, "\n".join(qatorlar), menu_kb())


@router.message(Yuklash.link, F.text)
async def link_qabul(message: Message, state: FSMContext):
    url = message.text.strip()
    if not url.startswith(("http://", "https://")):
        await ui.screen(
            message,
            state,
            "⚠️ Bu havolaga o'xshamaydi. <code>http://</code> yoki <code>https://</code> bilan boshlanishi kerak.",
            ui.kb([ui.NAVBAT, ui.XATOLAR], [ui.CANCEL], [ui.HOME]),
        )
        return

    kesh = await db.navbat_kesh(url)
    if kesh is not None:
        await ui.screen(
            message,
            state,
            f"♻️ Bu link avval yuklangan (#{kesh['id']}), qayta yuklanmaydi.\n"
            f"Arxiv kanaldagi xabar: <code>{kesh['kanal_msg_id']}</code>",
            ui.kb([ui.NAVBAT, ui.XATOLAR], [ui.CANCEL], [ui.HOME]),
        )
        return

    mavjud = await db.navbat_bormi(url)
    if mavjud is not None:
        await ui.screen(
            message,
            state,
            f"⏳ Bu link allaqachon navbatda (#{mavjud['id']}, holat: {mavjud['holat']}).",
            ui.kb([ui.NAVBAT, ui.XATOLAR], [ui.CANCEL], [ui.HOME]),
        )
        return

    navbat_id = await db.navbat_qosh(url)
    await ui.screen(
        message,
        state,
        f"✅ Navbatga qo'shildi: #{navbat_id}\nTayyor bo'lgach xabar beraman.",
        ui.kb([ui.NAVBAT, ui.XATOLAR], [ui.CANCEL], [ui.HOME]),
    )


# -------------------------------------------------------- fon vazifasi

def tmp_tozala(navbat_id: int, yakuniy: str | None = None) -> None:
    """Vaqtinchalik fayllarni o'chiradi."""
    if yakuniy:
        Path(yakuniy).unlink(missing_ok=True)
    for fayl in Path(TMP_DIR).glob(f"{navbat_id}.*"):
        fayl.unlink(missing_ok=True)


async def bajarish(bot: Bot, vazifa) -> None:
    navbat_id, url = vazifa["id"], vazifa["manba_url"]
    await db.navbat_holat(navbat_id, "yuklanmoqda")
    nishon = str(Path(TMP_DIR) / f"{navbat_id}.mp4")
    yakuniy = None
    try:
        # parser sinxron — event loop ni bloklamasligi uchun alohida threadda
        yakuniy = await asyncio.to_thread(parser.yuklab_ol, url, nishon)
        xabar = await bot.send_video(
            ARCHIVE_CHANNEL_ID, FSInputFile(yakuniy), caption=url, supports_streaming=True
        )
        await db.navbat_holat(navbat_id, "tayyor", kanal_msg_id=xabar.message_id)
        await bot.send_message(
            ADMIN_ID,
            f"✅ Yuklandi #{navbat_id}\n{ui.esc(url)}\n"
            f"Arxiv xabar: <code>{xabar.message_id}</code>",
        )
    except Exception as xato:  # navbat to'xtamaydi
        matn = f"{type(xato).__name__}: {xato}"
        log.warning("yuklash xatosi #%s: %s", navbat_id, matn)
        await db.navbat_holat(navbat_id, "xato", xato_matni=matn[:500])
        await bot.send_message(ADMIN_ID, f"⚠️ Xato #{navbat_id}\n{ui.esc(url)}\n<i>{ui.esc(matn[:300])}</i>")
    finally:
        tmp_tozala(navbat_id, yakuniy)


async def navbat_ishchisi(bot: Bot) -> None:
    """Bir vaqtda faqat bitta yuklash — navbatni birma-bir oladi."""
    await db.navbat_tiklash()  # yarim qolganlarni qaytaramiz
    while True:
        try:
            vazifa = await db.navbat_keyingi()
            if vazifa is None:
                await asyncio.sleep(NAVBAT_KUTISH)
                continue
            await bajarish(bot, vazifa)
        except asyncio.CancelledError:
            raise
        except Exception:  # ishchi hech qachon o'lmasin
            log.exception("navbat ishchisida kutilmagan xato")
            await asyncio.sleep(NAVBAT_KUTISH)


@router.startup()
async def ishga_tushir(bot: Bot, **_) -> None:
    global _ishchi
    Path(TMP_DIR).mkdir(parents=True, exist_ok=True)
    _ishchi = asyncio.create_task(navbat_ishchisi(bot))
    log.info("yuklash moduli yoqildi, navbat ishchisi ishga tushdi")


@router.shutdown()
async def to_xtatish(**_) -> None:
    if _ishchi is not None:
        _ishchi.cancel()
