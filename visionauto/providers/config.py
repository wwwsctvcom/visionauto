"""ProviderConfig: transport-layer settings for talking to a VLM.

Separated from the framework's behavior Config (visionauto/config.py) so each
provider manages only how it connects: api_key / model / base_url /
extra_headers / temperature.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass


@dataclass
class ProviderConfig:
    api_key: str | None = None
    model: str | None = None
    base_url: str | None = None
    # extra request headers merged into the OpenAI client's default_headers.
    extra_headers: dict[str, str] | None = None
    # default 0 for reproducibility; providers that reject temperature omit it.
    temperature: float = 0.0
    # per-request HTTP timeout (seconds); 0/None -> the openai SDK default.
    timeout: float = 120.0

    @classmethod
    def from_env(cls, prefix: str = "VISIONAUTO", **overrides) -> "ProviderConfig":
        """Build from ``{PREFIX}_API_KEY / _MODEL / _BASE_URL / _TEMPERATURE /
        _EXTRA_HEADERS``; explicit non-None overrides win."""
        kwargs: dict = {}
        for key in ("api_key", "model", "base_url"):
            val = os.environ.get(f"{prefix}_{key.upper()}")
            if val is not None:
                kwargs[key] = val

        temp_env = os.environ.get(f"{prefix}_TEMPERATURE")
        if temp_env is not None:
            try:
                kwargs["temperature"] = float(temp_env)
            except ValueError:
                raise ValueError(f"{prefix}_TEMPERATURE={temp_env!r} is not a valid float")

        timeout_env = os.environ.get(f"{prefix}_TIMEOUT")
        if timeout_env is not None:
            try:
                kwargs["timeout"] = float(timeout_env)
            except ValueError:
                raise ValueError(f"{prefix}_TIMEOUT={timeout_env!r} is not a valid float")

        headers_env = os.environ.get(f"{prefix}_EXTRA_HEADERS")
        if headers_env is not None:
            try:
                kwargs["extra_headers"] = json.loads(headers_env)
            except ValueError:
                raise ValueError(
                    f"{prefix}_EXTRA_HEADERS must be a JSON object, got {headers_env!r}"
                )

        for key, val in overrides.items():
            if val is not None:
                kwargs[key] = val
        return cls(**kwargs)
