"""Shared model connection for examples.

Three ways to set base_url / api_key / model / sn (precedence high -> low):
  1. CLI flags:        --base-url --api-key --model --sn
  2. env vars:         VISIONAUTO_BASE_URL / _API_KEY / _MODEL / _SN
  3. DEFAULTS below:   edit this dict directly

Edit DEFAULTS to match your account. NOTE: do NOT hardcode your api_key here
- set it via env var or --api-key so it never lands in git.
"""
from __future__ import annotations

import argparse
import os

from visionauto import VisionDevice

# Edit these defaults to match your account.
DEFAULTS = {
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "api_key": None,
    "model": "qwen3.8-max",
    "sn": None,          # e.g. "emulator-5554" or WiFi adb "192.168.1.10:5555"
}

_KEYS = ("base_url", "api_key", "model", "sn")


def _resolve() -> dict:
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--base-url", dest="base_url")
    ap.add_argument("--api-key", dest="api_key")
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
    """Build a VisionDevice with the resolved model connection."""
    return VisionDevice(**_resolve())
