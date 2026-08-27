"""Smoke tests: can the configured model answer an image question?

Connection comes from env vars (works with any endpoint/format):
  VISIONAUTO_API_KEY     api key (REQUIRED to run)
  VISIONAUTO_BASE_URL    endpoint
  VISIONAUTO_MODEL       model name (REQUIRED to run)
  VISIONAUTO_API_FORMAT  chat (default) | messages | responses
  VISIONAUTO_TEST_IMAGE  path to an image to send to the model (REQUIRED to run)
  VISIONAUTO_TEST_MODELS optional comma-separated list of models to try
                         (defaults to the single configured VISIONAUTO_MODEL)

Each model is a separate test case, so you can see which models handle image
input and which do not.
"""
from __future__ import annotations

import os

import pytest

from visionauto.providers import create_transport


# A plain free-text image question (no JSON), to check raw image Q&A ability.
QA_PROMPT = "请用中文简要描述这张图片的内容，并列出图中可见的文字。"


def _env(name: str) -> str | None:
    return os.environ.get(name) or None


def _models() -> list[str]:
    listed = os.environ.get("VISIONAUTO_TEST_MODELS")
    if listed:
        return [m.strip() for m in listed.split(",") if m.strip()]
    model = _env("VISIONAUTO_MODEL")
    return [model] if model else []


@pytest.fixture(scope="session")
def test_image_path() -> str:
    p = os.environ.get("VISIONAUTO_TEST_IMAGE")
    if not p or not os.path.isfile(p):
        pytest.skip("set VISIONAUTO_TEST_IMAGE to an existing image path")
    return p


@pytest.fixture(scope="session")
def test_image_bytes(test_image_path: str) -> bytes:
    with open(test_image_path, "rb") as f:
        return f.read()


@pytest.mark.parametrize("model", _models())
def test_vision_qa(model: str, test_image_bytes: bytes):
    api_key = _env("VISIONAUTO_API_KEY")
    if not api_key:
        pytest.skip("set VISIONAUTO_API_KEY")
    provider = create_transport(
        base_url=_env("VISIONAUTO_BASE_URL"),
        api_key=api_key,
        model=model,
        api_format=_env("VISIONAUTO_API_FORMAT") or "chat",
    )
    resp = provider.chat([test_image_bytes], QA_PROMPT, json_mode=False)
    assert isinstance(resp, str) and resp.strip(), f"empty response from {model}"
    print(f"\n[{model}] {resp[:120]}")
