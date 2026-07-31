"""MiMo (Xiaomi) provider. OpenAI-compatible endpoint."""
from __future__ import annotations

from .base import OpenAICompatibleProvider

MIMO_V2_OMNI = "mimo-v2-omni"
MIMO_V2_5_PRO = "mimo-v2.5-pro"
MIMO_V2_5 = "mimo-v2.5"


class MiMoProvider(OpenAICompatibleProvider):
    DEFAULT_BASE_URL = "https://api.xiaomimimo.com/v1"
    DEFAULT_MODEL = MIMO_V2_OMNI
