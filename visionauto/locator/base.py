"""Locator protocol."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..located import Located
from ..providers.base import VisionProvider


@runtime_checkable
class Locator(Protocol):
    def resolve(
        self,
        screenshot: bytes,
        width: int,
        height: int,
        provider: VisionProvider,
    ) -> list[Located]: ...
