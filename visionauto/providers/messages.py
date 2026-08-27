"""Anthropic Messages transport (/v1/messages).

Requires the ``anthropic`` package: ``pip install 'visionauto[anthropic]'``.
The Messages API has no response_format/json mode - the JSON shape is enforced
by the prompt and repaired client-side (json-repair), same as endpoints that
reject response_format on the chat transport.
"""
from __future__ import annotations

import base64

from .base import BaseTransport


class AnthropicMessagesTransport(BaseTransport):
    """``POST /v1/messages`` via the anthropic SDK."""

    def _init_client(self) -> None:
        try:
            import anthropic
        except ImportError as e:  # pragma: no cover - import guard
            raise ImportError(
                "the 'anthropic' package is required for ApiFormat.MESSAGES: "
                "pip install 'visionauto[anthropic]'"
            ) from e
        # auth_token sends "Authorization: Bearer ..." - accepted by both the
        # official Anthropic API and OpenRouter-compatible gateways (unlike
        # the x-api-key header, which gateways usually reject).
        # NOTE: the SDK posts to {base_url}/v1/messages, so the official
        # endpoint is "https://api.anthropic.com" (no /v1 suffix).
        self._client = anthropic.Anthropic(
            auth_token=self._api_key,
            base_url=self._base_url or None,
            default_headers=self._extra_headers or None,
            timeout=self._timeout or None,
        )

    def _build_request(self, images, prompt, json_mode: bool) -> dict:
        content: list[dict] = [{"type": "text", "text": prompt}]
        for img in images:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64.b64encode(img).decode(),
                },
            })
        # Anthropic requires max_tokens on every request.
        return {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": [{"role": "user", "content": content}],
        }

    def _request(self, kwargs: dict):
        return self._client.messages.create(**kwargs)

    def _parse_response(self, resp) -> tuple[str, bool]:
        text = "".join(
            block.text for block in resp.content
            if getattr(block, "type", "") == "text"
        )
        return text, resp.stop_reason == "max_tokens"
