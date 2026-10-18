"""SQLite qatlami. Bitta ochiq ulanish, barcha so'rovlar shu faylda."""
import aiosqlite

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS serials (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nom             TEXT NOT NULL,
    tavsif          TEXT,
    poster_file_id  TEXT,
    janr            TEXT,
    yil             INTEGER,
    holat           TEXT DEFAULT 'tasdiqlangan',   -- tasdiqlangan / kutilmoqda (hozircha ishlatilmaydi)
    qoshgan_user_id INTEGER,                       -- hozircha ishlatilmaydi
    manba_url       TEXT,                          -- hozircha ishlatilmaydi
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS episodes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    serial_id     INTEGER NOT NULL REFERENCES serials(id) ON DELETE CASCADE,
    qism_raqami   INTEGER NOT NULL,
    nom           TEXT,
    kanal_msg_id  INTEGER NOT NULL,
    davomiyligi   INTEGER,
    fasl          INTEGER DEFAULT 1,
    UNIQUE (serial_id, fasl, qism_raqami)
);

CREATE TABLE IF NOT EXISTS users (
    user_id        INTEGER PRIMARY KEY,
    username       TEXT,
    ism            TEXT,
    til            TEXT DEFAULT 'uz',
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
    oxirgi_faollik TEXT DEFAULT CURRENT_TIMESTAMP,
    faol           INTEGER DEFAULT 1        -- 0 = botni bloklagan
);

CREATE TABLE IF NOT EXISTS progress (
    user_id      INTEGER NOT NULL,
    serial_id    INTEGER NOT NULL REFERENCES serials(id) ON DELETE CASCADE,
    oxirgi_qism  INTEGER NOT NULL,
    yangilangan  TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, serial_id)
);

CREATE TABLE IF NOT EXISTS murojat (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    matn       TEXT NOT NULL,
    javob      TEXT,
    holat      TEXT DEFAULT 'yangi',   -- yangi / javob_berilgan
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS yuklash_navbat (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    manba_url    TEXT NOT NULL,
    serial_id    INTEGER REFERENCES serials(id) ON DELETE SET NULL,
    qism_raqami  INTEGER,
    holat        TEXT DEFAULT 'navbatda',   -- navbatda / yuklanmoqda / tayyor / xato
    kanal_msg_id INTEGER,
    xato_matni   TEXT,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
    tugagan_at   TEXT
);

CREATE INDEX IF NOT EXISTS idx_navbat_url ON yuklash_navbat(manba_url);
CREATE INDEX IF NOT EXISTS idx_navbat_holat ON yuklash_navbat(holat, id);
CREATE TABLE IF NOT EXISTS fsm (
    kalit    TEXT PRIMARY KEY,
    holat    TEXT,
    malumot  TEXT
);

CREATE TABLE IF NOT EXISTS kuzatuv (
    user_id    INTEGER NOT NULL,
    serial_id  INTEGER NOT NULL REFERENCES serials(id) ON DELETE CASCADE,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, serial_id)
);

CREATE TABLE IF NOT EXISTS baholar (
    user_id    INTEGER NOT NULL,
    serial_id  INTEGER NOT NULL REFERENCES serials(id) ON DELETE CASCADE,
    baho       INTEGER NOT NULL,          -- 1 yoki -1
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, serial_id)
);

CREATE TABLE IF NOT EXISTS qidiruvlar (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    soz        TEXT NOT NULL,
    user_id    INTEGER,
    topildi    INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS manbalar (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    manba      TEXT NOT NULL,
    user_id    INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rejalar (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id    INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    vaqt       TEXT NOT NULL,             -- "2026-10-18 20:00"
    holat      TEXT DEFAULT 'kutilmoqda', -- kutilmoqda / yuborildi / bekor
    natija     TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_qidiruvlar ON qidiruvlar(topildi, created_at);
CREATE INDEX IF NOT EXISTS idx_rejalar ON rejalar(holat, vaqt);
CREATE INDEX IF NOT EXISTS idx_episodes_serial ON episodes(serial_id, qism_raqami);
CREATE INDEX IF NOT EXISTS idx_progress_user ON progress(user_id, yangilangan);
"""

# Mavjud bazaga keyin qo'shilgan ustunlar: init_db avtomatik ALTER qiladi
YANGI_USTUNLAR = {
    "users": {"faol": "INTEGER DEFAULT 1"},
    "episodes": {"fasl": "INTEGER DEFAULT 1"},
    "serials": {"turi": "TEXT DEFAULT 'serial'"},   # 'kino' yoki 'serial'
}

_db: aiosqlite.Connection | None = None


async def init_db() -> None:
    global _db
    _db = await aiosqlite.connect(DB_PATH)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA foreign_keys = ON")
    await _db.executescript(SCHEMA)
    await _db.commit()
    await migratsiya()


async def migratsiya() -> None:
    """Yetishmayotgan ustunlarni qo'shadi — qo'lda ALTER TABLE qilish shart emas."""
    for jadval, ustunlar in YANGI_USTUNLAR.items():
        mavjud = {r["name"] for r in await _all(f"PRAGMA table_info({jadval})")}
        for nom, tur in ustunlar.items():
            if nom not in mavjud:
                await _run(f"ALTER TABLE {jadval} ADD COLUMN {nom} {tur}")
    await _episodes_kaliti()


async def _episodes_kaliti() -> None:
    """Eski bazalarda yagonalik (serial_id, qism_raqami) edi.

    Fasl qo'shilgach u yaramaydi: 2-faslning 1-qismi 1-faslnikini ustiga
    yozib yuborardi. SQLite da UNIQUE ni ALTER bilan o'zgartirib bo'lmaydi,
    shuning uchun jadval qayta quriladi (ma'lumot ko'chiriladi).
    """
    satr = await _one("SELECT sql FROM sqlite_master WHERE type='table' AND name='episodes'")
    if not satr or "fasl, qism_raqami" in (satr["sql"] or ""):
        return
    await _db.executescript(
        """
        PRAGMA foreign_keys = OFF;
        BEGIN;
        CREATE TABLE episodes_yangi (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            serial_id     INTEGER NOT NULL REFERENCES serials(id) ON DELETE CASCADE,
            qism_raqami   INTEGER NOT NULL,
            nom           TEXT,
            kanal_msg_id  INTEGER NOT NULL,
            davomiyligi   INTEGER,
            fasl          INTEGER DEFAULT 1,
            UNIQUE (serial_id, fasl, qism_raqami)
        );
        INSERT INTO episodes_yangi (id, serial_id, qism_raqami, nom, kanal_msg_id, davomiyligi, fasl)
            SELECT id, serial_id, qism_raqami, nom, kanal_msg_id, davomiyligi, COALESCE(fasl, 1)
            FROM episodes;
        DROP TABLE episodes;
        ALTER TABLE episodes_yangi RENAME TO episodes;
        CREATE INDEX IF NOT EXISTS idx_episodes_serial ON episodes(serial_id, qism_raqami);
        COMMIT;
        PRAGMA foreign_keys = ON;
        """
    )


async def close_db() -> None:
    if _db is not None:
        await _db.close()


async def _all(sql: str, args: tuple = ()) -> list[aiosqlite.Row]:
    async with _db.execute(sql, args) as cur:
        return await cur.fetchall()


async def _one(sql: str, args: tuple = ()) -> aiosqlite.Row | None:
    async with _db.execute(sql, args) as cur:
        return await cur.fetchone()


async def _run(sql: str, args: tuple = ()) -> int:
    cur = await _db.execute(sql, args)
    await _db.commit()
    return cur.lastrowid


# ---------------------------------------------------------------- users

async def save_user(user_id: int, username: str | None, ism: str | None) -> None:
    await _run(
        """
        INSERT INTO users (user_id, username, ism) VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            ism = excluded.ism,
            oxirgi_faollik = CURRENT_TIMESTAMP
        """,
        (user_id, username, ism),
    )


async def get_user(user_id: int):
    return await _one("SELECT * FROM users WHERE user_id = ?", (user_id,))


async def count_users() -> int:
    return (await _one("SELECT COUNT(*) AS n FROM users"))["n"]


async def count_active_today() -> int:
    row = await _one("SELECT COUNT(*) AS n FROM users WHERE date(oxirgi_faollik) = date('now')")
    return row["n"]


async def all_user_ids(faqat_faol: bool = True) -> list[int]:
    shart = "WHERE faol = 1" if faqat_faol else ""
    return [r["user_id"] for r in await _all(f"SELECT user_id FROM users {shart}")]


async def faol_belgila(user_id: int, faol: bool) -> None:
    """Bloklagan/qaytgan foydalanuvchini belgilaydi."""
    await _run("UPDATE users SET faol = ? WHERE user_id = ?", (1 if faol else 0, user_id))


async def count_faol() -> int:
    return (await _one("SELECT COUNT(*) AS n FROM users WHERE faol = 1"))["n"]


# -------------------------------------------------------------- serials

async def add_serial(nom, tavsif, poster_file_id, janr, yil) -> int:
    return await _run(
        "INSERT INTO serials (nom, tavsif, poster_file_id, janr, yil) VALUES (?, ?, ?, ?, ?)",
        (nom, tavsif, poster_file_id, janr, yil),
    )


# Foydalanuvchiga ko'rinadigan seriallar: eski yozuvlarda holat bo'sh bo'lishi mumkin
KORINADI = "(holat IS NULL OR holat = '' OR holat = 'tasdiqlangan')"


async def get_serial(serial_id: int):
    return await _one("SELECT * FROM serials WHERE id = ?", (serial_id,))


async def get_serial_by_name(nom: str):
    """Reply tugmalarda id yo'q — serial nomi bo'yicha topamiz."""
    return await _one(
        f"SELECT * FROM serials WHERE nom = ? AND {KORINADI} ORDER BY id LIMIT 1", (nom,)
    )


async def count_serials() -> int:
    return (await _one(f"SELECT COUNT(*) AS n FROM serials WHERE {KORINADI}"))["n"]


async def list_serials(offset: int, limit: int):
    return await _all(
        f"SELECT * FROM serials WHERE {KORINADI} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
        (limit, offset),
    )


async def search_serials(soz: str, limit: int = 20):
    naqsh = f"%{soz}%"
    return await _all(
        f"SELECT * FROM serials WHERE (nom LIKE ? OR janr LIKE ?) AND {KORINADI} ORDER BY nom LIMIT ?",
        (naqsh, naqsh, limit),
    )


async def update_serial(serial_id: int, maydon: str, qiymat) -> None:
    if maydon not in {"nom", "tavsif", "poster_file_id", "janr", "yil"}:
        raise ValueError("noma'lum maydon: " + maydon)
    await _run(f"UPDATE serials SET {maydon} = ? WHERE id = ?", (qiymat, serial_id))


async def delete_serial(serial_id: int) -> None:
    await _run("DELETE FROM serials WHERE id = ?", (serial_id,))


# ------------------------------------------------------------- episodes

async def add_episode(serial_id, qism_raqami, nom, kanal_msg_id, davomiyligi, fasl: int = 1) -> int:
    return await _run(
        """
        INSERT INTO episodes (serial_id, qism_raqami, nom, kanal_msg_id, davomiyligi, fasl)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(serial_id, fasl, qism_raqami) DO UPDATE SET
            nom = excluded.nom,
            kanal_msg_id = excluded.kanal_msg_id,
            davomiyligi = excluded.davomiyligi
        """,
        (serial_id, qism_raqami, nom, kanal_msg_id, davomiyligi, fasl),
    )


async def next_episode_number(serial_id: int, fasl: int = 1) -> int:
    row = await _one(
        "SELECT MAX(qism_raqami) AS m FROM episodes WHERE serial_id = ? AND COALESCE(fasl, 1) = ?",
        (serial_id, fasl),
    )
    return (row["m"] or 0) + 1


async def count_episodes(serial_id: int) -> int:
    row = await _one("SELECT COUNT(*) AS n FROM episodes WHERE serial_id = ?", (serial_id,))
    return row["n"]


async def list_episodes(serial_id: int, offset: int, limit: int):
    return await _all(
        "SELECT * FROM episodes WHERE serial_id = ? ORDER BY qism_raqami LIMIT ? OFFSET ?",
        (serial_id, limit, offset),
    )


async def get_episode(serial_id: int, qism_raqami: int, fasl: int | None = None):
    """fasl berilmasa — raqami mos keladigan birinchi qism (fasl bo'yicha)."""
    if fasl is None:
        return await _one(
            "SELECT * FROM episodes WHERE serial_id = ? AND qism_raqami = ? ORDER BY COALESCE(fasl, 1) LIMIT 1",
            (serial_id, qism_raqami),
        )
    return await _one(
        "SELECT * FROM episodes WHERE serial_id = ? AND qism_raqami = ? AND COALESCE(fasl, 1) = ?",
        (serial_id, qism_raqami, fasl),
    )


async def prev_next_episode(
    serial_id: int, qism_raqami: int, fasl: int | None = None
) -> tuple[int | None, int | None]:
    """Oldingi va keyingi qism raqamlari (fasl ichida); chekkada bo'lsa None."""
    shart = "" if fasl is None else " AND COALESCE(fasl, 1) = ?"
    argumentlar = (serial_id, qism_raqami) if fasl is None else (serial_id, qism_raqami, fasl)
    oldingi = await _one(
        f"SELECT MAX(qism_raqami) AS q FROM episodes WHERE serial_id = ? AND qism_raqami < ?{shart}",
        argumentlar,
    )
    keyingi = await _one(
        f"SELECT MIN(qism_raqami) AS q FROM episodes WHERE serial_id = ? AND qism_raqami > ?{shart}",
        argumentlar,
    )
    return oldingi["q"], keyingi["q"]


async def episode_page(
    serial_id: int, qism_raqami: int, per_page: int, fasl: int | None = None
) -> int:
    """Shu qism qismlar ro'yxatining qaysi sahifasida turganini qaytaradi."""
    shart = "" if fasl is None else " AND COALESCE(fasl, 1) = ?"
    argumentlar = (serial_id, qism_raqami) if fasl is None else (serial_id, qism_raqami, fasl)
    row = await _one(
        f"SELECT COUNT(*) AS n FROM episodes WHERE serial_id = ? AND qism_raqami < ?{shart}",
        argumentlar,
    )
    return row["n"] // per_page


async def delete_episode(episode_id: int) -> None:
    await _run("DELETE FROM episodes WHERE id = ?", (episode_id,))


# ------------------------------------------------------------- progress

async def save_progress(user_id: int, serial_id: int, qism: int) -> None:
    await _run(
        """
        INSERT INTO progress (user_id, serial_id, oxirgi_qism) VALUES (?, ?, ?)
        ON CONFLICT(user_id, serial_id) DO UPDATE SET
            oxirgi_qism = excluded.oxirgi_qism,
            yangilangan = CURRENT_TIMESTAMP
        """,
        (user_id, serial_id, qism),
    )


async def last_progress(user_id: int):
    """Eng oxirgi ko'rilgan serial — "Davom ettirish" tugmasi uchun."""
    return await _one(
        """
        SELECT p.serial_id, p.oxirgi_qism, s.nom
        FROM progress p JOIN serials s ON s.id = p.serial_id
        WHERE p.user_id = ?
        ORDER BY p.yangilangan DESC LIMIT 1
        """,
        (user_id,),
    )


async def top_serials(limit: int = 10):
    return await _all(
        """
        SELECT s.nom, COUNT(*) AS tomoshabin
        FROM progress p JOIN serials s ON s.id = p.serial_id
        GROUP BY p.serial_id ORDER BY tomoshabin DESC LIMIT ?
        """,
        (limit,),
    )


# -------------------------------------------------------------- murojat

async def add_murojat(user_id: int, matn: str) -> int:
    return await _run("INSERT INTO murojat (user_id, matn) VALUES (?, ?)", (user_id, matn))


async def get_murojat(murojat_id: int):
    return await _one("SELECT * FROM murojat WHERE id = ?", (murojat_id,))


async def answer_murojat(murojat_id: int, javob: str) -> None:
    await _run(
        "UPDATE murojat SET javob = ?, holat = 'javob_berilgan' WHERE id = ?",
        (javob, murojat_id),
    )


async def unanswered_murojat(limit: int = 20):
    return await _all(
        "SELECT * FROM murojat WHERE holat = 'yangi' ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )


# -------------------------------------------------- yuklash navbati

async def navbat_kesh(manba_url: str):
    """Shu URL avval muvaffaqiyatli yuklangan bo'lsa — o'sha yozuv (qayta yuklamaymiz)."""
    return await _one(
        "SELECT * FROM yuklash_navbat WHERE manba_url = ? AND holat = 'tayyor' ORDER BY id DESC LIMIT 1",
        (manba_url,),
    )


async def navbat_bormi(manba_url: str):
    """Shu URL navbatda yoki yuklanayotgan bo'lsa — o'sha yozuv."""
    return await _one(
        "SELECT * FROM yuklash_navbat WHERE manba_url = ? AND holat IN ('navbatda', 'yuklanmoqda') LIMIT 1",
        (manba_url,),
    )


async def navbat_qosh(manba_url: str, serial_id: int | None = None, qism_raqami: int | None = None) -> int:
    return await _run(
        "INSERT INTO yuklash_navbat (manba_url, serial_id, qism_raqami) VALUES (?, ?, ?)",
        (manba_url, serial_id, qism_raqami),
    )


async def navbat_keyingi():
    """Navbatdagi eng eski vazifa."""
    return await _one(
        "SELECT * FROM yuklash_navbat WHERE holat = 'navbatda' ORDER BY id LIMIT 1"
    )


async def navbat_holat(
    navbat_id: int,
    holat: str,
    kanal_msg_id: int | None = None,
    xato_matni: str | None = None,
) -> None:
    tugagan = "CURRENT_TIMESTAMP" if holat in {"tayyor", "xato"} else "tugagan_at"
    await _run(
        f"""
        UPDATE yuklash_navbat
        SET holat = ?, kanal_msg_id = COALESCE(?, kanal_msg_id),
            xato_matni = ?, tugagan_at = {tugagan}
        WHERE id = ?
        """,
        (holat, kanal_msg_id, xato_matni, navbat_id),
    )


async def navbat_sanoq() -> dict[str, int]:
    satrlar = await _all("SELECT holat, COUNT(*) AS n FROM yuklash_navbat GROUP BY holat")
    return {r["holat"]: r["n"] for r in satrlar}


async def navbat_royxat(holat: str, limit: int = 10):
    return await _all(
        "SELECT * FROM yuklash_navbat WHERE holat = ? ORDER BY id DESC LIMIT ?",
        (holat, limit),
    )


async def navbat_tiklash() -> None:
    """Bot qayta ishga tushganda yarim qolgan vazifalarni navbatga qaytaradi."""
    await _run("UPDATE yuklash_navbat SET holat = 'navbatda' WHERE holat = 'yuklanmoqda'")


# ---------------------------------------------------------- takliflar

async def taklif_qosh(nom: str, tavsif: str | None, manba_url: str | None, user_id: int) -> int:
    """Yangi taklif — serials jadvaliga holat='kutilmoqda' bilan yoziladi."""
    return await _run(
        """
        INSERT INTO serials (nom, tavsif, manba_url, qoshgan_user_id, holat)
        VALUES (?, ?, ?, ?, 'kutilmoqda')
        """,
        (nom, tavsif, manba_url, user_id),
    )


async def bugungi_takliflar(user_id: int) -> int:
    row = await _one(
        "SELECT COUNT(*) AS n FROM serials WHERE qoshgan_user_id = ? AND date(created_at) = date('now')",
        (user_id,),
    )
    return row["n"]


async def takliflar(limit: int = 20):
    return await _all(
        "SELECT * FROM serials WHERE holat = 'kutilmoqda' ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )


async def taklif_tasdiqla(serial_id: int) -> None:
    await _run("UPDATE serials SET holat = 'tasdiqlangan' WHERE id = ?", (serial_id,))


async def taklif_rad(serial_id: int) -> None:
    await _run("DELETE FROM serials WHERE id = ? AND holat = 'kutilmoqda'", (serial_id,))


# ------------------------------------------------- qidiruv sahifalash

async def search_count(soz: str) -> int:
    naqsh = f"%{soz}%"
    row = await _one(
        f"SELECT COUNT(*) AS n FROM serials WHERE (nom LIKE ? OR janr LIKE ?) AND {KORINADI}",
        (naqsh, naqsh),
    )
    return row["n"]


async def search_page(soz: str, offset: int, limit: int):
    naqsh = f"%{soz}%"
    return await _all(
        f"""
        SELECT * FROM serials WHERE (nom LIKE ? OR janr LIKE ?) AND {KORINADI}
        ORDER BY nom LIMIT ? OFFSET ?
        """,
        (naqsh, naqsh, limit, offset),
    )


# ------------------------------------------------------------- janrlar

async def janrlar() -> list[str]:
    satrlar = await _all(
        f"""
        SELECT DISTINCT janr FROM serials
        WHERE janr IS NOT NULL AND janr != '' AND {KORINADI}
        ORDER BY janr
        """
    )
    return [r["janr"] for r in satrlar]


async def janr_sanoq(janr: str) -> int:
    row = await _one(
        f"SELECT COUNT(*) AS n FROM serials WHERE janr = ? AND {KORINADI}", (janr,)
    )
    return row["n"]


async def janr_seriallari(janr: str, offset: int, limit: int):
    return await _all(
        f"""
        SELECT * FROM serials WHERE janr = ? AND {KORINADI}
        ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?
        """,
        (janr, limit, offset),
    )


# ------------------------------------------- tomoshabinlar / ro'yxatim

async def serial_tomoshabinlari(serial_id: int) -> list[int]:
    """Shu serialni ko'rgan (progress yozuvi bor) faol foydalanuvchilar."""
    satrlar = await _all(
        """
        SELECT p.user_id FROM progress p
        JOIN users u ON u.user_id = p.user_id
        WHERE p.serial_id = ? AND u.faol = 1
        """,
        (serial_id,),
    )
    return [r["user_id"] for r in satrlar]


async def progress_royxati(user_id: int, limit: int = 20):
    """Foydalanuvchi ko'rayotgan barcha seriallar (oxirgi ko'rilgani birinchi)."""
    return await _all(
        f"""
        SELECT p.serial_id, p.oxirgi_qism, p.yangilangan, s.nom
        FROM progress p JOIN serials s ON s.id = p.serial_id
        WHERE p.user_id = ? AND {KORINADI.replace("holat", "s.holat")}
        ORDER BY p.yangilangan DESC LIMIT ?
        """,
        (user_id, limit),
    )


async def zaxira_ol(nishon_yoli: str) -> None:
    """Ishlayotgan bazadan izchil nusxa (SQLite backup API)."""
    async with aiosqlite.connect(nishon_yoli) as nishon:
        await _db.backup(nishon)


# ------------------------------------------------------------ kuzatuv

async def kuzatuv_bormi(user_id: int, serial_id: int) -> bool:
    satr = await _one(
        "SELECT 1 AS b FROM kuzatuv WHERE user_id = ? AND serial_id = ?", (user_id, serial_id)
    )
    return satr is not None


async def kuzatuv_almashtir(user_id: int, serial_id: int) -> bool:
    """Kuzatishni yoqadi/o'chiradi, yangi holatni qaytaradi."""
    if await kuzatuv_bormi(user_id, serial_id):
        await _run("DELETE FROM kuzatuv WHERE user_id = ? AND serial_id = ?", (user_id, serial_id))
        return False
    await _run("INSERT INTO kuzatuv (user_id, serial_id) VALUES (?, ?)", (user_id, serial_id))
    return True


async def kuzatuvchilar(serial_id: int) -> list[int]:
    satrlar = await _all(
        """
        SELECT k.user_id FROM kuzatuv k JOIN users u ON u.user_id = k.user_id
        WHERE k.serial_id = ? AND u.faol = 1
        """,
        (serial_id,),
    )
    return [r["user_id"] for r in satrlar]


async def kuzatganlarim(user_id: int, limit: int = 20):
    return await _all(
        f"""
        SELECT s.* FROM kuzatuv k JOIN serials s ON s.id = k.serial_id
        WHERE k.user_id = ? AND {KORINADI.replace("holat", "s.holat")}
        ORDER BY k.created_at DESC LIMIT ?
        """,
        (user_id, limit),
    )


# ------------------------------------------------------------- baholar

async def baho_qoy(user_id: int, serial_id: int, baho: int) -> None:
    await _run(
        """
        INSERT INTO baholar (user_id, serial_id, baho) VALUES (?, ?, ?)
        ON CONFLICT(user_id, serial_id) DO UPDATE SET baho = excluded.baho
        """,
        (user_id, serial_id, baho),
    )


async def baho_sanoq(serial_id: int) -> tuple[int, int]:
    satr = await _one(
        """
        SELECT SUM(CASE WHEN baho > 0 THEN 1 ELSE 0 END) AS yoqdi,
               SUM(CASE WHEN baho < 0 THEN 1 ELSE 0 END) AS yoqmadi
        FROM baholar WHERE serial_id = ?
        """,
        (serial_id,),
    )
    return satr["yoqdi"] or 0, satr["yoqmadi"] or 0


async def eng_yaxshilar(limit: int = 10):
    return await _all(
        f"""
        SELECT s.*, SUM(b.baho) AS ball FROM baholar b JOIN serials s ON s.id = b.serial_id
        WHERE {KORINADI.replace("holat", "s.holat")}
        GROUP BY b.serial_id HAVING ball > 0 ORDER BY ball DESC LIMIT ?
        """,
        (limit,),
    )


# ----------------------------------------------------- qidiruv jurnali

async def qidiruv_yoz(soz: str, user_id: int, topildi: bool) -> None:
    await _run(
        "INSERT INTO qidiruvlar (soz, user_id, topildi) VALUES (?, ?, ?)",
        (soz.lower(), user_id, 1 if topildi else 0),
    )


async def topilmaganlar(limit: int = 20):
    return await _all(
        """
        SELECT soz, COUNT(*) AS soni, MAX(created_at) AS oxirgi
        FROM qidiruvlar WHERE topildi = 0
        GROUP BY soz ORDER BY soni DESC, oxirgi DESC LIMIT ?
        """,
        (limit,),
    )


async def mashhur_qidiruvlar(limit: int = 10):
    return await _all(
        "SELECT soz, COUNT(*) AS soni FROM qidiruvlar GROUP BY soz ORDER BY soni DESC LIMIT ?",
        (limit,),
    )


# ------------------------------------------------------------ manbalar

async def manba_yoz(manba: str, user_id: int) -> None:
    await _run("INSERT INTO manbalar (manba, user_id) VALUES (?, ?)", (manba, user_id))


async def manba_statistika(limit: int = 15):
    return await _all(
        """
        SELECT manba, COUNT(*) AS soni, COUNT(DISTINCT user_id) AS odamlar
        FROM manbalar GROUP BY manba ORDER BY soni DESC LIMIT ?
        """,
        (limit,),
    )


# ------------------------------------------------------------- rejalar

async def reja_qosh(chat_id: int, message_id: int, vaqt: str) -> int:
    return await _run(
        "INSERT INTO rejalar (chat_id, message_id, vaqt) VALUES (?, ?, ?)",
        (chat_id, message_id, vaqt),
    )


async def reja_yetganlar():
    return await _all(
        "SELECT * FROM rejalar WHERE holat = 'kutilmoqda' AND vaqt <= datetime('now') ORDER BY vaqt"
    )


async def rejalar(holat: str = "kutilmoqda", limit: int = 10):
    return await _all("SELECT * FROM rejalar WHERE holat = ? ORDER BY vaqt LIMIT ?", (holat, limit))


async def reja_holat(reja_id: int, holat: str, natija: str | None = None) -> None:
    await _run("UPDATE rejalar SET holat = ?, natija = ? WHERE id = ?", (holat, natija, reja_id))


# ---------------------------------------------------------------- fasl

async def fasllar(serial_id: int) -> list[int]:
    satrlar = await _all(
        "SELECT DISTINCT COALESCE(fasl, 1) AS fasl FROM episodes WHERE serial_id = ? ORDER BY fasl",
        (serial_id,),
    )
    return [r["fasl"] for r in satrlar]


async def fasl_episodes(serial_id: int, fasl: int, offset: int, limit: int):
    return await _all(
        """
        SELECT * FROM episodes WHERE serial_id = ? AND COALESCE(fasl, 1) = ?
        ORDER BY qism_raqami LIMIT ? OFFSET ?
        """,
        (serial_id, fasl, limit, offset),
    )


async def fasl_sanoq(serial_id: int, fasl: int) -> int:
    satr = await _one(
        "SELECT COUNT(*) AS n FROM episodes WHERE serial_id = ? AND COALESCE(fasl, 1) = ?",
        (serial_id, fasl),
    )
    return satr["n"]


async def episode_fasl(serial_id: int, qism_raqami: int, fasl: int) -> None:
    await _run(
        "UPDATE episodes SET fasl = ? WHERE serial_id = ? AND qism_raqami = ?",
        (fasl, serial_id, qism_raqami),
    )


async def episode_yangila(
    serial_id: int, qism_raqami: int, kanal_msg_id: int, davomiyligi, fasl: int | None = None
) -> None:
    """Qism videosini almashtirish."""
    shart = "" if fasl is None else " AND COALESCE(fasl, 1) = ?"
    argumentlar = (kanal_msg_id, davomiyligi, serial_id, qism_raqami)
    if fasl is not None:
        argumentlar += (fasl,)
    await _run(
        f"UPDATE episodes SET kanal_msg_id = ?, davomiyligi = ? "
        f"WHERE serial_id = ? AND qism_raqami = ?{shart}",
        argumentlar,
    )


# ------------------------------------------------------ kashfiyot / CSV

async def tasodifiy_serial():
    return await _one(f"SELECT * FROM serials WHERE {KORINADI} ORDER BY RANDOM() LIMIT 1")


async def yangi_seriallar(kun: int = 7, limit: int = 10):
    return await _all(
        f"""
        SELECT * FROM serials WHERE {KORINADI} AND created_at >= datetime('now', ?)
        ORDER BY created_at DESC LIMIT ?
        """,
        (f"-{kun} days", limit),
    )


async def barcha_seriallar():
    return await _all("SELECT * FROM serials ORDER BY id")


async def barcha_episodes():
    return await _all("SELECT * FROM episodes ORDER BY serial_id, qism_raqami")


async def serial_nomlari() -> list[tuple[int, str]]:
    """Chidamli qidiruv uchun: (id, nom) ro'yxati."""
    satrlar = await _all(f"SELECT id, nom FROM serials WHERE {KORINADI}")
    return [(r["id"], r["nom"]) for r in satrlar]


# ------------------------------------------------------------------ til

async def til_belgila(user_id: int, til: str) -> None:
    await _run("UPDATE users SET til = ? WHERE user_id = ?", (til, user_id))


async def til_ol(user_id: int) -> str:
    satr = await _one("SELECT til FROM users WHERE user_id = ?", (user_id,))
    return (satr["til"] if satr else None) or "uz"


async def progress_bitta(user_id: int, serial_id: int):
    return await _one(
        "SELECT * FROM progress WHERE user_id = ? AND serial_id = ?", (user_id, serial_id)
    )


# ------------------------------------------------------ FSM (storage.py)

async def fsm_oqi(kalit: str):
    return await _one("SELECT * FROM fsm WHERE kalit = ?", (kalit,))


async def fsm_yoz(kalit: str, holat: str | None = ..., malumot: str | None = ...) -> None:
    """Faqat berilgan maydonni yangilaydi (... = tegilmaydi)."""
    mavjud = await fsm_oqi(kalit)
    yangi_holat = mavjud["holat"] if (holat is ... and mavjud) else (None if holat is ... else holat)
    yangi_malumot = (
        mavjud["malumot"] if (malumot is ... and mavjud) else (None if malumot is ... else malumot)
    )
    await _run(
        """
        INSERT INTO fsm (kalit, holat, malumot) VALUES (?, ?, ?)
        ON CONFLICT(kalit) DO UPDATE SET holat = excluded.holat, malumot = excluded.malumot
        """,
        (kalit, yangi_holat, yangi_malumot),
    )


# ------------------------------------------------------------------ turi

async def turi_belgila(serial_id: int, turi: str) -> None:
    await _run("UPDATE serials SET turi = ? WHERE id = ?", (turi, serial_id))


async def turi_sanoq(turi: str) -> int:
    satr = await _one(
        f"SELECT COUNT(*) AS n FROM serials WHERE COALESCE(turi, 'serial') = ? AND {KORINADI}",
        (turi,),
    )
    return satr["n"]


async def turi_royxati(turi: str, offset: int, limit: int):
    return await _all(
        f"""
        SELECT * FROM serials WHERE COALESCE(turi, 'serial') = ? AND {KORINADI}
        ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?
        """,
        (turi, limit, offset),
    )
