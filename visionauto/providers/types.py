"""User-facing connection types.

``ApiFormat`` is the only sugar users need beyond VisionDevice's plain
parameters: it picks the wire protocol (default CHAT covers almost every
provider; a plain string like "messages" is also accepted). Model names and
sampling params are deliberately NOT wrapped here - model ids are
provider-specific dialects users copy from their own console, and sampling
params vary per model, so the framework sends none of them except a single
``max_tokens`` output cap.
"""
from __future__ import annotations

from enum import Enum


class ApiFormat(str, Enum):
    """Wire protocol of the model service.

    CHAT is the default and covers virtually every OpenAI-compatible provider
    (all CN vendors, OpenRouter, LiteLLM/new-api gateways, vLLM, ...).
    A plain string ("chat" / "messages" / "responses") is also accepted.
    """

    CHAT = "chat"            # OpenAI Chat Completions (/v1/chat/completions)
    MESSAGES = "messages"    # Anthropic Messages (/v1/messages)
    RESPONSES = "responses"  # OpenAI Responses (/v1/responses)
