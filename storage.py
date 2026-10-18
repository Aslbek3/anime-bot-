"""FSM holatini SQLite da saqlash (FEATURE_SQLITE_FSM).

MemoryStorage da bot qayta ishga tushsa navigatsiya konteksti yo'qoladi.
aiogram 3 da tayyor SQLite storage yo'q (faqat Memory va Redis), shuning
uchun shu yerda BaseStorage ning ixcham amalga oshirilishi — ma'lumot
botning o'z bazasidagi `fsm` jadvaliga yoziladi.
"""
import json

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StorageKey

import db


class SQLiteStorage(BaseStorage):
    @staticmethod
    def _kalit(key: StorageKey) -> str:
        return f"{key.bot_id}:{key.chat_id}:{key.user_id}"

    async def set_state(self, key: StorageKey, state: State | str | None = None) -> None:
        nom = state.state if isinstance(state, State) else state
        await db.fsm_yoz(self._kalit(key), holat=nom)

    async def get_state(self, key: StorageKey) -> str | None:
        satr = await db.fsm_oqi(self._kalit(key))
        return satr["holat"] if satr else None

    async def set_data(self, key: StorageKey, data: dict) -> None:
        await db.fsm_yoz(self._kalit(key), malumot=json.dumps(data, ensure_ascii=False))

    async def get_data(self, key: StorageKey) -> dict:
        satr = await db.fsm_oqi(self._kalit(key))
        if not satr or not satr["malumot"]:
            return {}
        try:
            return json.loads(satr["malumot"])
        except json.JSONDecodeError:
            return {}

    async def close(self) -> None:
        pass
