"""Image matching facade, backed by airtest's aircv.

Exposes a single :func:`match` that tries template -> multiscale -> keypoint
matchers (airtest's core OpenCV capabilities) and returns absolute-pixel
bboxes. Used as the image locator's fallback when the VLM finds nothing.
"""
from __future__ import annotations

from .opencv import match

__all__ = ["match"]
