"""Vision model transport: ONE OpenAI-compatible client for any endpoint.

The framework absorbs every provider quirk here, so the caller only ever needs
``base_url`` + ``api_key`` + ``model``:

* temperature quirks are resolved from the *model name* (reasoning/thinking
  models reject ``temperature``; kimi-k2.5/2.6 are server-managed; the kimi-k2.7
  family requires ``temperature=1.0``);
* if an endpoint rejects ``response_format`` (json mode) or ``temperature``,
  the request is retried once with that parameter dropped;
* every HTTP / network failure is mapped to a specific, actionable
  :class:`~visionauto.exceptions.ProviderError` subclass (see exceptions.py).
"""
from __future__ import annotations

import base64
from typing import Protocol, runtime_checkable

from ..exceptions import (
    ImageNotSupportedError,
    InsufficientBalanceError,
    ModelNotFoundError,
    ProviderAuthError,
    ProviderConfigError,
    ProviderConnectionError,
    ProviderError,
    ProviderRateLimitError,
)
from .config import ProviderConfig

# Normalization scale most VLMs emit for bbox coords (GLM-V/Qwen-VL: 0-999/0-1000).
DEFAULT_NORM_SCALE = 1000.0


def encode_data_url(image: bytes, mime: str = "image/png") -> str:
    return f"data:{mime};base64,{base64.b64encode(image).decode()}"


@runtime_checkable
class VisionProvider(Protocol):
    """Send images + a prompt to a VLM, return the raw text response."""

    norm_scale: float

    def chat(
        self,
        images: list[bytes],
        prompt: str,
        *,
        json_mode: bool = True,
    ) -> str: ...


# --- model-name temperature quirks (model name is all the framework sees) ---
# temperature server-managed / rejected -> omit the param entirely.
_NO_TEMPERATURE_PREFIX = ("kimi-k2.5", "kimi-k2.6", "o1", "o3", "o4")
_NO_TEMPERATURE_SUBSTR = ("qwq", "thinking", "reasoner", "deepseek-r1", "glm-z1", "-z1")
# require temperature=1.0 (prefix match covers kimi-k2.7-code / -code-highspeed).
_FORCE_TEMPERATURE_1_PREFIX = ("kimi-k2.7",)


def _temperature_for(model: str, default: float) -> float | None:
    """Resolve the temperature to send for a model, or None to omit it."""
    name = (model or "").lower()
    if any(name.startswith(p) for p in _FORCE_TEMPERATURE_1_PREFIX):
        return 1.0
    if any(name.startswith(p) for p in _NO_TEMPERATURE_PREFIX) or any(
        p in name for p in _NO_TEMPERATURE_SUBSTR
    ):
        return None
    return default


class OpenAICompatibleProvider:
    """Talk to any OpenAI-compatible Chat Completions endpoint.

    This is the single concrete provider the framework uses. It validates the
    connection config up front (clear errors instead of a later stack trace),
    resolves model quirks, and translates API failures into specific exceptions.
    """

    COORD_NORM_SCALE = DEFAULT_NORM_SCALE

    def __init__(self, cfg: ProviderConfig):
        try:
            from openai import OpenAI
        except ImportError as e:  # pragma: no cover - import guard
            raise ImportError(
                "the 'openai' package is required: pip install openai"
            ) from e
        if not cfg.api_key:
            raise ProviderConfigError(
                "missing api_key: pass api_key=... or set the VISIONAUTO_API_KEY "
                "environment variable",
                model=cfg.model,
                base_url=cfg.base_url,
            )
        if not cfg.model:
            raise ProviderConfigError(
                "missing model: pass model=... (or base_url=... together with a "
                "model name), or use a provider preset / the VISIONAUTO_MODEL "
                "environment variable",
                model=cfg.model,
                base_url=cfg.base_url,
            )
        self.cfg = cfg
        self._client = OpenAI(
            api_key=cfg.api_key,
            base_url=cfg.base_url or None,
            default_headers=cfg.extra_headers or None,
            timeout=cfg.timeout or None,
        )
        self._model = cfg.model
        self._temperature = _temperature_for(cfg.model, cfg.temperature)
        self.norm_scale = self.COORD_NORM_SCALE

    # -- public API ----------------------------------------------------------

    def chat(self, images, prompt, *, json_mode=True) -> str:
        content: list[dict] = [{"type": "text", "text": prompt}]
        for img in images:
            content.append(
                {"type": "image_url", "image_url": {"url": encode_data_url(img)}}
            )
        kwargs: dict = {
            "model": self._model,
            "messages": [{"role": "user", "content": content}],
        }
        if self._temperature is not None:
            kwargs["temperature"] = self._temperature
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        return self._create(kwargs, json_mode=json_mode)

    # -- request with adaptive fallback + error mapping ----------------------

    def _create(self, kwargs: dict, *, json_mode: bool) -> str:
        while True:
            try:
                resp = self._client.chat.completions.create(**kwargs)
                return resp.choices[0].message.content or ""
            except Exception as exc:
                self._raise_mapped(exc)  # raises for hard failures
                if not self._maybe_drop_param(exc, kwargs, json_mode):
                    # No adaptive retry applies - surface a readable error.
                    raise ProviderError(
                        f"model request failed: {str(exc)[:200]}",
                        model=self._model,
                        base_url=self.cfg.base_url,
                        status=getattr(exc, "status_code", None),
                    ) from exc

    def _maybe_drop_param(self, exc: Exception, kwargs: dict, json_mode: bool) -> bool:
        """If the endpoint rejected an optional param, drop it and retry once."""
        if getattr(exc, "status_code", None) not in (400, 422):
            return False
        low = str(exc).lower()
        if (
            json_mode
            and kwargs.get("response_format")
            and any(k in low for k in ("response_format", "json_object", "json mode", "json_mode"))
        ):
            kwargs.pop("response_format", None)
            return True
        if "temperature" in low and "temperature" in kwargs:
            kwargs.pop("temperature", None)
            return True
        return False

    # -- error mapping -------------------------------------------------------

    def _ctx(self) -> dict:
        return {"model": self._model, "base_url": self.cfg.base_url}

    def _raise_mapped(self, exc: Exception) -> None:
        """Raise a specific ProviderError for hard failures, else return None."""
        status = getattr(exc, "status_code", None)
        msg = str(exc)
        low = msg.lower()
        model = self._model
        base = self.cfg.base_url or "<default endpoint>"

        if status is None:  # network / DNS / timeout
            raise ProviderConnectionError(
                f"cannot reach the model endpoint {base}: check that base_url is "
                f"correct and the network/proxy is reachable. "
                f"original error: {msg[:160]}",
                model=model, base_url=self.cfg.base_url,
            )
        if status in (401, 403):
            raise ProviderAuthError(
                f"invalid or unauthorized API key (HTTP {status}). Check the "
                f"api_key and that it belongs to the base_url platform "
                f"(e.g. .cn/.ai - the two Moonshot platforms are not interchangeable). "
                f"original error: {msg[:160]}",
                model=model, base_url=self.cfg.base_url, status=status,
            )
        if status == 402 or "insufficient" in low or "balance" in low or "欠费" in low or "recharge" in low:
            raise InsufficientBalanceError(
                f"insufficient balance / suspended account - the model call was "
                f"rejected. Recharge or use another key. "
                f"original error: {msg[:160]}",
                model=model, base_url=self.cfg.base_url, status=status,
            )
        if status == 404:
            if any(k in low for k in ("image", "vision", "视觉", "图像")):
                raise ImageNotSupportedError(
                    f"model {model!r} has no image-input endpoint (text-only "
                    f"model) and cannot be used for vision locating. Use a "
                    f"multimodal/VL model instead. original error: {msg[:160]}",
                    model=model, base_url=self.cfg.base_url, status=status,
                )
            raise ModelNotFoundError(
                f"model not found or not enabled (HTTP 404): {model!r}. Check the "
                f"model name spelling or whether this platform/account has it. "
                f"original error: {msg[:160]}",
                model=model, base_url=self.cfg.base_url, status=status,
            )
        if status == 429:
            raise ProviderRateLimitError(
                f"rate limited (HTTP 429). Lower the request frequency or retry "
                f"later. original error: {msg[:160]}",
                model=model, base_url=self.cfg.base_url, status=status,
            )
        # image rejected as 400 (e.g. deepseek "does not support image",
        # glm "content.type only allows text")
        if status in (400, 422) and self._is_image_rejection(low):
            raise ImageNotSupportedError(
                f"model {model!r} does not support image input (text-only model) "
                f"and cannot be used for vision locating. Use a multimodal/VL "
                f"model instead. original error: {msg[:160]}",
                model=model, base_url=self.cfg.base_url, status=status,
            )
        # 400-family unknown-model wording (e.g. OpenRouter "not a valid model ID",
        # Xiaomi "Unsupported model", Zhipu "模型不存在").
        if status in (400, 422) and any(
            k in low for k in (
                "unsupported model", "model not exist", "not a valid model",
                "does not exist", "unknown model", "模型不存在", "没有可用的模型",
                "supported api model names", "you passed",
            )
        ):
            raise ModelNotFoundError(
                f"model not found or not provided by this platform (HTTP {status}): "
                f"{model!r}. Check the model name spelling or whether this "
                f"platform/account has it. original error: {msg[:160]}",
                model=model, base_url=self.cfg.base_url, status=status,
            )
        return None  # not a hard failure - let the adaptive fallback try

    @staticmethod
    def _is_image_rejection(low: str) -> bool:
        # Keep the keyword list tight to avoid misclassifying generic 400s.
        image_words = ("does not support image", "not support image", "no endpoints found that support image",
                       "不支持图片", "不支持图像", "content.type", "multimodal")
        return any(w in low for w in image_words)
