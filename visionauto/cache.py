"""A tiny TTL cache for screenshot resolutions."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class _Entry:
    value: Any
    expires: float


class TTLCache:
    def __init__(self, ttl: float):
        self._ttl = ttl
        self._store: dict[Any, _Entry] = {}

    def get(self, key) -> Any:
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() > entry.expires:
            self._store.pop(key, None)
            return None
        return entry.value

    def set(self, key, value) -> None:
        self._store[key] = _Entry(value, time.monotonic() + self._ttl)

    def clear(self) -> None:
        self._store.clear()
