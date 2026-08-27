"""OpenAI Chat Completions transport - the default api_format.

Covers virtually every OpenAI-compatible provider: all CN vendors (DashScope,
Zhipu, Moonshot, Xiaomi, DeepSeek), OpenRouter, LiteLLM/new-api gateways,
vLLM/Ollama self-hosting, ...
"""
from __future__ import annotations

from .base import BaseTransport, encode_data_url


class ChatCompletionsTransport(BaseTransport):
    """``POST /v1/chat/completions`` via the openai SDK."""

    def _init_client(self) -> None:
        try:
            from openai import OpenAI
        except ImportError as e:  # pragma: no cover - import guard
            raise ImportError(
                "the 'openai' package is required: pip install openai"
            ) from e
        self._client = OpenAI(
            api_key=self._api_key,
            base_url=self._base_url or None,
            default_headers=self._extra_headers or None,
            timeout=self._timeout or None,
        )

    def _build_request(self, images, prompt, json_mode: bool) -> dict:
        content: list[dict] = [{"type": "text", "text": prompt}]
        for img in images:
            content.append(
                {"type": "image_url", "image_url": {"url": encode_data_url(img)}}
            )
        kwargs: dict = {
            "model": self._model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": self._max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        return kwargs

    def _request(self, kwargs: dict):
        return self._client.chat.completions.create(**kwargs)

    def _parse_response(self, resp) -> tuple[str, bool]:
        choice = resp.choices[0]
        text = choice.message.content or ""
        return text, choice.finish_reason == "length"
