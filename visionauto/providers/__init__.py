"""Provider layer.

The framework talks to any OpenAI-compatible endpoint through ONE transport
(``OpenAICompatibleProvider``). Named presets (``PROVIDER_PRESETS``) are just a
convenience so users don't have to remember base_urls and a default vision
model — you can always pass base_url/api_key/model directly to VisionDevice.

Helpers kept for backward compatibility / tests:
    get_provider("qwen", ProviderConfig(api_key=...))
    get_provider_from_env()
"""
from __future__ import annotations

import os

from ..exceptions import ProviderConfigError
from .base import OpenAICompatibleProvider, VisionProvider
from .config import ProviderConfig
from .presets import PROVIDER_PRESETS


def register_provider(name: str, base_url: str | None, model: str | None = None) -> None:
    """Register/override a named preset (base_url + optional default model)."""
    PROVIDER_PRESETS[name.lower()] = {"base_url": base_url, "model": model}


def get_provider(name: str, cfg: ProviderConfig | None = None) -> VisionProvider:
    """Build a provider from a preset name; explicit cfg fields override the preset."""
    preset = PROVIDER_PRESETS.get(name.lower())
    if preset is None:
        raise ProviderConfigError(
            f"unknown provider {name!r}; known: {sorted(PROVIDER_PRESETS)}. "
            f"Or pass base_url/api_key/model directly to VisionDevice instead of "
            f"using a preset name."
        )
    cfg = cfg or ProviderConfig()
    merged = ProviderConfig(
        api_key=cfg.api_key,
        base_url=cfg.base_url or preset.get("base_url"),
        model=cfg.model or preset.get("model"),
        extra_headers=cfg.extra_headers,
        temperature=cfg.temperature,
        timeout=cfg.timeout,
    )
    return OpenAICompatibleProvider(merged)


def get_provider_from_env(prefix: str = "VISIONAUTO") -> VisionProvider:
    """Build a provider purely from env vars ({PREFIX}_PROVIDER/API_KEY/MODEL/BASE_URL)."""
    name = os.environ.get(f"{prefix}_PROVIDER", "glm")
    return get_provider(name, ProviderConfig.from_env(prefix))


__all__ = [
    "VisionProvider",
    "ProviderConfig",
    "OpenAICompatibleProvider",
    "PROVIDER_PRESETS",
    "register_provider",
    "get_provider",
    "get_provider_from_env",
]
