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
    UNIQUE (serial_id, qism_raqami)
);

CREATE TABLE IF NOT EXISTS users (
    user_id        INTEGER PRIMARY KEY,
    username       TEXT,
    ism            TEXT,
    til            TEXT DEFAULT 'uz',
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
    oxirgi_faollik TEXT DEFAULT CURRENT_TIMESTAMP
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

CREATE INDEX IF NOT EXISTS idx_episodes_serial ON episodes(serial_id, qism_raqami);
CREATE INDEX IF NOT EXISTS idx_progress_user ON progress(user_id, yangilangan);
"""

_db: aiosqlite.Connection | None = None


async def init_db() -> None:
    global _db
    _db = await aiosqlite.connect(DB_PATH)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA foreign_keys = ON")
    await _db.executescript(SCHEMA)
    await _db.commit()


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


async def count_users() -> int:
    return (await _one("SELECT COUNT(*) AS n FROM users"))["n"]


async def count_active_today() -> int:
    row = await _one("SELECT COUNT(*) AS n FROM users WHERE date(oxirgi_faollik) = date('now')")
    return row["n"]


async def all_user_ids() -> list[int]:
    return [r["user_id"] for r in await _all("SELECT user_id FROM users")]


# -------------------------------------------------------------- serials

async def add_serial(nom, tavsif, poster_file_id, janr, yil) -> int:
    return await _run(
        "INSERT INTO serials (nom, tavsif, poster_file_id, janr, yil) VALUES (?, ?, ?, ?, ?)",
        (nom, tavsif, poster_file_id, janr, yil),
    )


async def get_serial(serial_id: int):
    return await _one("SELECT * FROM serials WHERE id = ?", (serial_id,))


async def get_serial_by_name(nom: str):
    """Reply tugmalarda id yo'q — serial nomi bo'yicha topamiz."""
    return await _one("SELECT * FROM serials WHERE nom = ? ORDER BY id LIMIT 1", (nom,))


async def count_serials() -> int:
    return (await _one("SELECT COUNT(*) AS n FROM serials"))["n"]


async def list_serials(offset: int, limit: int):
    return await _all(
        "SELECT * FROM serials ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
        (limit, offset),
    )


async def search_serials(soz: str, limit: int = 20):
    naqsh = f"%{soz}%"
    return await _all(
        "SELECT * FROM serials WHERE nom LIKE ? OR janr LIKE ? ORDER BY nom LIMIT ?",
        (naqsh, naqsh, limit),
    )


async def update_serial(serial_id: int, maydon: str, qiymat) -> None:
    if maydon not in {"nom", "tavsif", "poster_file_id", "janr", "yil"}:
        raise ValueError("noma'lum maydon: " + maydon)
    await _run(f"UPDATE serials SET {maydon} = ? WHERE id = ?", (qiymat, serial_id))


async def delete_serial(serial_id: int) -> None:
    await _run("DELETE FROM serials WHERE id = ?", (serial_id,))


# ------------------------------------------------------------- episodes

async def add_episode(serial_id, qism_raqami, nom, kanal_msg_id, davomiyligi) -> int:
    return await _run(
        """
        INSERT INTO episodes (serial_id, qism_raqami, nom, kanal_msg_id, davomiyligi)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(serial_id, qism_raqami) DO UPDATE SET
            nom = excluded.nom,
            kanal_msg_id = excluded.kanal_msg_id,
            davomiyligi = excluded.davomiyligi
        """,
        (serial_id, qism_raqami, nom, kanal_msg_id, davomiyligi),
    )


async def next_episode_number(serial_id: int) -> int:
    row = await _one("SELECT MAX(qism_raqami) AS m FROM episodes WHERE serial_id = ?", (serial_id,))
    return (row["m"] or 0) + 1


async def count_episodes(serial_id: int) -> int:
    row = await _one("SELECT COUNT(*) AS n FROM episodes WHERE serial_id = ?", (serial_id,))
    return row["n"]


async def list_episodes(serial_id: int, offset: int, limit: int):
    return await _all(
        "SELECT * FROM episodes WHERE serial_id = ? ORDER BY qism_raqami LIMIT ? OFFSET ?",
        (serial_id, limit, offset),
    )


async def get_episode(serial_id: int, qism_raqami: int):
    return await _one(
        "SELECT * FROM episodes WHERE serial_id = ? AND qism_raqami = ?",
        (serial_id, qism_raqami),
    )


async def prev_next_episode(serial_id: int, qism_raqami: int) -> tuple[int | None, int | None]:
    """Oldingi va keyingi qism raqamlari; chekkada bo'lsa None."""
    oldingi = await _one(
        "SELECT MAX(qism_raqami) AS q FROM episodes WHERE serial_id = ? AND qism_raqami < ?",
        (serial_id, qism_raqami),
    )
    keyingi = await _one(
        "SELECT MIN(qism_raqami) AS q FROM episodes WHERE serial_id = ? AND qism_raqami > ?",
        (serial_id, qism_raqami),
    )
    return oldingi["q"], keyingi["q"]


async def episode_page(serial_id: int, qism_raqami: int, per_page: int) -> int:
    """Shu qism qismlar ro'yxatining qaysi sahifasida turganini qaytaradi."""
    row = await _one(
        "SELECT COUNT(*) AS n FROM episodes WHERE serial_id = ? AND qism_raqami < ?",
        (serial_id, qism_raqami),
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
