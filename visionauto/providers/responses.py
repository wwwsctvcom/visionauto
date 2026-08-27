"""OpenAI Responses transport (/v1/responses).

Uses the same ``openai`` package as the chat transport, via
``client.responses.create``. The protocol spells the output cap
``max_output_tokens``.
"""
from __future__ import annotations

from .base import BaseTransport, encode_data_url


class OpenAIResponsesTransport(BaseTransport):
    """``POST /v1/responses`` via the openai SDK."""

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
        content: list[dict] = [{"type": "input_text", "text": prompt}]
        for img in images:
            content.append({"type": "input_image", "image_url": encode_data_url(img)})
        kwargs: dict = {
            "model": self._model,
            "input": [{"role": "user", "content": content}],
            "max_output_tokens": self._max_tokens,
        }
        if json_mode:
            kwargs["text"] = {"format": {"type": "json_object"}}
        return kwargs

    def _request(self, kwargs: dict):
        return self._client.responses.create(**kwargs)

    def _parse_response(self, resp) -> tuple[str, bool]:
        text = getattr(resp, "output_text", "") or ""
        status = getattr(resp, "status", None)
        reason = getattr(getattr(resp, "incomplete_details", None), "reason", None)
        return text, status == "incomplete" and reason == "max_output_tokens"
