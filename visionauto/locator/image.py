"""Image-series locator: VLM matching first, airtest-backed OpenCV as fallback."""
from __future__ import annotations

from ..coords import normalize_raw_boxes, to_norm_from_abs
from ..located import Located
from ..matching import match as opencv_match
from ..prompts import IMAGE_PROMPT
from ..providers.base import VisionProvider
from ..utils import parse_json


class ImageLocator:
    def __init__(
        self,
        query: dict,
        opencv_threshold: float = 0.8,
        opencv_rgb: bool = True,
        opencv_method: str = "auto",
    ):
        self.target_path = query["image"]
        self.threshold = opencv_threshold
        self.rgb = opencv_rgb
        self.method = opencv_method

    def resolve(self, screenshot, width, height, provider: VisionProvider) -> list[Located]:
        # Primary: ask the VLM where the target template appears in the screenshot.
        vlm_hits = self._vlm_match(screenshot, width, height, provider)
        if vlm_hits:
            return vlm_hits

        # Fallback: airtest-backed OpenCV (template -> multiscale -> keypoint).
        boxes = opencv_match(
            screenshot,
            self.target_path,
            threshold=self.threshold,
            rgb=self.rgb,
            method=self.method,
            find_all=True,
        )
        return [
            Located(bbox=to_norm_from_abs(b, width, height))
            for b in boxes
        ]

    def _vlm_match(self, screenshot, width, height, provider: VisionProvider) -> list[Located]:
        target = self._read_target()
        raw = provider.chat([screenshot, target], IMAGE_PROMPT, json_mode=True)
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

    def _read_target(self) -> bytes:
        with open(self.target_path, "rb") as f:
            return f.read()


