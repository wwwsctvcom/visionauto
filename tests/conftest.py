"""Shared fixtures for provider tests.

Configuration is fully generic (one set of env vars, no per-provider specifics):
  VISIONAUTO_PROVIDER  glm | qwen | openai   (default glm)
  VISIONAUTO_API_KEY    api key
  VISIONAUTO_MODEL      model name (defaults from the provider if any)
  VISIONAUTO_BASE_URL   endpoint (defaults from the provider if any)
  VISIONAUTO_TEST_IMAGE path to an image to send to the model (REQUIRED to run)
  VISIONAUTO_TEST_MODELS optional comma-separated list of models to try
"""
from __future__ import annotations

import os

import pytest


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
