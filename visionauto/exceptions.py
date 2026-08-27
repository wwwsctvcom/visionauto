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
# Provider / transport errors - model endpoint / account / config problems,
# each with an actionable hint. These are the ones users hit most often, so
# they are separate classes for precise `except` handling.
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
    """HTTP 401/403 — invalid/expired api_key, or a key that does not belong
    to the base_url platform."""


class ModelNotFoundError(ProviderError):
    """HTTP 404 — model does not exist, name misspelled, or not enabled for
    this platform/account."""


class ImageNotSupportedError(ProviderError):
    """The model is text-only and rejects image input, so it cannot be used
    for vision locating."""


class InsufficientBalanceError(ProviderError):
    """HTTP 402 — insufficient balance / suspended account."""


class ProviderRateLimitError(ProviderError):
    """HTTP 429 — rate limited."""


class OutputTruncatedError(ProviderError):
    """Model output was cut off by the max_tokens limit, so the returned JSON
    may be incomplete. Raise sampling.max_tokens and retry."""


class ProviderConnectionError(ProviderError):
    """Cannot reach base_url (network / DNS / wrong endpoint)."""
