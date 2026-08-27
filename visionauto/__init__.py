"""visionauto: uiautomator2 device control with AI-vision selectors.

One entry point - VisionDevice takes the device serial (sn) and the model
connection. The connection is three plain values users already know::

    from visionauto import VisionDevice

    d = VisionDevice(
        sn="emulator-5554",                 # USB serial / WiFi adb "192.168.1.10:5555"
        base_url="https://api.deepseek.com/v1",
        api_key="sk-xxx",
        model="deepseek-v4-flash-vision-exp",   # a model name from your provider
    )
    d(text="你好").click()

Optional: api_format=ApiFormat.MESSAGES / RESPONSES (default CHAT) and
max_tokens=8192 (output cap; thinking models may need more).
"""
from __future__ import annotations

from .config import Config
from .device import VisionDevice
from .exceptions import (
    ElementNotFound,
    ImageNotSupportedError,
    InsufficientBalanceError,
    ModelNotFoundError,
    OutputTruncatedError,
    ProviderAuthError,
    ProviderConfigError,
    ProviderConnectionError,
    ProviderError,
    ProviderRateLimitError,
    VisionAutoError,
)
from .located import Located
from .providers.types import ApiFormat
from .selector import Selector

__all__ = [
    "VisionDevice",
    "Config",
    # connection types
    "ApiFormat",
    # selector layer
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
    "OutputTruncatedError",
]
