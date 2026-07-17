"""Locator strategies: turn a screenshot + query into a list of Located elements."""
from __future__ import annotations

from .base import Locator
from .text import TextLocator
from .description import DescriptionLocator
from .image import ImageLocator

__all__ = ["Locator", "TextLocator", "DescriptionLocator", "ImageLocator"]
