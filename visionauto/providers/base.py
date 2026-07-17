"""Provider transport layer: how to talk to a VLM (auth + HTTP), nothing about prompts."""
from __future__ import annotations

import base64
from typing import Protocol, runtime_checkable

from ..config import Config


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

    Subclasses set DEFAULT_BASE_URL / DEFAULT_MODEL so users only need an api_key.
    """

    DEFAULT_BASE_URL: str = ""
    DEFAULT_MODEL: str = ""
    # Normalization scale the model emits for bbox coords (GLM-V/Qwen-VL: 0-999/0-1000).
    # Locators use this to convert returned coords to canonical [0,1] space.
    COORD_NORM_SCALE: float = 1000.0

    def __init__(self, cfg: Config):
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
        )
        self._model = cfg.model or self.DEFAULT_MODEL
        if not self._model:
            raise ValueError(
                "no model configured: set VISIONAUTO_MODEL (or pass model=...) "
                "for the generic 'openai' provider."
            )
        self._temperature = cfg.temperature
        self.norm_scale = self.COORD_NORM_SCALE

    def supports_temperature(self) -> bool:
        """Whether the current model accepts a ``temperature`` argument.

        Default True; providers override to return False for reasoning/thinking
        models that reject temperature.
        """
        return True

    def chat(self, images, prompt, *, json_mode=True) -> str:
        content: list[dict] = [{"type": "text", "text": prompt}]
        for img in images:
            content.append(
                {"type": "image_url", "image_url": {"url": encode_data_url(img)}}
            )
        messages = [{"role": "user", "content": content}]

        kwargs: dict = {"model": self._model, "messages": messages}
        # Only pass temperature when the model supports it AND a value is set
        # (cfg.temperature defaults to 0.0; set to None to force-omit).
        if self.supports_temperature() and self._temperature is not None:
            kwargs["temperature"] = self._temperature

        try:
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            resp = self._client.chat.completions.create(**kwargs)
        except Exception:
            # Some OpenAI-compatible endpoints reject response_format; retry without it.
            kwargs.pop("response_format", None)
            resp = self._client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""
