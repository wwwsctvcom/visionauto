"""visionauto: uiautomator2 device control with AI-vision selectors.

One entry point — VisionDevice takes the device serial (sn) and the model
connection. 最简用法，直接给 base_url + api_key + model::

    from visionauto import VisionDevice

    d = VisionDevice(
        sn="emulator-5554",                 # USB serial / WiFi adb "192.168.1.10:5555"
        base_url="https://api.deepseek.com/v1",
        api_key="sk-xxx",
        model="deepseek-v4-flash-vision-exp",
    )
    d(text="你好").click()

也可用预设名省去记 base_url：VisionDevice(sn, provider="qwen", api_key="sk-...")。
"""
from __future__ import annotations

from .config import Config
from .device import VisionDevice
from .exceptions import (
    ElementNotFound,
    ImageNotSupportedError,
    InsufficientBalanceError,
    ModelNotFoundError,
    ProviderAuthError,
    ProviderConfigError,
    ProviderConnectionError,
    ProviderError,
    ProviderRateLimitError,
    VisionAutoError,
)
from .located import Located
from .providers.models import Models
from .selector import Selector

__all__ = [
    "VisionDevice",
    "Config",
    "Models",
    "Selector",
    "Located",
    # errors
    "VisionAutoError",
    "ElementNotFound",
    "ProviderError",
    "ProviderConfigError",
    "ProviderAuthError",
    "ModelNotFoundError",
    "ImageNotSupportedError",
    "InsufficientBalanceError",
    "ProviderRateLimitError",
    "ProviderConnectionError",
]
