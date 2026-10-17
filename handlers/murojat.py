"""Murojaat: user yozadi -> admin oladi -> admin reply qilsa javob userga qaytadi."""
import re

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

import db
import ui
from config import ADMIN_ID

router = Router(name="murojat")

# Admin xabaridagi "#m12" belgisi orqali qaysi murojaatga javob berilayotganini bilamiz
TAG = re.compile(r"#m(\d+)")

SORASH = (
    "✍️ Savolingiz yoki taklifingizni bitta xabarda yozing.\n"
    "Admin javob bergach, bot sizga xabar qiladi."
)


class Murojat(StatesGroup):
    matn = State()


async def sorash_ekrani(message: Message, state: FSMContext):
    await ui.set_nav(state, "murojat")
    await ui.screen(message, state, SORASH, ui.simple_kb())
    await state.set_state(Murojat.matn)


@router.message(F.text == ui.MUROJAT)
async def sorash(message: Message, state: FSMContext):
    await sorash_ekrani(message, state)


@router.message(Command("murojat"))
async def sorash_buyruq(message: Message, state: FSMContext):
    await sorash_ekrani(message, state)


@router.message(Murojat.matn, F.text)
async def qabul(message: Message, state: FSMContext, bot: Bot):
    matn = message.text.strip()
    murojat_id = await db.add_murojat(message.from_user.id, matn)

    user = message.from_user
    kim = f'<a href="tg://user?id={user.id}">{ui.esc(user.full_name)}</a>'
    if user.username:
        kim += f" (@{user.username})"
    await bot.send_message(
        ADMIN_ID,
        f"📩 <b>Yangi murojaat</b> #m{murojat_id}\n"
        f"👤 {kim} · <code>{user.id}</code>\n\n"
        f"{ui.esc(matn)}\n\n"
        f"<i>Javob berish uchun shu xabarga reply qiling.</i>",
    )
    await state.set_state(None)
    await ui.screen(
        message, state, "✅ Murojaatingiz adminga yuborildi.", ui.simple_kb()
    )


def admin_javobi(message: Message) -> dict | bool:
    """Admin #m<id> belgisi bor xabarga reply qilgan bo'lsa — murojaat javobi."""
    if message.from_user.id != ADMIN_ID or message.reply_to_message is None:
        return False
    manba = message.reply_to_message.text or message.reply_to_message.caption or ""
    topildi = TAG.search(manba)
    return {"murojat_id": int(topildi.group(1))} if topildi else False


@router.message(StateFilter(None), admin_javobi, F.text)
async def javob_berish(message: Message, murojat_id: int, bot: Bot):
    murojaat = await db.get_murojat(murojat_id)
    if murojaat is None:
        await message.reply("⚠️ Bu murojaat topilmadi.")
        return

    javob = message.text.strip()
    try:
        await bot.send_message(
            murojaat["user_id"],
            f"💬 <b>Admin javobi:</b>\n\n{ui.esc(javob)}\n\n"
            f"<i>Sizning murojaatingiz:</i> {ui.esc(murojaat['matn'])}",
        )
    except Exception as xato:  # user botni bloklagan bo'lishi mumkin
        await message.reply(f"⚠️ Javob yetib bormadi: {xato}")
        return

    await db.answer_murojat(murojat_id, javob)
    await message.reply("✅ Javob yuborildi.")
