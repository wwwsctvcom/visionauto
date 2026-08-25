"""Shared provider config for examples.

Three ways to set provider / api_key / base_url / model / sn (precedence high -> low):
  1. CLI flags:        --provider --api-key --base-url --model --sn
  2. env vars:         VISIONAUTO_PROVIDER / _API_KEY / _BASE_URL / _MODEL / _SN
  3. DEFAULTS below:   edit this dict directly

Edit DEFAULTS to match your account. model/base_url = None -> use the
provider preset's built-in defaults (e.g. qwen -> qwen3.7-max + DashScope).
NOTE: do NOT hardcode your api_key here - set it via env var or --api-key so
it never lands in git. Examples will skip/run-only-with-key accordingly.
"""
from __future__ import annotations

import argparse
import os

from visionauto import VisionDevice

# Edit these defaults to match your account. model/base_url = None -> use the
# provider preset's built-in defaults (e.g. qwen -> qwen3.7-max + DashScope).
DEFAULTS = {
    "provider": "qwen",
    "api_key": None,
    "model": None,
    "base_url": None,
    "sn": None,          # e.g. "emulator-5554" or WiFi adb "192.168.1.10:5555"
}

_KEYS = ("provider", "api_key", "base_url", "model", "sn")


def _resolve() -> dict:
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--provider")
    ap.add_argument("--api-key", dest="api_key")
    ap.add_argument("--base-url", dest="base_url")
    ap.add_argument("--model")
    ap.add_argument("--sn")
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


def connect() -> VisionDevice:
    """Build a VisionDevice with the resolved model connection.

    VisionDevice natively accepts base_url/api_key/model (any OpenAI-compatible
    endpoint) plus the optional provider preset name.
    """
    return VisionDevice(**_resolve())
