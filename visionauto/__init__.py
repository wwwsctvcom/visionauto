"""visionauto: uiautomator2 device control with AI-vision selectors.

One entry point — VisionDevice takes the device serial (sn) and a provider::

    from visionauto import VisionDevice, Config, Models
    from visionauto.providers.kimi import KimiProvider
    from visionauto.providers.config import ProviderConfig

    d = VisionDevice(
        sn="emulator-5554",                 # USB serial / WiFi adb "192.168.1.10:5555"
        provider=KimiProvider(ProviderConfig(api_key="sk-xxx", model=Models.KIMI_K3)),
    )
    d(text="你好").click()
"""
from __future__ import annotations

from .config import Config
from .device import VisionDevice
from .exceptions import ElementNotFound, VisionAutoError
from .located import Located
from .providers.models import Models
from .selector import Selector

__all__ = [
    "VisionDevice",
    "Config",
    "Models",
    "Selector",
    "Located",
    "ElementNotFound",
    "VisionAutoError",
]
