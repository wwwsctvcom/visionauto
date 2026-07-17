"""Shared helpers for locators."""
from __future__ import annotations

import re

try:
    from json_repair import repair_json
except ImportError as e:  # pragma: no cover - import guard
    raise ImportError(
        "the 'json-repair' package is required: pip install json-repair"
    ) from e

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def parse_json(text: str) -> dict:
    """Parse a VLM response into a dict, tolerating malformed JSON.

    VLMs occasionally return trailing commas, unquoted keys, markdown fences, or
    prose around the JSON. ``json-repair`` recovers a valid object from most of
    these; we additionally strip code fences beforehand.
    """
    s = text.strip()
    if s.startswith("```"):
        s = _FENCE_RE.sub("", s).strip()

    obj = repair_json(s, return_objects=True)

    if isinstance(obj, dict):
        return obj
    if isinstance(obj, list):
        # Some models return a bare array of regions.
        return {"regions": obj}
    return {}
