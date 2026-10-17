"""Sozlamalar — hammasi .env dan o'qiladi."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
# Videolar saqlanadigan arxiv kanal (bot u yerda admin bo'lishi shart)
ARCHIVE_CHANNEL_ID = int(os.getenv("ARCHIVE_CHANNEL_ID", "0"))
DB_PATH = os.getenv("DB_PATH", "qogoz.db")

# Vaqtinchalik yuklab olingan fayllar (yuklash tugagach darhol o'chiriladi)
TMP_DIR = os.getenv("TMP_DIR", str(Path(__file__).parent / "tmp"))


def bayroq(nom: str, standart: str = "false") -> bool:
    """.env dagi true/1/yes qiymatlarini bool ga aylantiradi."""
    return os.getenv(nom, standart).strip().lower() in {"true", "1", "yes", "ha"}


# Modul bayroqlari: false bo'lsa router ham, tugmalar ham umuman ko'rinmaydi
FEATURE_YUKLASH = bayroq("FEATURE_YUKLASH")
FEATURE_TAKLIF = bayroq("FEATURE_TAKLIF")

# Sahifalash
SERIALS_PER_PAGE = 8
EPISODES_PER_PAGE = 8

# Tarqatish: bir to'plamdagi xabarlar soni va to'plamlar orasidagi tanaffus
BROADCAST_CHUNK = 25
BROADCAST_PAUSE = 1.0

# Taklif: bitta user kuniga nechta taklif yubora oladi
TAKLIF_KUNLIK_LIMIT = 3

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN .env faylda ko'rsatilmagan")
