"""Selector: a lazy handle to one or more located elements, mirroring u2's API."""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from .exceptions import ElementNotFound
from .locator.image import ImageLocator
from .locator.text import TextLocator
from .locator.description import DescriptionLocator
from .located import Located

if TYPE_CHECKING:
    from .device import VisionDevice


class Selector:
    def __init__(self, device: "VisionDevice", query: dict, index: int = 0):
        self._device = device
        self._query = query
        self._index = index

    # -- resolution ---------------------------------------------------------

    def _locator(self):
        cfg = self._device._config
        if "image" in self._query:
            return ImageLocator(
                self._query,
                opencv_threshold=cfg.opencv_threshold,
                opencv_rgb=cfg.opencv_rgb,
                opencv_method=cfg.opencv_method,
            )
        if "description" in self._query:
            return DescriptionLocator(self._query)
        return TextLocator(self._query, normalize_text=cfg.normalize_text)

    def _resolve(self, force_shot: bool = False) -> list[Located]:
        shot, (w, h) = self._device._screenshot(force=force_shot)
        key = (hash(shot), tuple(sorted(self._query.items())))
        cached = self._device._cache.get(key)
        if cached is not None:
            self._device._debug.record_resolve(
                self._query, self._kind(), shot, cached, cached=True,
                picked_index=self._index,
            )
            return cached
        locs = self._locator().resolve(shot, w, h, self._device._provider)
        self._device._cache.set(key, locs)
        self._device._debug.record_resolve(
            self._query, self._kind(), shot, locs, cached=False,
            picked_index=self._index,
        )
        return locs

    def _kind(self) -> str:
        if "image" in self._query:
            return "image"
        if "description" in self._query:
            return "description"
        return "text"

    def _pick(self, force_shot: bool = False) -> Located | None:
        locs = self._resolve(force_shot=force_shot)
        if not locs:
            return None
        if self._index >= len(locs):
            return None
        return locs[self._index]

    def all(self) -> list[Located]:
        """Return every match for this query."""
        return list(self._resolve())

    # -- queries ------------------------------------------------------------

    def exists(self) -> bool:
        return self._pick() is not None

    def wait(self, timeout: float | None = None, interval: float = 0.5) -> bool:
        """Poll with fresh screenshots until the element appears or timeout."""
        deadline = time.monotonic() + (timeout if timeout is not None else self._device._config.default_timeout)
        while time.monotonic() < deadline:
            if self._pick(force_shot=True) is not None:
                return True
            time.sleep(interval)
        return False

    def wait_gone(self, timeout: float | None = None, interval: float = 0.5) -> bool:
        deadline = time.monotonic() + (timeout if timeout is not None else self._device._config.default_timeout)
        while time.monotonic() < deadline:
            if self._pick(force_shot=True) is None:
                return True
            time.sleep(interval)
        return False

    # -- actions ------------------------------------------------------------

    def _require(self) -> Located:
        loc = self._pick()
        if loc is None:
            raise ElementNotFound(self._query, self._index)
        return loc

    def center(self) -> tuple[int, int]:
        loc = self._require()
        _, (w, h) = self._device._screenshot()
        x, y = loc.center_abs(w, h)
        return self._device._clamp(x, y)

    def click(self) -> None:
        x, y = self.center()
        self._device._u2.click(x, y)
        self._device._debug.record_action("click", f"at ({x},{y}) {self._query}")

    def long_click(self, duration: float | None = None) -> None:
        x, y = self.center()
        if duration is None:
            self._device._u2.long_click(x, y)
        else:
            self._device._u2.long_click(x, y, duration)
        self._device._debug.record_action("long_click", f"at ({x},{y}) {self._query}")

    def get_text(self) -> str | None:
        """Return the element's text.

        Always present for text matches; may be None for image matches (image
        only yields coordinates) and may or may not be present for description
        matches — by design.
        """
        loc = self._require()
        return loc.text

    def bounds(self) -> tuple[int, int, int, int]:
        """Return the element's absolute-pixel bbox (x1, y1, x2, y2), clamped."""
        loc = self._require()
        _, (w, h) = self._device._screenshot()
        box = loc.to_abs(w, h).clamp(w, h)
        return (box.x1, box.y1, box.x2, box.y2)

    def count(self) -> int:
        """Number of matches for this query."""
        return len(self._resolve())

    def input(self, text: str, clear: bool = False) -> None:
        """Click the element then type ``text`` into it.

        Works for any locator kind (text/image/description): click center to
        focus, then send keys via u2.
        """
        self.click()
        self._device._u2.send_keys(text, clear=clear)
        self._device._debug.record_action("input", f"{text!r} into {self._query}")

    def drag_to(self, *, duration: float = 0.5, **query) -> None:
        """Drag this element onto the element described by ``query``.

            d(description="A").drag_to(image="b.png")
            d(text="A").drag_to(text="B", duration=1.0)

        Both coordinates are resolved from the same (cached) screenshot so the
        start and end points stay consistent.
        """
        if not query:
            raise ValueError("drag_to needs target query kwargs, e.g. .drag_to(text='B')")
        other = self._device(**query)
        sx, sy = self.center()
        ex, ey = other.center()
        self._device._u2.drag(sx, sy, ex, ey, duration)
        self._device._debug.record_action("drag_to", f"{self._query} -> {query} ({sx},{sy})->({ex},{ey})")

    def swipe(self, direction: str, scale: float = 0.9, duration: float = 0.5) -> None:
        """Swipe within/from this element's bbox in a direction, u2-swipe_ext style.

        direction: "left" | "right" | "up" | "down". scale in (0, 1] is the
        swipe length as a fraction of the element box.
        """
        box = self.bounds()
        self._device._u2.swipe_ext(direction, scale=scale, box=box, duration=duration)
        self._device._debug.record_action("swipe", f"{direction} scale={scale} box={box}")

    def click_exists(self, timeout: float | None = None) -> bool:
        """Click if present; return whether a click happened. Polls up to timeout."""
        if timeout is None or timeout <= 0:
            if self.exists():
                self.click()
                return True
            return False
        if self.wait(timeout):
            self.click()
            return True
        return False

    def __repr__(self) -> str:
        return f"<Selector {self._query} index={self._index}>"
