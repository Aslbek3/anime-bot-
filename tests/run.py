"""Barcha sinovlarni ishga tushiradi:  python tests/run.py

Bayroqlar import vaqtida o'qilgani uchun har bir holat alohida jarayonda
ishlaydi. Baza vaqtinchalik faylda — loyihadagi qogoz.db ga tegilmaydi.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ILDIZ = Path(__file__).resolve().parent.parent

ASOSIY = {
    "BOT_TOKEN": "42:TEST",
    "ADMIN_ID": "1",
    "ARCHIVE_CHANNEL_ID": "-100123",
    "PYTHONUNBUFFERED": "1",
}

HOLATLAR = [
    ("bayroqlar o'chiq", "tests/test_ochiq.py", {}),
    (
        "bayroqlar yoqiq",
        "tests/test_yoqiq.py",
        {"FEATURE_YUKLASH": "true", "FEATURE_TAKLIF": "true"},
    ),
    (
        "hamma modullar yoqiq",
        "tests/test_hammasi.py",
        {
            "FEATURE_YUKLASH": "true",
            "FEATURE_TAKLIF": "true",
            "FEATURE_BILDIRISHNOMA": "true",
            "FEATURE_RAQAM": "true",
            "FEATURE_ROYXATIM": "true",
            "FEATURE_ULASHISH": "true",
            "FEATURE_JANR": "true",
            "FEATURE_OBUNA": "true",
            "FEATURE_AVTOPOST": "true",
            "FEATURE_ZAXIRA": "true",
            "FEATURE_ANTIFLOOD": "true",
            "OBUNA_KANALLAR": "@test_kanal",
            "POST_CHANNEL_ID": "-100777",
            "ANTIFLOOD_INTERVAL": "0.4",
        },
    ),
    (
        "ikkinchi to'plam yoqiq",
        "tests/test_toplam2.py",
        {
            "FEATURE_KANAL_IMPORT": "true",
            "FEATURE_FUZZY": "true",
            "FEATURE_BUYRUQLAR": "true",
            "FEATURE_INLINE": "true",
            "FEATURE_JURNAL": "true",
            "FEATURE_SQLITE_FSM": "true",
            "FEATURE_KORILGAN": "true",
            "FEATURE_QIDIRUV_JURNALI": "true",
            "FEATURE_KUZATISH": "true",
            "FEATURE_FASL": "true",
            "FEATURE_MANBA": "true",
            "FEATURE_QISM_ALMASH": "true",
            "FEATURE_REJA": "true",
            "FEATURE_BAHO": "true",
            "FEATURE_KASHFIYOT": "true",
            "FEATURE_TIL": "true",
            "FEATURE_CSV": "true",
            "FEATURE_TUR": "true",
            "LOG_CHANNEL_ID": "-100555",
        },
    ),
]


def main() -> int:
    xatolar = 0
    with tempfile.TemporaryDirectory() as papka:
        for nom, fayl, qoshimcha in HOLATLAR:
            muhit = {**os.environ, **ASOSIY, **qoshimcha}
            muhit["DB_PATH"] = str(Path(papka) / f"{Path(fayl).stem}.db")
            print(f"\n=== {nom} ===", flush=True)
            natija = subprocess.run([sys.executable, fayl], cwd=ILDIZ, env=muhit)
            xatolar += natija.returncode != 0
    print("\nHAMMASI O'TDI" if not xatolar else f"\n{xatolar} ta sinov yiqildi")
    return 1 if xatolar else 0


if __name__ == "__main__":
    raise SystemExit(main())
