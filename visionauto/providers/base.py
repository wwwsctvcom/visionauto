"""Transport base: shared request / retry / error-mapping across API formats.

Three wire formats share everything except the request/response shapes:
  chat.py      - OpenAI Chat Completions (default; most providers)
  messages.py  - Anthropic Messages
  responses.py - OpenAI Responses

Each subclass implements ``_init_client`` / ``_build_request`` / ``_request`` /
``_parse_response``; this base supplies the retry loop, adaptive param
dropping (temperature / top_k / json mode / max_tokens rename), temperature
quirks by model name, truncation diagnosis, and the specific-error mapping
with endpoint hints.
"""
from __future__ import annotations

import base64
from typing import Protocol, runtime_checkable

from ..exceptions import (
    ImageNotSupportedError,
    InsufficientBalanceError,
    ModelNotFoundError,
    OutputTruncatedError,
    ProviderAuthError,
    ProviderConfigError,
    ProviderConnectionError,
    ProviderError,
    ProviderRateLimitError,
)
from .types import Model, Sampling

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


def _temperature_for(model: str, default: float | None) -> float | None:
    """Resolve the temperature to send for a model, or None to omit it."""
    name = (model or "").lower()
    if any(name.startswith(p) for p in _FORCE_TEMPERATURE_1_PREFIX):
        return 1.0
    if any(name.startswith(p) for p in _NO_TEMPERATURE_PREFIX) or any(
        p in name for p in _NO_TEMPERATURE_SUBSTR
    ):
        return None
    return default


# model-name prefix -> where such models usually live; used for error hints
_ENDPOINT_HINTS = (
    ("qwen", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    ("glm", "https://open.bigmodel.cn/api/paas/v4/"),
    ("kimi", "https://api.moonshot.ai/v1 (or https://api.moonshot.cn/v1)"),
    ("deepseek", "https://api.deepseek.com/v1"),
    ("mimo", "https://api.xiaomimimo.com/v1"),
    ("claude", "https://api.anthropic.com"),
    ("gpt", "https://api.openai.com/v1"),
    ("o1", "https://api.openai.com/v1"),
    ("o3", "https://api.openai.com/v1"),
    ("o4", "https://api.openai.com/v1"),
)


def _endpoint_hint(model: str) -> str | None:
    name = (model or "").lower()
    for prefix, url in _ENDPOINT_HINTS:
        if name.startswith(prefix):
            return url
    return None


class BaseTransport:
    """Shared plumbing for all API formats; subclasses shape the payloads."""

    COORD_NORM_SCALE = DEFAULT_NORM_SCALE

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | Model | None = None,
        sampling: Sampling | None = None,
        extra_headers: dict | None = None,
        timeout: float = 120.0,
    ):
        if not api_key:
            raise ProviderConfigError(
                "missing api_key: pass api_key=... or set the VISIONAUTO_API_KEY "
                "environment variable",
                model=str(model) if model else None,
                base_url=base_url,
            )
        if not model:
            raise ProviderConfigError(
                "missing model: pass model=... (a model name or a Model preset)",
                base_url=base_url,
            )
        self._base_url = base_url
        self._api_key = api_key
        # Model mixes in str, but normalize to a plain str so SDKs/JSON never
        # see an enum repr.
        self._model = model.value if isinstance(model, Model) else str(model)
        self._sampling = sampling or Sampling()
        self._extra_headers = extra_headers
        self._timeout = timeout
        self._init_client()
        self.norm_scale = self.COORD_NORM_SCALE

    # -- subclass hooks ------------------------------------------------------

    def _init_client(self) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    def _build_request(self, images, prompt, json_mode: bool) -> dict:
        raise NotImplementedError

    def _request(self, kwargs: dict):  # pragma: no cover - overridden
        raise NotImplementedError

    def _parse_response(self, resp) -> tuple[str, bool]:
        """Return (text, truncated_by_max_tokens)."""
        raise NotImplementedError

    # -- public API -----------------------------------------------------------

    def chat(self, images, prompt, *, json_mode: bool = True) -> str:
        kwargs = self._build_request(images, prompt, json_mode)
        return self._create(kwargs)

    # -- request loop: adaptive fallback + truncation + error mapping ---------

    def _create(self, kwargs: dict) -> str:
        while True:
            try:
                resp = self._request(kwargs)
            except Exception as exc:
                self._raise_mapped(exc)  # raises for hard failures
                if not self._maybe_drop_param(exc, kwargs):
                    # No adaptive retry applies - surface a readable error.
                    raise ProviderError(
                        f"model request failed: {str(exc)[:200]}",
                        model=self._model,
                        base_url=self._base_url,
                        status=getattr(exc, "status_code", None),
                    ) from exc
                continue
            text, truncated = self._parse_response(resp)
            if truncated:
                raise OutputTruncatedError(
                    f"model output was truncated by the max_tokens limit - the "
                    f"returned JSON may be incomplete. Raise sampling.max_tokens "
                    f"and retry.",
                    model=self._model,
                    base_url=self._base_url,
                )
            return text

    def _maybe_drop_param(self, exc: Exception, kwargs: dict) -> bool:
        """If the endpoint rejected an optional sampling param, drop/rename it
        and let the caller retry once. Returns True when kwargs was changed."""
        if getattr(exc, "status_code", None) not in (400, 422):
            return False
        low = str(exc).lower()
        # Rename first: OpenAI new-style models want max_completion_tokens.
        # (Must precede the generic drop: "max_completion_tokens" contains
        # "max_tokens" as a substring.)
        if "max_completion_tokens" in low and "max_tokens" in kwargs:
            kwargs["max_completion_tokens"] = kwargs.pop("max_tokens")
            return True
        aliases = {
            "response_format": ("response_format", "json_object", "json mode", "json_mode"),
            "temperature": ("temperature",),
            "top_p": ("top_p",),
            "top_k": ("top_k",),
            "max_tokens": ("max_tokens",),
            "max_completion_tokens": ("max_completion_tokens",),
        }
        extra_keys = set(self._sampling.extra or {})
        for key in list(kwargs):
            if key in extra_keys and key in low:
                kwargs.pop(key)
                return True
            key_aliases = aliases.get(key)
            if key_aliases and any(a in low for a in key_aliases):
                kwargs.pop(key)
                return True
        return False

    # -- error mapping -------------------------------------------------------

    def _raise_mapped(self, exc: Exception) -> None:
        """Raise a specific ProviderError for hard failures, else return None."""
        status = getattr(exc, "status_code", None)
        msg = str(exc)
        low = msg.lower()
        model = self._model
        base = self._base_url or "<default endpoint>"
        hint = _endpoint_hint(model)
        hint_msg = (
            f" hint: models named {model.split('-')[0].split('/')[0]}* usually live at "
            f"{hint} - check your base_url."
            if hint else ""
        )

        if status is None:  # not an HTTP error: network vs client-side
            cls_name = type(exc).__name__.lower()
            if ("connection" in cls_name or "timeout" in cls_name
                    or "connect" in low or "timed out" in low):
                raise ProviderConnectionError(
                    f"cannot reach the model endpoint {base}: check that base_url is "
                    f"correct and the network/proxy is reachable. "
                    f"original error: {msg[:160]}",
                    model=model, base_url=self._base_url,
                )
            # client-side error (bad param, SDK misuse) - surface as-is
            raise
        if status in (401, 403):
            raise ProviderAuthError(
                f"invalid or unauthorized API key (HTTP {status}). Check the "
                f"api_key and that it belongs to the base_url platform "
                f"(e.g. .cn/.ai - the two Moonshot platforms are not interchangeable). "
                f"original error: {msg[:160]}{hint_msg}",
                model=model, base_url=self._base_url, status=status,
            )
        if status == 402 or "insufficient" in low or "balance" in low or "欠费" in low or "recharge" in low:
            raise InsufficientBalanceError(
                f"insufficient balance / suspended account - the model call was "
                f"rejected. Recharge or use another key. "
                f"original error: {msg[:160]}",
                model=model, base_url=self._base_url, status=status,
            )
        if status == 404:
            if any(k in low for k in ("image", "vision", "视觉", "图像")):
                raise ImageNotSupportedError(
                    f"model {model!r} has no image-input endpoint (text-only "
                    f"model) and cannot be used for vision locating. Use a "
                    f"multimodal/VL model instead. original error: {msg[:160]}",
                    model=model, base_url=self._base_url, status=status,
                )
            raise ModelNotFoundError(
                f"model not found or not enabled (HTTP 404): {model!r}. Check the "
                f"model name spelling or whether this platform/account has it. "
                f"original error: {msg[:160]}{hint_msg}",
                model=model, base_url=self._base_url, status=status,
            )
        if status == 429:
            raise ProviderRateLimitError(
                f"rate limited (HTTP 429). Lower the request frequency or retry "
                f"later. original error: {msg[:160]}",
                model=model, base_url=self._base_url, status=status,
            )
        # image rejected as 400 (e.g. deepseek "does not support image",
        # glm "content.type only allows text")
        if status in (400, 422) and self._is_image_rejection(low):
            raise ImageNotSupportedError(
                f"model {model!r} does not support image input (text-only model) "
                f"and cannot be used for vision locating. Use a multimodal/VL "
                f"model instead. original error: {msg[:160]}",
                model=model, base_url=self._base_url, status=status,
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
                f"platform/account has it. original error: {msg[:160]}{hint_msg}",
                model=model, base_url=self._base_url, status=status,
            )
        return None  # not a hard failure - let the adaptive fallback try

    @staticmethod
    def _is_image_rejection(low: str) -> bool:
        # Keep the keyword list tight to avoid misclassifying generic 400s.
        image_words = ("does not support image", "not support image", "no endpoints found that support image",
                       "不支持图片", "不支持图像", "content.type", "multimodal")
        return any(w in low for w in image_words)
