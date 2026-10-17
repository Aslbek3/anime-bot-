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


# Modul bayroqlari: false bo'lsa router ham, tugmalar ham umuman ko'rinmaydi.
# Har biri alohida fayl — handlers/<nom>.py
FEATURE_YUKLASH = bayroq("FEATURE_YUKLASH")            # handlers/yuklash.py
FEATURE_TAKLIF = bayroq("FEATURE_TAKLIF")              # handlers/taklif.py
FEATURE_BILDIRISHNOMA = bayroq("FEATURE_BILDIRISHNOMA")  # handlers/bildirishnoma.py
FEATURE_RAQAM = bayroq("FEATURE_RAQAM")                # handlers/qism_raqam.py
FEATURE_ROYXATIM = bayroq("FEATURE_ROYXATIM")          # handlers/royxatim.py
FEATURE_ULASHISH = bayroq("FEATURE_ULASHISH")          # handlers/ulashish.py
FEATURE_JANR = bayroq("FEATURE_JANR")                  # handlers/janrlar.py
FEATURE_OBUNA = bayroq("FEATURE_OBUNA")                # handlers/obuna.py
FEATURE_AVTOPOST = bayroq("FEATURE_AVTOPOST")          # handlers/avtopost.py
FEATURE_ZAXIRA = bayroq("FEATURE_ZAXIRA")              # handlers/zaxira.py
FEATURE_ANTIFLOOD = bayroq("FEATURE_ANTIFLOOD")        # middlewares.py

# Majburiy obuna: vergul bilan ajratilgan kanallar (@nom yoki -100...)
OBUNA_KANALLAR = [k.strip() for k in os.getenv("OBUNA_KANALLAR", "").split(",") if k.strip()]
OBUNA_KESH = 300          # a'zolik tekshiruvi shuncha soniya keshlanadi

# Avtopost: yangi serial/qism e'lon qilinadigan ochiq kanal
POST_CHANNEL_ID = int(os.getenv("POST_CHANNEL_ID", "0") or 0)

# Zaxira: har necha soatda va nechtasini saqlash
ZAXIRA_SOAT = int(os.getenv("ZAXIRA_SOAT", "24"))
ZAXIRA_SAQLASH = int(os.getenv("ZAXIRA_SAQLASH", "7"))
ZAXIRA_DIR = os.getenv("ZAXIRA_DIR", str(Path(__file__).parent / "backup"))

# Antiflood: bitta userdan shuncha soniyada bitta update
ANTIFLOOD_INTERVAL = float(os.getenv("ANTIFLOOD_INTERVAL", "0.4"))

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
