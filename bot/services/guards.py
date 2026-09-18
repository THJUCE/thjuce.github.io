from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager


class BusyOperationError(Exception):
    pass


class OperationGuard:
    def __init__(self, cooldown_seconds: int = 4) -> None:
        self.cooldown_seconds = cooldown_seconds
        self._busy: set[str] = set()
        self._cooldowns: dict[str, float] = {}
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def lock(self, key: str):
        async with self._lock:
            now = time.monotonic()
            cooldown_until = self._cooldowns.get(key)
            if key in self._busy or (cooldown_until and cooldown_until > now):
                raise BusyOperationError
            self._busy.add(key)
        try:
            yield
        finally:
            async with self._lock:
                self._busy.discard(key)
                self._cooldowns[key] = time.monotonic() + self.cooldown_seconds
