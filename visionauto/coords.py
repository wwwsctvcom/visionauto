"""Coordinate handling: convert VLM bbox coords to device pixels.

Internal canonical representation is [0,1] normalized. Different VLMs emit
coords in different scales (GLM-V / Qwen-VL typically 0-999/0-1000; some use
[0,1]; some return absolute pixels). ``normalize_raw_boxes`` auto-detects the
magnitude and converts to canonical [0,1] using the screenshot's real size when
needed, so the conversion always reflects the actual image scale.
"""
from __future__ import annotations

from dataclasses import dataclass

# Default normalization scale most VLMs use. Providers can override via
# ``COORD_NORM_SCALE``. GLM-V / Qwen-VL emit values in 0-999 / 0-1000.
DEFAULT_NORM_SCALE = 1000.0


@dataclass
class BBox:
    """Canonical normalized bounding box in [0, 1] coordinate space."""

    x1: float
    y1: float
    x2: float
    y2: float

    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    def area(self) -> float:
        return max(0.0, self.x2 - self.x1) * max(0.0, self.y2 - self.y1)

    def to_abs(self, w: int, h: int) -> "AbsBBox":
        return AbsBBox(
            int(round(self.x1 * w)),
            int(round(self.y1 * h)),
            int(round(self.x2 * w)),
            int(round(self.y2 * h)),
        )


@dataclass
class AbsBBox:
    """Bounding box in absolute device pixels."""

    x1: int
    y1: int
    x2: int
    y2: int

    def center(self) -> tuple[int, int]:
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    def clamp(self, w: int, h: int) -> "AbsBBox":
        return AbsBBox(
            max(0, min(self.x1, w)),
            max(0, min(self.y1, h)),
            max(0, min(self.x2, w)),
            max(0, min(self.y2, h)),
        )


def to_norm_from_abs(box: AbsBBox, w: int, h: int) -> BBox:
    """Convert an absolute-pixel box (from OpenCV etc.) to canonical [0,1]."""
    return BBox(box.x1 / w, box.y1 / h, box.x2 / w, box.y2 / h)


def normalize_raw_boxes(
    boxes: list[list[float]],
    norm_scale: float = DEFAULT_NORM_SCALE,
    width: int | None = None,
    height: int | None = None,
) -> list[BBox]:
    """Convert raw VLM bbox coords to canonical [0,1] BBoxes.

    Auto-detects the magnitude of the returned coordinates:
      * max <= 1.0        -> already [0,1], used as-is
      * max <= norm_scale -> [0, norm_scale], divided by norm_scale
      * max > norm_scale  -> absolute pixels; divided by width/height
                             (requires width and height to be passed)

    This makes the conversion robust across models that disagree on scale and
    always maps to real pixel dimensions of the screenshot.
    """
    if not boxes:
        return []

    valid = [b for b in boxes if len(b) >= 4]
    if not valid:
        return []

    mx = 0.0
    for b in valid:
        mx = max(mx, float(b[2]), float(b[3]))

    if mx <= 1.0:
        divisor_x = divisor_y = 1.0
    elif mx <= norm_scale:
        divisor_x = divisor_y = norm_scale
    else:
        if not width or not height:
            raise ValueError(
                f"VLM returned absolute-pixel coords (max={mx}) but screenshot "
                f"size was not provided; cannot scale."
            )
        divisor_x, divisor_y = float(width), float(height)

    out: list[BBox] = []
    for b in valid:
        out.append(
            BBox(
                float(b[0]) / divisor_x,
                float(b[1]) / divisor_y,
                float(b[2]) / divisor_x,
                float(b[3]) / divisor_y,
            )
        )
    return out
