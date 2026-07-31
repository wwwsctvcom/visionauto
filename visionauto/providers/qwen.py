"""Qwen (Alibaba DashScope) provider. OpenAI-compatible endpoint."""
from __future__ import annotations

from .base import OpenAICompatibleProvider

QWEN3_7_MAX = "qwen3.7-max-2026-06-08"
QWEN3_7_PLUS = "qwen3.7-plus"
QWEN3_7_FLASH = "qwen3.7-flash"
QWEN3_6_PLUS = "qwen3.6-plus"
QWEN3_5_PLUS = "qwen3.5-plus"
QWEN_VL_MAX = "qwen-vl-max"
QWEN3_VL_PLUS = "qwen3-vl-plus"
QWEN3_VL_FLASH = "qwen3-vl-flash"


class QwenProvider(OpenAICompatibleProvider):
    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DEFAULT_MODEL = QWEN3_7_MAX

    def supports_temperature(self) -> bool:
        # Qwen thinking / reasoning models (qwq, *-thinking, *-reasoner, R1
        # distills) do not accept temperature/top_p. qwen3.x-max/plus do.
        name = (self._model or "").lower()
        return not any(
            p in name for p in ("qwq", "thinking", "reasoner", "deepseek-r1")
        )
