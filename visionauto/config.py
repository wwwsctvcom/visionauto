"""Configuration for visionauto: provider credentials, model, thresholds, timing."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Config:
    provider: str = "glm"
    api_key: str | None = None
    model: str | None = None
    base_url: str | None = None

    # image strategy: OpenCV confidence threshold; below this, fall back to VLM
    opencv_threshold: float = 0.8
    # airtest-backed matching: re-verify with BGR channels, and matcher selection.
    opencv_rgb: bool = True
    opencv_method: str = "auto"  # auto | template | multiscale | keypoint
    # how long a screenshot and its resolution are reused across calls
    cache_ttl: float = 2.0
    # default wait() timeout
    default_timeout: float = 10.0
    temperature: float = 0.0
    # collapse whitespace in returned text before text/textContains/textStartsWith
    # matching, so "设置 中心" still matches "设置中心" (AI sometimes splits labels).
    normalize_text: bool = True
    # debug trace: auto-save an annotated screenshot + log line for every AI
    # resolution, so the whole run can be replayed from debug_dir.
    debug: bool = False
    debug_dir: str = "out/trace"

    @classmethod
    def from_env(cls, **overrides) -> "Config":
        """Build config from env vars, then apply explicit overrides (non-None wins)."""
        kwargs: dict = {}

        str_map = {
            "provider": "VISIONAUTO_PROVIDER",
            "api_key": "VISIONAUTO_API_KEY",
            "model": "VISIONAUTO_MODEL",
            "base_url": "VISIONAUTO_BASE_URL",
            "opencv_method": "VISIONAUTO_OPENCV_METHOD",
            "debug_dir": "VISIONAUTO_DEBUG_DIR",
        }
        for key, env in str_map.items():
            val = os.environ.get(env)
            if val is not None:
                kwargs[key] = val

        for key in ("opencv_threshold", "cache_ttl", "default_timeout", "temperature"):
            env = f"VISIONAUTO_{key.upper()}"
            val = os.environ.get(env)
            if val is not None:
                try:
                    kwargs[key] = float(val)
                except ValueError:
                    raise ValueError(f"{env}={val!r} is not a valid float for {key}")

        kwargs["opencv_rgb"] = _env_bool("VISIONAUTO_OPENCV_RGB", True)
        kwargs["normalize_text"] = _env_bool("VISIONAUTO_NORMALIZE_TEXT", True)
        kwargs["debug"] = _env_bool("VISIONAUTO_DEBUG", False)

        for key, val in overrides.items():
            if val is not None:
                kwargs[key] = val

        return cls(**kwargs)
