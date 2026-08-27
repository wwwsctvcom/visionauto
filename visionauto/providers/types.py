"""User-facing connection types: ApiFormat, Model, Sampling.

These are the only "vocabulary" users need beyond VisionDevice's plain
parameters. All three are optional sugar:

* ``ApiFormat`` - which wire protocol to speak (default CHAT covers almost
  every provider; a plain string like "messages" is also accepted);
* ``Model`` - a ``str``-mixin enum of verified multimodal models, so
  ``Model.KIMI_K3 == "kimi-k3"``: preset and plain string are interchangeable;
* ``Sampling`` - request-level sampling params with sane defaults (None means
  "omit, use the endpoint default").
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ApiFormat(str, Enum):
    """Wire protocol of the model service.

    CHAT is the default and covers virtually every OpenAI-compatible provider
    (all CN vendors, OpenRouter, LiteLLM/new-api gateways, vLLM, ...).
    A plain string ("chat" / "messages" / "responses") is also accepted.
    """

    CHAT = "chat"            # OpenAI Chat Completions (/v1/chat/completions)
    MESSAGES = "messages"    # Anthropic Messages (/v1/messages)
    RESPONSES = "responses"  # OpenAI Responses (/v1/responses)


class Model(str, Enum):
    """Verified multimodal (vision-capable) models.

    Because the enum mixes in ``str``, every member IS the model name —
    ``Model.KIMI_K3 == "kimi-k3"`` — so presets and plain strings are fully
    interchangeable. Only vision-capable models are listed: text-only models
    (``mimo-v2.5-pro``, ``deepseek-v4-flash``, MiniMax M-series, ``glm-4.6``)
    raise ImageNotSupportedError and are deliberately absent.
    """

    # Qwen (DashScope: https://dashscope.aliyuncs.com/compatible-mode/v1)
    QWEN3_8_MAX = "qwen3.8-max"
    QWEN3_7_PLUS = "qwen3.7-plus"
    QWEN3_7_FLASH = "qwen3.7-flash"
    QWEN3_VL_PLUS = "qwen3-vl-plus"
    QWEN3_VL_FLASH = "qwen3-vl-flash"

    # GLM (Zhipu: https://open.bigmodel.cn/api/paas/v4/)
    GLM_5V_TURBO = "GLM-5V-Turbo"
    GLM_4_5V = "glm-4.5v"

    # DeepSeek (https://api.deepseek.com/v1)
    DEEPSEEK_V4_FLASH_VISION = "deepseek-v4-flash-vision-exp"

    # Kimi (Moonshot: https://api.moonshot.ai/v1 or https://api.moonshot.cn/v1 -
    # two platforms, keys are NOT interchangeable; pick the matching base_url)
    KIMI_K3 = "kimi-k3"
    KIMI_K2_7_CODE = "kimi-k2.7-code"
    KIMI_K2_6 = "kimi-k2.6"
    KIMI_K2_5 = "kimi-k2.5"

    # MiMo (Xiaomi: https://api.xiaomimimo.com/v1)
    MIMO_V2_5 = "mimo-v2.5"

    # OpenRouter (https://openrouter.ai/api/v1, "upstream/model" ids)
    OR_KIMI_K3 = "moonshotai/kimi-k3"
    OR_QWEN3_8_MAX = "qwen/qwen3.8-max"
    OR_MIMO_V2_5 = "xiaomi/mimo-v2.5"


@dataclass
class Sampling:
    """Request-level sampling parameters.

    ``None`` means "omit the parameter" (use the endpoint default). Params an
    endpoint rejects are auto-dropped with one retry per request, and
    ``max_tokens`` is auto-renamed to ``max_completion_tokens`` where required,
    so users never need to know the per-provider quirks.
    """

    temperature: float | None = 0.0   # 0.0 for reproducible locating
    max_tokens: int | None = None     # output cap; rename-aware per protocol
    top_p: float | None = None
    top_k: float | None = None        # supported by CN providers and Anthropic;
                                      # auto-dropped on OpenAI-protocol endpoints
    extra: dict | None = None         # escape hatch: any other request param
