"""Mening ro'yxatim (FEATURE_ROYXATIM).

Asosiy menyudagi "📺 Mening ro'yxatim" — foydalanuvchi ko'rayotgan barcha
seriallar (progress jadvalidan), eng oxirgi ko'rilgani birinchi.
Tugma bosilsa o'sha serialning to'xtagan qismi yuboriladi.

Router `kino` dan KEYIN ulanadi: "▶️ Davom ettirish: ..." tugmasini
avval kino oladi, qolgan "▶️ ..." tugmalari shu modulga tushadi.
"""
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
import ui
from handlers.kino import send_episode, show_main

router = Router(name="royxatim")

AJRATGICH = " · "


def tugma_matni(yozuv) -> str:
    return f"{ui.ROYXAT_PREFIX}{yozuv['nom']}{AJRATGICH}{yozuv['oxirgi_qism']}{ui.QISM_SUFFIX}"


@router.message(F.text == ui.ROYXATIM)
async def royxat(message: Message, state: FSMContext):
    yozuvlar = await db.progress_royxati(message.from_user.id)
    if not yozuvlar:
        await ui.set_nav(state, "royxatim")
        await ui.screen(
            message,
            state,
            "📺 Hali hech qanday serialni boshlamagansiz.",
            ui.kb([ui.HOME]),
        )
        return

    await ui.set_nav(state, "royxatim")
    await ui.screen(
        message,
        state,
        f"📺 <b>Mening ro'yxatim</b> — {len(yozuvlar)} ta serial.\n"
        "Davom ettirish uchun tanlang:",
        ui.kb(*[[tugma_matni(y)] for y in yozuvlar], [ui.HOME]),
    )


@router.message(F.text.startswith(ui.ROYXAT_PREFIX), ui.ekran("royxatim"))
async def davom(message: Message, state: FSMContext, bot: Bot):
    matn = message.text[len(ui.ROYXAT_PREFIX):]
    nom, _, qism_matni = matn.rpartition(AJRATGICH)
    serial = await db.get_serial_by_name(nom.strip())
    qism = qism_matni.replace(ui.QISM_SUFFIX, "").strip()
    if serial is None or not qism.isdigit():
        await show_main(message, state)
        return
    await send_episode(message, state, bot, serial["id"], int(qism))
