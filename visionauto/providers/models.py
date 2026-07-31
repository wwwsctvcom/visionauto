"""Model name catalog, aggregated from each provider module.

Each provider defines its own model-id constants in its own file; this module
collects them into a single ``Models`` class for convenient reference:

    from visionauto.providers.models import Models
    KimiProvider(ProviderConfig(api_key=..., model=Models.KIMI_K3))
"""
from __future__ import annotations

from .glm import GLM_4_5V, GLM_5V_TURBO
from .kimi import KIMI_K2_5, KIMI_K2_6, KIMI_K2_7, KIMI_K2_7_CODE, KIMI_K3
from .mimo import MIMO_V2_5, MIMO_V2_5_PRO, MIMO_V2_OMNI
from .qwen import (
    QWEN3_5_PLUS,
    QWEN3_6_PLUS,
    QWEN3_7_FLASH,
    QWEN3_7_MAX,
    QWEN3_7_PLUS,
    QWEN3_VL_FLASH,
    QWEN3_VL_PLUS,
    QWEN_VL_MAX,
)


class Models:
    # Kimi (Moonshot) — latest: k3
    KIMI_K3 = KIMI_K3
    KIMI_K2_7 = KIMI_K2_7
    KIMI_K2_7_CODE = KIMI_K2_7_CODE
    KIMI_K2_6 = KIMI_K2_6
    KIMI_K2_5 = KIMI_K2_5

    # MiMo (Xiaomi)
    MIMO_V2_OMNI = MIMO_V2_OMNI
    MIMO_V2_5_PRO = MIMO_V2_5_PRO
    MIMO_V2_5 = MIMO_V2_5

    # GLM (Zhipu)
    GLM_5V_TURBO = GLM_5V_TURBO
    GLM_4_5V = GLM_4_5V

    # Qwen (DashScope)
    QWEN3_7_MAX = QWEN3_7_MAX
    QWEN3_7_PLUS = QWEN3_7_PLUS
    QWEN3_7_FLASH = QWEN3_7_FLASH
    QWEN3_6_PLUS = QWEN3_6_PLUS
    QWEN3_5_PLUS = QWEN3_5_PLUS
    QWEN_VL_MAX = QWEN_VL_MAX
    QWEN3_VL_PLUS = QWEN3_VL_PLUS
    QWEN3_VL_FLASH = QWEN3_VL_FLASH
