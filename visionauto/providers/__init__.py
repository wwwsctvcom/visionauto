"""Provider registry. Add new VLM backends here and in _REGISTRY."""
from __future__ import annotations

from ..config import Config
from .base import VisionProvider
from .glm import GLMProvider
from .openai import OpenAIProvider
from .qwen import QwenProvider

_REGISTRY: dict[str, type[VisionProvider]] = {
    "glm": GLMProvider,
    "qwen": QwenProvider,
    "openai": OpenAIProvider,
}


def register_provider(name: str, cls: type[VisionProvider]) -> None:
    _REGISTRY[name] = cls


def get_provider(cfg: Config) -> VisionProvider:
    name = cfg.provider
    if name not in _REGISTRY:
        raise ValueError(
            f"unknown provider {name!r}; registered: {list(_REGISTRY)}"
        )
    return _REGISTRY[name](cfg)


__all__ = ["VisionProvider", "GLMProvider", "QwenProvider", "register_provider", "get_provider"]
