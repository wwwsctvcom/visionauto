"""Debug trace recorder.

When enabled, every AI resolution is auto-captured to ``debug_dir``:
an annotated screenshot (``NNNN_<kind>.png``) plus a line in ``trace.log``
with the query, node count, and whether it was a cache hit. Actions are
also appended to ``trace.log`` so the whole run can be replayed and you
can see exactly which step's recognition went wrong — no manual per-API calls.
"""
from __future__ import annotations

import os

from .viz import draw_nodes


class DebugRecorder:
    def __init__(self, debug_dir: str, enabled: bool = False):
        self.dir = debug_dir
        self.enabled = enabled
        self._n = 0
        if enabled:
            self._reset()

    @property
    def _log_path(self) -> str:
        # derived from self.dir so it stays correct after enable(debug_dir=...)
        return os.path.join(self.dir, "trace.log")

    def _reset(self) -> None:
        os.makedirs(self.dir, exist_ok=True)
        self._n = 0
        # truncate the log on a fresh start
        open(self._log_path, "w", encoding="utf-8").close()

    def enable(self, debug_dir: str | None = None) -> None:
        if debug_dir:
            self.dir = debug_dir
        self.enabled = True
        self._reset()

    def disable(self) -> None:
        self.enabled = False

    def _log(self, line: str) -> None:
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def record_resolve(
        self,
        query: dict,
        kind: str,
        screenshot_png: bytes,
        nodes: list,
        cached: bool,
        picked_index: int | None = None,
    ) -> None:
        if not self.enabled:
            return
        self._n += 1
        idx = f"{self._n:04d}"
        img_name = f"{idx}_{kind}.png"
        command = " ".join(f"{k}={v!r}" for k, v in query.items())
        try:
            draw_nodes(
                screenshot_png, nodes, command=command, picked_index=picked_index
            ).save(os.path.join(self.dir, img_name))
        except Exception:
            img_name = "<draw failed>"
        tag = "cached" if cached else "fresh"
        self._log(
            f"[{idx}] {kind} {command} -> {len(nodes)} nodes ({tag}) img={img_name}"
        )

    def record_action(self, action: str, detail: str = "") -> None:
        if not self.enabled:
            return
        self._log(f"       action: {action} {detail}".rstrip())
