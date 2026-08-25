"""Exceptions raised by visionauto."""
from __future__ import annotations


class VisionAutoError(Exception):
    """Base class for all visionauto errors."""


class ElementNotFound(VisionAutoError):
    """Raised when an action targets an element that could not be located."""

    def __init__(self, query: dict, index: int):
        self.query = query
        self.index = index
        super().__init__(
            f"no element matched {query}" + (f" [index={index}]" if index else "")
        )


# ---------------------------------------------------------------------------
# Provider / transport errors — 模型端点 / 账号 / 配置类问题，附带可操作提示。
# 这些才是用户最常撞到的，单独成类以便 `except` 精准捕获并给出指引。
# ---------------------------------------------------------------------------


class ProviderError(VisionAutoError):
    """Base for all provider/transport failures.

    Carries the model / base_url / HTTP status so the caller can log or branch.
    The message is written to be directly actionable by the user.
    """

    def __init__(
        self,
        message: str,
        *,
        model: str | None = None,
        base_url: str | None = None,
        status: int | None = None,
    ):
        self.model = model
        self.base_url = base_url
        self.status = status
        super().__init__(message)


class ProviderConfigError(ProviderError):
    """Missing or invalid connection config (e.g. no api_key / model)."""


class ProviderAuthError(ProviderError):
    """HTTP 401/403 — api_key 无效、过期，或不属于该 base_url 的平台。"""


class ModelNotFoundError(ProviderError):
    """HTTP 404 — 模型不存在、名字拼错，或该平台/账号未开通此模型。"""


class ImageNotSupportedError(ProviderError):
    """该模型是纯文本模型，不接受图像输入，无法用于视觉定位。"""


class InsufficientBalanceError(ProviderError):
    """HTTP 402 — 账户余额不足 / 欠费 / 被暂停。"""


class ProviderRateLimitError(ProviderError):
    """HTTP 429 — 触发限流。"""


class ProviderConnectionError(ProviderError):
    """连不上 base_url（网络 / DNS / 端点写错）。"""
