"""VisionDevice: wraps a uiautomator2 device, adds AI-vision selectors."""
from __future__ import annotations

import io
import os
import time
from typing import Any

from .cache import TTLCache
from .config import Config
from .debug import DebugRecorder
from .providers import get_provider
from .providers.base import VisionProvider
from .selector import Selector


class VisionDevice:
    def __init__(self, u2_device: Any, config: Config):
        self._u2 = u2_device
        self._config = config
        self._provider: VisionProvider = get_provider(config)
        self._cache = TTLCache(config.cache_ttl)
        self._shot_bytes: bytes | None = None
        self._shot_size: tuple[int, int] | None = None
        self._shot_expires: float = 0.0
        self._debug = DebugRecorder(config.debug_dir, config.debug)

    # -- debug trace --------------------------------------------------------

    @property
    def debug(self) -> bool:
        return self._debug.enabled

    @debug.setter
    def debug(self, value: bool) -> None:
        if value:
            self._debug.enable()
        else:
            self._debug.disable()

    def start_debug(self, debug_dir: str | None = None) -> None:
        """Enable auto-capture of every AI resolution to the trace dir."""
        self._debug.enable(debug_dir)

    def stop_debug(self) -> None:
        self._debug.disable()

    def dump(self, out_path: str | None = None) -> list:
        """Capture the full screen's clickable nodes (visual dump_hierarchy).

        Returns the Located list and saves an annotated image if out_path given.
        """
        shot, (w, h) = self._screenshot(force=True)
        from .locator.text import TextLocator

        locs = TextLocator(
            {}, normalize_text=self._config.normalize_text, match_all=True
        ).resolve(shot, w, h, self._provider)
        if out_path:
            from .viz import draw_nodes

            draw_nodes(shot, locs).save(out_path)
        return locs

    # -- screenshot (TTL cached so exists()+click() reuse one frame) --------

    def _screenshot(self, force: bool = False) -> tuple[bytes, tuple[int, int]]:
        now = time.monotonic()
        if force or self._shot_bytes is None or now > self._shot_expires:
            img = self._u2.screenshot()  # PIL.Image
            w, h = img.size
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            self._shot_bytes = buf.getvalue()
            self._shot_size = (w, h)
            self._shot_expires = now + self._config.cache_ttl
            self._cache.clear()  # new frame invalidates prior resolutions
        assert self._shot_bytes is not None and self._shot_size is not None
        return self._shot_bytes, self._shot_size

    def _clamp(self, x: int, y: int) -> tuple[int, int]:
        w, h = self.window_size()
        return (max(0, min(x, w - 1)), max(0, min(y, h - 1)))

    # -- selector factory ---------------------------------------------------

    def __call__(self, **query) -> Selector:
        index = query.pop("index", 0)
        return Selector(self, query, index)

    # -- implicit wait ------------------------------------------------------

    def implicitly_wait(self, seconds: float) -> None:
        """Set implicit wait: exists()/actions poll up to this many seconds."""
        self._config.implicit_wait = seconds

    # -- assertions (auto-screenshot on failure) ----------------------------

    def _fail_shot(self, label: str, query: dict) -> str | None:
        """Save a fresh screenshot + sidecar txt to fail_dir; return png path."""
        try:
            shot, _ = self._screenshot(force=True)
            os.makedirs(self._config.fail_dir, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            safe_q = "_".join(f"{k}-{v}" for k, v in query.items())
            safe_q = "".join(c if c.isalnum() or c in "-_." else "-" for c in safe_q)[:60]
            base = f"{label}_{ts}_{safe_q}"
            png = os.path.join(self._config.fail_dir, base + ".png")
            with open(png, "wb") as f:
                f.write(shot)
            with open(os.path.join(self._config.fail_dir, base + ".txt"), "w", encoding="utf-8") as f:
                f.write(f"{label}\nquery: {query}\ntime: {ts}\n")
            return png
        except Exception:
            return None

    def _fail(self, label: str, query: dict, msg: str) -> None:
        shot = self._fail_shot(label, query)
        raise AssertionError(msg + (f"  [screenshot: {shot}]" if shot else "  [screenshot failed]"))

    def assert_exists(self, **query) -> bool:
        """Assert an element is present (respects implicit_wait)."""
        if self(**query).exists():
            return True
        self._fail("assert_exists", query, f"assert_exists failed: not found {query}")

    def assert_gone(self, **query) -> bool:
        """Assert an element is absent (waits up to implicit_wait/default_timeout)."""
        timeout = self._config.implicit_wait or self._config.default_timeout
        if self(**query).wait_gone(timeout=timeout):
            return True
        self._fail("assert_gone", query, f"assert_gone failed: still present {query}")

    def assert_text(self, expected: str, **query) -> bool:
        """Assert an element's text equals ``expected``."""
        sel = self(**query)
        if not sel.exists():
            self._fail("assert_text", query, f"assert_text failed: element not found {query}")
        actual = sel.get_text()
        if actual == expected:
            return True
        self._fail("assert_text", query, f"assert_text failed: expected {expected!r}, got {actual!r} {query}")

    def assert_count(self, expected: int, **query) -> bool:
        """Assert the number of matches equals ``expected``."""
        n = self(**query).count()
        if n == expected:
            return True
        self._fail("assert_count", query, f"assert_count failed: expected {expected}, got {n} {query}")

    # -- u2 API passthrough -------------------------------------------------
    # Any attribute not defined on VisionDevice is delegated to the underlying
    # uiautomator2 device, so the full u2 API works directly on `d`:
    #   d.app_start("pkg"), d.press("back"), d.swipe(...), d.window_size(), ...
    # Vision selectors are unaffected because they go through __call__, not attr access.

    def __getattr__(self, name):
        u2_dev = self.__dict__.get("_u2")
        if u2_dev is None:
            raise AttributeError(name)
        return getattr(u2_dev, name)

    @property
    def u2(self):
        """The underlying uiautomator2 device, for explicit access if needed."""
        return self._u2
