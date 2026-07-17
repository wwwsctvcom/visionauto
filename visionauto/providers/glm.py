"""GLM (Zhipu BigModel) provider. OpenAI-compatible endpoint."""
from __future__ import annotations

from .base import OpenAICompatibleProvider


class GLMProvider(OpenAICompatibleProvider):
    DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
    DEFAULT_MODEL = "GLM-5V-Turbo"

    def supports_temperature(self) -> bool:
        # GLM-Z1 / thinking / reasoner series do not accept temperature.
        name = (self._model or "").lower()
        return not any(p in name for p in ("z1", "thinking", "reasoner"))
