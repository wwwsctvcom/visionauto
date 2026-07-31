"""Kimi (Moonshot) provider. OpenAI-compatible endpoint.

Temperature quirks (per Moonshot docs):
- kimi-k2.5 / kimi-k2.6: temperature is server-managed -> do not send it.
- kimi-k2.7 series: requires temperature=1.0.
- kimi-k3: default temperature=0 for reproducibility (adjust if the API rejects it).
"""
from __future__ import annotations

from .base import OpenAICompatibleProvider

KIMI_K3 = "kimi-k3"
KIMI_K2_7 = "kimi-k2.7"
KIMI_K2_7_CODE = "kimi-k2.7-code"
KIMI_K2_6 = "kimi-k2.6"
KIMI_K2_5 = "kimi-k2.5"


class KimiProvider(OpenAICompatibleProvider):
    DEFAULT_BASE_URL = "https://api.moonshot.ai/v1"
    DEFAULT_MODEL = KIMI_K3
    # Server-managed temperature: omit the param entirely.
    NO_TEMPERATURE_MODELS = ("kimi-k2.5", "kimi-k2.6")
    # Force temperature=1.0 for models that require it.
    MODEL_PARAM_OVERRIDES = (
        ("kimi-k2.7", {"temperature": 1.0}),
    )
