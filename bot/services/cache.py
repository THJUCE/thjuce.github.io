from __future__ import annotations

import asyncio
import time
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: int = 60) -> None:
        self.ttl_seconds = ttl_seconds
        self._storage: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            item = self._storage.get(key)
            if not item:
                return None
            expires_at, value = item
            if expires_at < time.monotonic():
                self._storage.pop(key, None)
                return None
            return value

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        async with self._lock:
            ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
            self._storage[key] = (time.monotonic() + ttl, value)

    async def invalidate(self, prefix: str) -> None:
        async with self._lock:
            for key in list(self._storage):
                if key.startswith(prefix):
                    self._storage.pop(key, None)
