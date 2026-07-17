"""visionauto: uiautomator2 device control with AI-vision selectors.

Usage::

    import visionauto as va
    d = va.connect(api_key="sk-xxx")          # or set VISIONAUTO_API_KEY

    d(text="你好").click()
    d(textContains="设置").exists()
    d(text="删除", index=2).click()
    d(description="左上角的红色图标").center()
    d(image="./test.png").click()

    btn = d(text="你好")
    if btn.exists():
        btn.click()
"""
from __future__ import annotations

from typing import Any

from .config import Config
from .device import VisionDevice
from .exceptions import ElementNotFound, VisionAutoError
from .located import Located
from .selector import Selector


def connect(serial: str | None = None, **config_overrides) -> VisionDevice:
    """Connect to an Android device via uiautomator2 and wrap it with vision selectors.

    Config precedence: explicit kwargs > env vars (VISIONAUTO_*) > defaults.
    """
    cfg = Config.from_env(**config_overrides)
    import uiautomator2 as u2

    u2_dev = u2.connect(serial) if serial else u2.connect()
    return VisionDevice(u2_dev, cfg)


__all__ = [
    "connect",
    "VisionDevice",
    "Selector",
    "Located",
    "Config",
    "ElementNotFound",
    "VisionAutoError",
]
