"""Description locator: semantic — hand a natural-language description to the VLM
and let it pick the matching region (e.g. "the red icon left of the person",
"the wifi button next to the text"). Only ``description`` is supported; the
region is determined entirely by the description via the AI.
"""
from __future__ import annotations

from ..coords import normalize_raw_boxes
from ..located import Located
from ..prompts import DESCRIPTION_PROMPT_TEMPLATE
from ..providers.base import VisionProvider
from ..utils import parse_json


class DescriptionLocator:
    def __init__(self, query: dict):
        self.description = query.get("description", "")

    def resolve(self, screenshot, width, height, provider: VisionProvider) -> list[Located]:
        if not self.description:
            return []
        prompt = DESCRIPTION_PROMPT_TEMPLATE.replace("{desc}", self.description)
        raw = provider.chat([screenshot], prompt, json_mode=True)
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
            out.append(
                Located(
                    bbox=boxes[0],
                    text=node.get("text") or None,
                )
            )
        return out
