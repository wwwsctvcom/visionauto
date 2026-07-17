"""A located element: its bbox plus whatever metadata the locator recovered."""
from __future__ import annotations

from dataclasses import dataclass

from .coords import BBox


@dataclass
class Located:
    """One tappable UI node recovered from a screenshot.

    The bbox is the node's tappable area (for an icon with a label, one node
    covers the icon and carries the label as ``text`` — not a separate text
    region). Only what is visible on screen is described; there is no nesting.
    """

    bbox: BBox
    text: str | None = None

    def to_abs(self, w: int, h: int):
        return self.bbox.to_abs(w, h)

    def center_abs(self, w: int, h: int) -> tuple[int, int]:
        return self.bbox.to_abs(w, h).center()
