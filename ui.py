"""Reply (oddiy) tugmalar va ekran chizish.

Butun navigatsiya reply tugmalar orqali: inline tugma ishlatilmaydi.
Tugma bosilganda bot oddiy matn xabari oladi, shuning uchun routing
shu fayldagi matn konstantalari bo'yicha ketadi.
"""
from html import escape
from math import ceil

from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from config import EPISODES_PER_PAGE, FEATURE_TAKLIF, SERIALS_PER_PAGE

# ----------------------------------------------- tugma matnlari (routing kalitlari)
HOME = "🏠 Asosiy menyu"
BACK = "⬅️ Orqaga"
TO_LIST = "⬅️ Ro'yxatga"
PREV = "⬅️"
NEXT = "➡️"
MUROJAT = "✍️ Adminga yozish"
PREV_EP = "⬅️ Oldingi"
EPISODES = "📋 Qismlar"
NEXT_EP = "Keyingi ➡️"
CANCEL = "✖️ Bekor qilish"
SKIP = "➖ O'tkazib yuborish"
ADMIN_BACK = "⬅️ Admin panel"
DONE = "✅ Tugatdim"

# Modul tugmalari — mos bayroq o'chiq bo'lsa umuman chizilmaydi
TAKLIF_QIL = "➕ Kino taklif qilish"   # FEATURE_TAKLIF (user)
TAKLIFLAR = "📥 Takliflar"             # FEATURE_TAKLIF (admin)
YUKLASH = "⬇️ Yuklash"                 # FEATURE_YUKLASH (admin)
LINK = "🔗 Link yuborish"
NAVBAT = "📋 Navbat holati"
XATOLAR = "⚠️ Xatolar"
HAVOLA = "🔗 Havola"
TASDIQLASH = "✅ Tasdiqlash"
RAD_ETISH = "❌ Rad etish"

SERIAL_PREFIX = "🎬 "        # serial tugmalari: "🎬 <nom>"
DAVOM_PREFIX = "▶️ Davom ettirish"
QISM_SUFFIX = "-qism"        # qism tugmalari: "<N>-qism"
OCHIR_PREFIX = "🗑 "         # admin: qism o'chirish tugmalari


async def havola(bot, payload: str) -> str:
    """Deeplink: https://t.me/<bot>?start=<payload>  (bot.me() keshlanadi)."""
    me = await bot.me()
    return f"https://t.me/{me.username}?start={payload}"


def esc(matn) -> str:
    """HTML parse_mode uchun xavfsiz matn."""
    return escape(str(matn or ""))


def kb(*qatorlar: list[str]) -> ReplyKeyboardMarkup:
    """Bo'sh qatorlarni tashlab, reply klaviatura yig'adi."""
    tugmalar = [[KeyboardButton(text=t) for t in qator] for qator in qatorlar if qator]
    return ReplyKeyboardMarkup(
        keyboard=tugmalar,
        resize_keyboard=True,
        input_field_placeholder="Serial nomini yozib qidiring…",
    )


def rows(nomlar: list[str], nechta: int) -> list[list[str]]:
    """Tugmalarni qatorlarga bo'ladi."""
    return [nomlar[i : i + nechta] for i in range(0, len(nomlar), nechta)]


def page_row(page: int, jami: int, per_page: int) -> list[str]:
    """⬅️ 1/3 ➡️ qatori. Bitta sahifa bo'lsa — bo'sh."""
    sahifalar = max(1, ceil(jami / per_page))
    if sahifalar == 1:
        return []
    qator = []
    if page > 0:
        qator.append(PREV)
    qator.append(f"{page + 1}/{sahifalar}")
    if page < sahifalar - 1:
        qator.append(NEXT)
    return qator


# ------------------------------------------------------------- klaviaturalar

def main_menu_kb(serials, page: int, jami: int, davom=None) -> ReplyKeyboardMarkup:
    qatorlar = []
    if davom:
        qatorlar.append([f"{DAVOM_PREFIX}: {davom['nom']} {davom['oxirgi_qism']}{QISM_SUFFIX}"])
    qatorlar += [[SERIAL_PREFIX + s["nom"]] for s in serials]
    qatorlar.append(page_row(page, jami, SERIALS_PER_PAGE))
    if FEATURE_TAKLIF:
        qatorlar.append([TAKLIF_QIL])
    qatorlar.append([MUROJAT])
    return kb(*qatorlar)


def serial_kb(episodes, page: int, jami: int) -> ReplyKeyboardMarkup:
    nomlar = [f"{e['qism_raqami']}{QISM_SUFFIX}" for e in episodes]
    return kb(
        *rows(nomlar, 4),
        page_row(page, jami, EPISODES_PER_PAGE),
        [TO_LIST, HOME],
    )


def episode_kb(oldingi: int | None, keyingi: int | None) -> ReplyKeyboardMarkup:
    qator = []
    if oldingi is not None:
        qator.append(PREV_EP)
    qator.append(EPISODES)
    if keyingi is not None:
        qator.append(NEXT_EP)
    return kb(qator, [HOME])


def simple_kb(*tugmalar: str) -> ReplyKeyboardMarkup:
    """Tupik ekran bo'lmasligi uchun — har doim asosiy menyu tugmasi bilan."""
    return kb(*[[t] for t in tugmalar], [HOME])


# ----------------------------------------------------------------- ekran

async def kb_if_new(state: FSMContext, keyboard: ReplyKeyboardMarkup) -> ReplyKeyboardMarkup | None:
    """Klaviatura o'zgarmagan bo'lsa None qaytaradi.

    reply_markup yuborilmasa Telegram mavjud klaviaturani o'z holicha qoldiradi —
    shuning uchun tugmalar har xabarda yopilib-ochilmaydi, "sakramaydi".
    """
    imzo = "|".join(",".join(b.text for b in qator) for qator in keyboard.keyboard)
    malumot = await state.get_data()
    if malumot.get("kb_imzo") == imzo:
        return None
    await state.update_data(kb_imzo=imzo)
    return keyboard


async def screen(
    message: Message,
    state: FSMContext,
    matn: str,
    keyboard: ReplyKeyboardMarkup,
    rasm: str | None = None,
) -> Message:
    """Yangi ekran yuboradi.

    Hech narsa o'chirilmaydi: foydalanuvchi yozgan xabar ham, botning eski
    ekrani ham chatda qoladi — oddiy yozishmadek. Klaviatura esa faqat
    o'zgarganda qayta yuboriladi.
    """
    km = await kb_if_new(state, keyboard)
    if rasm:
        return await message.answer_photo(rasm, caption=matn, reply_markup=km)
    return await message.answer(matn, reply_markup=km)


async def set_nav(state: FSMContext, ekran: str, **qiymatlar) -> None:
    """Joriy ekranni eslab qoladi — ⬅️/➡️ va qism tugmalari shunga qarab ishlaydi."""
    await state.update_data(nav_ekran=ekran, **qiymatlar)


def ekran(*nomlar: str):
    """Filtr: foydalanuvchi shu ekranlardan birida turganda ishlaydi."""

    async def tekshir(message: Message, state: FSMContext) -> bool:
        malumot = await state.get_data()
        return malumot.get("nav_ekran") in nomlar

    return tekshir
