"""Airtest-backed OpenCV matching: template / multiscale / keypoint.

Wraps airtest.aircv matcher classes behind one facade so the image locator
gets RGB-confidence re-checking, multi-match, multi-scale, and keypoint
(rotation/scale-tolerant) fallback without spreading airtest calls around.
"""
from __future__ import annotations

import logging
import os
from typing import Iterable

from ..coords import AbsBBox

# airtest logs at DEBUG on stderr by default; quiet it to WARNING.
logging.getLogger("airtest").setLevel(logging.WARNING)
logging.getLogger("airtest.aircv").setLevel(logging.WARNING)

_METHOD_MATCHERS = {
    "template": ("airtest.aircv.template_matching", "TemplateMatching"),
    "multiscale": ("airtest.aircv.multiscale_template_matching", "MultiScaleTemplateMatching"),
    "keypoint": ("airtest.aircv.keypoint_matching", "KAZEMatching"),
}

# 'auto' tries each in order and returns the first that yields matches.
_AUTO_ORDER = ("template", "multiscale", "keypoint")


def _load_image(src) -> "object | None":
    """Load an image from bytes or a file path into a BGR numpy array."""
    import cv2
    import numpy as np

    if isinstance(src, (bytes, bytearray)):
        arr = np.frombuffer(src, np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if isinstance(src, str) and os.path.isfile(src):
        return cv2.imread(src, cv2.IMREAD_COLOR)
    return None


def _import_matcher(method: str):
    mod_path, cls_name = _METHOD_MATCHERS[method]
    import importlib

    mod = importlib.import_module(mod_path)
    return getattr(mod, cls_name)


def _result_to_bbox(result: dict) -> AbsBBox | None:
    rect = result.get("rectangle")
    if not rect:
        return None
    xs = [p[0] for p in rect]
    ys = [p[1] for p in rect]
    return AbsBBox(int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))


def _run_matcher(Matcher, im_search, im_source, threshold, rgb, find_all) -> list[AbsBBox]:
    m = Matcher(im_search, im_source, threshold=threshold, rgb=rgb)
    if find_all:
        results = m.find_all_results() or []
    else:
        best = m.find_best_result()
        results = [best] if best else []
    out: list[AbsBBox] = []
    for r in results:
        box = _result_to_bbox(r)
        if box is not None:
            out.append(box)
    return out


def match(
    screenshot,
    template,
    *,
    threshold: float = 0.8,
    rgb: bool = True,
    method: str = "auto",
    find_all: bool = False,
) -> list[AbsBBox]:
    """Find ``template`` in ``screenshot``; return absolute-pixel bboxes.

    Args:
        screenshot: screenshot as PNG/JPG bytes (or a file path).
        template: target image as bytes (or a file path).
        threshold: minimum confidence.
        rgb: re-verify matches with BGR-channel confidence (reduces false positives).
        method: "auto" | "template" | "multiscale" | "keypoint".
        find_all: return every match (up to airtest's cap), not just the best.

    Returns absolute-pixel bboxes (in screenshot pixel space). Empty list if
    airtest/cv2 is unavailable or nothing matches.
    """
    try:
        import cv2  # noqa: F401  (airtest depends on it)
    except ImportError:
        return []

    im_source = _load_image(screenshot)
    im_search = _load_image(template)
    if im_source is None or im_search is None:
        return []

    sh, sw = im_source.shape[:2]
    th, tw = im_search.shape[:2]
    if th > sh or tw > sw:
        return []

    methods: Iterable[str]
    if method == "auto":
        methods = _AUTO_ORDER
    elif method in _METHOD_MATCHERS:
        methods = (method,)
    else:
        raise ValueError(f"unknown match method {method!r}; use auto/template/multiscale/keypoint")

    for mname in methods:
        try:
            Matcher = _import_matcher(mname)
        except Exception:
            continue
        try:
            boxes = _run_matcher(Matcher, im_search, im_source, threshold, rgb, find_all)
        except Exception:
            continue
        if boxes:
            return boxes
    return []
