"""Text-series locator: ask the VLM for flat tappable nodes, then filter."""
from __future__ import annotations

import re

from ..coords import normalize_raw_boxes
from ..located import Located
from ..prompts import TEXT_PROMPT
from ..providers.base import VisionProvider
from ..utils import parse_json

_TEXT_KEYS = ("text", "textContains", "textStartsWith", "textMatches")


def _collapse_ws(s: str) -> str:
    """Remove all whitespace so minor AI splits (e.g. "设置 中心") still match."""
    return re.sub(r"\s+", "", s or "")


def _match(node: Located, query: dict, normalize: bool = True) -> bool:
    raw = node.text or ""
    text = _collapse_ws(raw) if normalize else raw

    if "text" in query:
        q = _collapse_ws(query["text"]) if normalize else query["text"]
        return text == q
    if "textContains" in query:
        q = _collapse_ws(query["textContains"]) if normalize else query["textContains"]
        return q in text
    if "textStartsWith" in query:
        q = _collapse_ws(query["textStartsWith"]) if normalize else query["textStartsWith"]
        return text.startswith(q)
    if "textMatches" in query:
        # Regex matched against the (whitespace-collapsed) text; users can write
        # \s* if they want to tolerate spaces instead.
        return re.search(query["textMatches"], text) is not None
    # No text key in query: match nothing (a query should carry a text condition).
    return False


class TextLocator:
    def __init__(self, query: dict, normalize_text: bool = True, match_all: bool = False):
        self.query = query
        self.normalize = normalize_text
        self.match_all = match_all

    def resolve(self, screenshot, width, height, provider: VisionProvider) -> list[Located]:
        raw = provider.chat([screenshot], TEXT_PROMPT, json_mode=True)
        data = parse_json(raw)
        norm_scale = getattr(provider, "norm_scale", 1000.0)
        out: list[Located] = []
        for node in data.get("nodes", []):
            bbox = node.get("bbox")
            if not bbox or len(bbox) < 4:
                continue
            boxes = normalize_raw_boxes(
                [bbox], norm_scale=norm_scale, width=width, height=height
            )
            if not boxes:
                continue
            loc = Located(
                bbox=boxes[0],
                text=node.get("text") or None,
            )
            if self.match_all or _match(loc, self.query, self.normalize):
                out.append(loc)
        return out
