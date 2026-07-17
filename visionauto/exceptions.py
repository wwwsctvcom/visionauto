"""Exceptions raised by visionauto."""
from __future__ import annotations


class VisionAutoError(Exception):
    """Base class."""


class ElementNotFound(VisionAutoError):
    """Raised when an action targets an element that could not be located."""

    def __init__(self, query: dict, index: int):
        self.query = query
        self.index = index
        super().__init__(
            f"no element matched {query}" + (f" [index={index}]" if index else "")
        )
