"""CSV import/eksport (FEATURE_CSV).

Eksport: seriallar va qismlar ikkita CSV fayl bo'lib keladi.
Import: seriallar CSV sini yuborsangiz, yo'qlari qo'shiladi
(ustunlar: nom;tavsif;janr;yil). Mavjud nomlar o'tkazib yuboriladi.
"""
import csv
import io
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, Message

import db
import ui
from middlewares import AdminOnly

router = Router(name="csv_almash")
router.message.outer_middleware(AdminOnly())
log = logging.getLogger(__name__)

AJRATGICH = ";"
CHEGARA = 2 * 1024 * 1024   # 2 MB dan katta faylni olmaymiz


class CSVImport(StatesGroup):
    fayl = State()


def _csv(satrlar, ustunlar: list[str]) -> bytes:
    bufer = io.StringIO()
    yozuvchi = csv.writer(bufer, delimiter=AJRATGICH, lineterminator="\n")
    yozuvchi.writerow(ustunlar)
    for satr in satrlar:
        yozuvchi.writerow([satr[u] if u in satr.keys() else "" for u in ustunlar])
    return bufer.getvalue().encode("utf-8-sig")


@router.message(F.text == ui.CSV)
async def menyu(message: Message, state: FSMContext):
    await state.set_state(None)
    await ui.set_nav(state, "a_csv")
    await ui.screen(
        message,
        state,
        "🗂 <b>CSV</b>\n\nEksport — barcha seriallar va qismlar fayl bo'lib keladi.\n"
        "Import — seriallar CSV sini yuborasiz, yangilari qo'shiladi.",
        ui.kb([ui.CSV_EKSPORT], [ui.CSV_IMPORT], [ui.ADMIN_BACK, ui.HOME]),
    )


@router.message(F.text == ui.CSV_EKSPORT)
async def eksport(message: Message, state: FSMContext):
    seriallar = await db.barcha_seriallar()
    qismlar = await db.barcha_episodes()
    await message.answer_document(
        BufferedInputFile(
            _csv(seriallar, ["id", "nom", "tavsif", "janr", "yil", "holat", "created_at"]),
            filename="seriallar.csv",
        ),
        caption=f"🗂 {len(seriallar)} ta serial",
    )
    await message.answer_document(
        BufferedInputFile(
            _csv(qismlar, ["id", "serial_id", "fasl", "qism_raqami", "nom", "kanal_msg_id", "davomiyligi"]),
            filename="qismlar.csv",
        ),
        caption=f"🗂 {len(qismlar)} ta qism",
    )


@router.message(F.text == ui.CSV_IMPORT)
async def import_sorash(message: Message, state: FSMContext):
    await ui.screen(
        message,
        state,
        "⬆️ Seriallar CSV faylini yuboring.\nUstunlar: <code>nom;tavsif;janr;yil</code>",
        ui.kb([ui.CANCEL], [ui.HOME]),
    )
    await state.set_state(CSVImport.fayl)


@router.message(CSVImport.fayl, F.document)
async def import_qilish(message: Message, state: FSMContext, bot: Bot):
    hujjat = message.document
    if hujjat.file_size and hujjat.file_size > CHEGARA:
        await message.answer("⚠️ Fayl juda katta (2 MB dan oshmasin).")
        return

    bufer = io.BytesIO()
    await bot.download(hujjat, destination=bufer)
    matn = bufer.getvalue().decode("utf-8-sig", errors="replace")
    oquvchi = csv.DictReader(io.StringIO(matn), delimiter=AJRATGICH)

    qoshildi = otkazildi = xato = 0
    for satr in oquvchi:
        nom = (satr.get("nom") or "").strip()
        if not nom:
            xato += 1
            continue
        if await db.get_serial_by_name(nom):
            otkazildi += 1
            continue
        yil = (satr.get("yil") or "").strip()
        await db.add_serial(
            nom,
            (satr.get("tavsif") or "").strip() or None,
            None,
            (satr.get("janr") or "").strip() or None,
            int(yil) if yil.isdigit() else None,
        )
        qoshildi += 1

    await state.set_state(None)
    await ui.screen(
        message,
        state,
        f"🗂 <b>Import tugadi</b>\n✅ Qo'shildi: {qoshildi}\n↩️ Mavjud edi: {otkazildi}\n⚠️ Xato satr: {xato}",
        ui.kb([ui.CSV], [ui.ADMIN_BACK], [ui.HOME]),
    )
