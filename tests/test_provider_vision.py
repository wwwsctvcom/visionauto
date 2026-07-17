"""Smoke tests: can the configured provider/model answer an image question?

All parameters flow through the framework's generic Config (one set of env
vars, no per-provider specifics — works with any OpenAI-compatible model):
  VISIONAUTO_PROVIDER  glm | qwen | openai   (default glm)
  VISIONAUTO_API_KEY    api key
  VISIONAUTO_MODEL      model name (defaults from the provider if any)
  VISIONAUTO_BASE_URL   endpoint (defaults from the provider if any)
  VISIONAUTO_TEST_IMAGE path to an image to send (REQUIRED to run)
  VISIONAUTO_TEST_MODELS optional comma-separated list of models to try
                         (defaults to the single configured VISIONAUTO_MODEL)

Each model is a separate test case, so you can see which models handle image
input and which do not.

Run example (qwen, multiple models):
    VISIONAUTO_PROVIDER=qwen \\
    VISIONAUTO_API_KEY=sk-xxx \\
    VISIONAUTO_TEST_IMAGE=./sample.png \\
    VISIONAUTO_TEST_MODELS=qwen3.7-max-2026-06-08,qwen3.7-plus,qwen3.6-plus,qwen3.5-plus \\
    pytest -v -s tests/test_provider_vision.py
"""
from __future__ import annotations

import os
from dataclasses import replace

import pytest

from visionauto.config import Config
from visionauto.providers import get_provider

# A plain free-text image question (no JSON), to check raw image Q&A ability.
QA_PROMPT = "请用中文简要描述这张图片的内容，并列出图中可见的文字。"


def _base_cfg() -> Config:
    cfg = Config.from_env()
    if not cfg.api_key:
        pytest.skip("set VISIONAUTO_API_KEY")
    return cfg


def _models() -> list[str]:
    listed = os.environ.get("VISIONAUTO_TEST_MODELS")
    if listed:
        return [m.strip() for m in listed.split(",") if m.strip()]
    model = Config.from_env().model
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
    cfg = replace(_base_cfg(), model=model)
    provider = get_provider(cfg)
    resp = provider.chat([test_image_bytes], QA_PROMPT, json_mode=False)
    assert isinstance(resp, str) and resp.strip(), f"empty response from {model}"
    print(f"\n[{cfg.provider} {model}] {resp[:120]}")
