"""Transport base: shared request / retry / error-mapping across API formats.

Three wire formats share everything except the request/response shapes:
  chat.py      - OpenAI Chat Completions (default; most providers)
  messages.py  - Anthropic Messages
  responses.py - OpenAI Responses

Design: the framework sends NO sampling params (temperature/top_p/top_k) -
those vary per model and are left to each endpoint's default. The only knob
is ``max_tokens`` (the output cap), which every protocol has (under different
key names) and which the framework must set anyway: Anthropic requires it,
and aggregators like OpenRouter pre-authorize the model's full output budget
when it is omitted. Each subclass implements ``_init_client`` /
``_build_request`` / ``_request`` / ``_parse_response``; this base supplies
the retry loop, adaptive param dropping (json mode, max_tokens rename),
truncation diagnosis, and the specific-error mapping with endpoint hints.
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

# Normalization scale most VLMs emit for bbox coords (GLM-V/Qwen-VL: 0-999/0-1000).
DEFAULT_NORM_SCALE = 1000.0
# Output token cap sent with every request. Generous enough for a full screen
# of bbox JSON plus thinking-model reasoning; not so large that low-balance
# aggregator accounts get rejected outright.
DEFAULT_MAX_TOKENS = 8192


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
        model: str | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        extra_headers: dict | None = None,
        timeout: float = 120.0,
    ):
        if not api_key:
            raise ProviderConfigError(
                "missing api_key: pass api_key=... or set the VISIONAUTO_API_KEY "
                "environment variable",
                model=model,
                base_url=base_url,
            )
        if not model:
            raise ProviderConfigError(
                "missing model: pass model=... (a model name from your provider)",
                base_url=base_url,
            )
        self._base_url = base_url
        self._api_key = api_key
        self._model = str(model)
        self._max_tokens = max_tokens
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
                    f"returned JSON may be incomplete. Raise the max_tokens "
                    f"argument and retry.",
                    model=self._model,
                    base_url=self._base_url,
                )
            return text

    def _maybe_drop_param(self, exc: Exception, kwargs: dict) -> bool:
        """If the endpoint rejected an optional param, drop/rename it and let
        the caller retry once. Returns True when kwargs was changed."""
        if getattr(exc, "status_code", None) not in (400, 422):
            return False
        low = str(exc).lower()
        # Rename first: OpenAI new-style models want max_completion_tokens.
        # (Must precede the drop check: "max_completion_tokens" contains
        # "max_tokens" as a substring.)
        if "max_completion_tokens" in low and "max_tokens" in kwargs:
            kwargs["max_completion_tokens"] = kwargs.pop("max_tokens")
            return True
        # Some OpenAI-compatible endpoints reject response_format (json mode);
        # the prompt itself already demands JSON, so dropping it is safe.
        if kwargs.get("response_format") and any(
            a in low for a in ("response_format", "json_object", "json mode", "json_mode")
        ):
            kwargs.pop("response_format", None)
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
