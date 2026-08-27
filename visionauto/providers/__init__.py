"""Model connection layer (internal).

Users never touch this package directly: they pass base_url / api_key /
model / api_format / max_tokens straight to ``VisionDevice``, which builds
the right transport here. The user-facing ApiFormat type lives in
``providers.types`` and is re-exported from the ``visionauto`` top level.
"""
from __future__ import annotations

from ..exceptions import ProviderConfigError
from .base import BaseTransport, DEFAULT_MAX_TOKENS, VisionProvider
from .chat import ChatCompletionsTransport
from .messages import AnthropicMessagesTransport
from .responses import OpenAIResponsesTransport
from .types import ApiFormat

_TRANSPORTS: dict[ApiFormat, type[BaseTransport]] = {
    ApiFormat.CHAT: ChatCompletionsTransport,
    ApiFormat.MESSAGES: AnthropicMessagesTransport,
    ApiFormat.RESPONSES: OpenAIResponsesTransport,
}


def create_transport(
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    api_format: ApiFormat | str = ApiFormat.CHAT,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    extra_headers: dict | None = None,
    timeout: float = 120.0,
) -> VisionProvider:
    """Build the transport matching ``api_format`` (validated up front)."""
    try:
        fmt = ApiFormat(api_format)
    except ValueError:
        valid = [f.value for f in ApiFormat]
        raise ProviderConfigError(
            f"invalid api_format {api_format!r}; valid values: {valid}",
            model=model,
            base_url=base_url,
        )
    return _TRANSPORTS[fmt](
        base_url=base_url,
        api_key=api_key,
        model=model,
        max_tokens=max_tokens,
        extra_headers=extra_headers,
        timeout=timeout,
    )


__all__ = [
    "create_transport",
    "DEFAULT_MAX_TOKENS",
    "VisionProvider",
    "BaseTransport",
    "ChatCompletionsTransport",
    "AnthropicMessagesTransport",
    "OpenAIResponsesTransport",
    "ApiFormat",
]
