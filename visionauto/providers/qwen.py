"""Qwen (Alibaba DashScope) provider. OpenAI-compatible endpoint."""
from __future__ import annotations

from .base import OpenAICompatibleProvider


class QwenProvider(OpenAICompatibleProvider):
    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DEFAULT_MODEL = "qwen3.7-max-2026-06-08"

    def supports_temperature(self) -> bool:
        # Qwen thinking / reasoning models (qwq, *-thinking, *-reasoner, R1
        # distills) do not accept temperature/top_p. qwen3.x-max/plus do.
        name = (self._model or "").lower()
        return not any(
            p in name for p in ("qwq", "thinking", "reasoner", "deepseek-r1")
        )
