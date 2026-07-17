"""Generic OpenAI-compatible provider.

No baked-in base_url/model defaults — supply them via Config so this works with
any OpenAI-compatible endpoint and any model (OpenAI, third-party gateways,
self-hosted, etc.).
"""
from __future__ import annotations

from .base import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    DEFAULT_BASE_URL = ""   # empty -> the openai SDK uses its own default
    DEFAULT_MODEL = ""

    def supports_temperature(self) -> bool:
        # OpenAI o-series reasoning models (o1/o3/o4*) do not accept temperature.
        name = (self._model or "").lower()
        return not name.startswith(("o1", "o3", "o4"))
