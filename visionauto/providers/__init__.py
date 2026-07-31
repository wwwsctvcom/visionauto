"""Provider registry. Add new VLM backends here and in _REGISTRY."""
from __future__ import annotations

import os

from .base import VisionProvider
from .config import ProviderConfig
from .glm import GLMProvider
from .kimi import KimiProvider
from .mimo import MiMoProvider
from .openai import OpenAIProvider
from .qwen import QwenProvider

_REGISTRY: dict[str, type[VisionProvider]] = {
    "glm": GLMProvider,
    "qwen": QwenProvider,
    "kimi": KimiProvider,
    "mimo": MiMoProvider,
    "openai": OpenAIProvider,
}


def register_provider(name: str, cls: type[VisionProvider]) -> None:
    _REGISTRY[name] = cls


def get_provider(name: str, cfg: ProviderConfig) -> VisionProvider:
    if name not in _REGISTRY:
        raise ValueError(
            f"unknown provider {name!r}; registered: {list(_REGISTRY)}"
        )
    return _REGISTRY[name](cfg)


def get_provider_from_env(prefix: str = "VISIONAUTO") -> VisionProvider:
    """Convenience: build a provider from env vars.

    ``{PREFIX}_PROVIDER`` picks the provider name; the rest of the
    ProviderConfig comes from ProviderConfig.from_env().
    """
    name = os.environ.get(f"{prefix}_PROVIDER", "glm")
    return get_provider(name, ProviderConfig.from_env(prefix))


__all__ = [
    "VisionProvider",
    "ProviderConfig",
    "GLMProvider",
    "QwenProvider",
    "KimiProvider",
    "MiMoProvider",
    "OpenAIProvider",
    "register_provider",
    "get_provider",
    "get_provider_from_env",
]
