"""Model connection layer (internal).

Users never touch this package directly: they pass base_url / api_key /
model / api_format / sampling straight to ``VisionDevice``, which builds the
right transport here. The user-facing types live in ``providers.types`` and
are re-exported from the ``visionauto`` top level.
"""
from __future__ import annotations

from ..exceptions import ProviderConfigError
from .base import BaseTransport, VisionProvider
from .chat import ChatCompletionsTransport
from .messages import AnthropicMessagesTransport
from .responses import OpenAIResponsesTransport
from .types import ApiFormat, Model, Sampling

_TRANSPORTS: dict[ApiFormat, type[BaseTransport]] = {
    ApiFormat.CHAT: ChatCompletionsTransport,
    ApiFormat.MESSAGES: AnthropicMessagesTransport,
    ApiFormat.RESPONSES: OpenAIResponsesTransport,
}


def create_transport(
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | Model | None = None,
    api_format: ApiFormat | str = ApiFormat.CHAT,
    sampling: Sampling | dict | None = None,
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
            model=str(model) if model else None,
            base_url=base_url,
        )
    if sampling is None:
        sampling = Sampling()
    elif isinstance(sampling, dict):
        sampling = Sampling(**sampling)
    return _TRANSPORTS[fmt](
        base_url=base_url,
        api_key=api_key,
        model=model,
        sampling=sampling,
        extra_headers=extra_headers,
        timeout=timeout,
    )


__all__ = [
    "create_transport",
    "VisionProvider",
    "BaseTransport",
    "ChatCompletionsTransport",
    "AnthropicMessagesTransport",
    "OpenAIResponsesTransport",
    "ApiFormat",
    "Model",
    "Sampling",
]
