"""Provider transport layer: how to talk to a VLM (auth + HTTP), nothing about prompts."""
from __future__ import annotations

import base64
from typing import Protocol, runtime_checkable

from .config import ProviderConfig


def encode_data_url(image: bytes, mime: str = "image/png") -> str:
    return f"data:{mime};base64,{base64.b64encode(image).decode()}"


@runtime_checkable
class VisionProvider(Protocol):
    """Send images + a prompt to a VLM, return the raw text response."""

    def chat(
        self,
        images: list[bytes],
        prompt: str,
        *,
        json_mode: bool = True,
    ) -> str: ...


class OpenAICompatibleProvider:
    """Base for providers speaking the OpenAI Chat Completions API.

    Subclasses set DEFAULT_BASE_URL / DEFAULT_MODEL so users only need an api_key,
    and may declare per-model parameter quirks via NO_TEMPERATURE_MODELS /
    MODEL_PARAM_OVERRIDES.
    """

    DEFAULT_BASE_URL: str = ""
    DEFAULT_MODEL: str = ""
    # Normalization scale the model emits for bbox coords (GLM-V/Qwen-VL: 0-999/0-1000).
    # Locators use this to convert returned coords to canonical [0,1] space.
    COORD_NORM_SCALE: float = 1000.0
    # Model-name prefixes whose temperature is server-managed; do NOT send it.
    NO_TEMPERATURE_MODELS: tuple[str, ...] = ()
    # (prefix, params) — force request params for models whose name starts with prefix,
    # e.g. (("kimi-k2.7", {"temperature": 1.0}),). Overrides win over the default.
    MODEL_PARAM_OVERRIDES: tuple[tuple[str, dict], ...] = ()

    def __init__(self, cfg: ProviderConfig):
        try:
            from openai import OpenAI
        except ImportError as e:  # pragma: no cover - import guard
            raise ImportError(
                "the 'openai' package is required: pip install openai"
            ) from e
        self.cfg = cfg
        self._client = OpenAI(
            api_key=cfg.api_key or "",
            base_url=cfg.base_url or self.DEFAULT_BASE_URL,
            default_headers=cfg.extra_headers or None,
        )
        self._model = cfg.model or self.DEFAULT_MODEL
        if not self._model:
            raise ValueError(
                "no model configured: set model in the ProviderConfig "
                "(required for the generic 'openai' provider)."
            )
        self._temperature = cfg.temperature
        self.norm_scale = self.COORD_NORM_SCALE

    def supports_temperature(self) -> bool:
        """Whether the current model accepts a ``temperature`` argument.

        Default True; providers override for reasoning/thinking models that
        reject temperature, and NO_TEMPERATURE_MODELS is always honored.
        """
        name = (self._model or "").lower()
        return not any(name.startswith(p.lower()) for p in self.NO_TEMPERATURE_MODELS)

    def _request_params(self) -> dict:
        """Build per-request params: default temperature (if supported) plus any
        MODEL_PARAM_OVERRIDES that match the current model (overrides win)."""
        params: dict = {}
        if self.supports_temperature() and self._temperature is not None:
            params["temperature"] = self._temperature
        name = (self._model or "").lower()
        for prefix, override in self.MODEL_PARAM_OVERRIDES:
            if name.startswith(prefix.lower()):
                params.update(override)
        return params

    def chat(self, images, prompt, *, json_mode=True) -> str:
        content: list[dict] = [{"type": "text", "text": prompt}]
        for img in images:
            content.append(
                {"type": "image_url", "image_url": {"url": encode_data_url(img)}}
            )
        messages = [{"role": "user", "content": content}]

        kwargs: dict = {"model": self._model, "messages": messages}
        kwargs.update(self._request_params())

        try:
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            resp = self._client.chat.completions.create(**kwargs)
        except Exception:
            # Some OpenAI-compatible endpoints reject response_format; retry without it.
            kwargs.pop("response_format", None)
            resp = self._client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""
