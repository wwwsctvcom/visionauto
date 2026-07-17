"""Shared provider config for examples.

Three ways to set provider / api_key / base_url / model (precedence high -> low):
  1. CLI flags:        --provider --api-key --base-url --model
  2. env vars:         VISIONAUTO_PROVIDER / _API_KEY / _BASE_URL / _MODEL
  3. DEFAULTS below:   edit this dict directly

Edit DEFAULTS to hardcode your own, or pass flags at run time:
    python examples/wechat_search.py --provider glm --api-key sk-xxx --base-url https://...
    python examples/search_download.py --provider qwen --model qwen3.7-plus
"""
from __future__ import annotations

import argparse
import os

import visionauto as va

# Edit these defaults to match your account. model/base_url = None -> use the
# provider's built-in defaults (e.g. qwen -> qwen3.7-max + DashScope).
# NOTE: do NOT hardcode your api_key here — set it via env var or --api-key so
# it never lands in git. Examples will skip/run-only-with-key accordingly.
DEFAULTS = {
    "provider": "qwen",
    "api_key": None,
    "model": None,
    "base_url": None,
}

_KEYS = ("provider", "api_key", "base_url", "model")


def _resolve() -> dict:
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--provider")
    ap.add_argument("--api-key", dest="api_key")
    ap.add_argument("--base-url", dest="base_url")
    ap.add_argument("--model")
    args, _ = ap.parse_known_args()

    overrides: dict = {}
    for key in _KEYS:
        cli_val = getattr(args, key)
        env_val = os.environ.get(f"VISIONAUTO_{key.upper()}")
        default_val = DEFAULTS.get(key)
        val = cli_val or env_val or default_val
        if val:
            overrides[key] = val
    return overrides


def connect():
    """Connect to the default adb device with the resolved provider config."""
    return va.connect(**_resolve())
