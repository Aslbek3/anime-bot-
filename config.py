"""Sozlamalar — hammasi .env dan o'qiladi."""
import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
# Videolar saqlanadigan arxiv kanal (bot u yerda admin bo'lishi shart)
ARCHIVE_CHANNEL_ID = int(os.getenv("ARCHIVE_CHANNEL_ID", "0"))
DB_PATH = os.getenv("DB_PATH", "qogoz.db")

# Sahifalash
SERIALS_PER_PAGE = 8
EPISODES_PER_PAGE = 8

# Tarqatish: bir to'plamdagi xabarlar soni va to'plamlar orasidagi tanaffus
BROADCAST_CHUNK = 25
BROADCAST_PAUSE = 1.0

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN .env faylda ko'rsatilmagan")
