"""Convenience model-name constants (optional — you can always pass a plain
string ``model="..."`` to ``VisionDevice``; these just save some typing).

Only models verified to accept image input are listed, because visionauto needs
multimodal models. Text-only variants (``mimo-v2.5-pro``, ``deepseek-v4-flash``,
``glm-4.6``, MiniMax M-series…) raise ImageNotSupportedError and are NOT here.
"""
from __future__ import annotations


class Models:
    # Kimi (Moonshot) — latest: k3
    KIMI_K3 = "kimi-k3"
    KIMI_K2_7_CODE = "kimi-k2.7-code"
    KIMI_K2_7_CODE_HIGHSPEED = "kimi-k2.7-code-highspeed"
    KIMI_K2_6 = "kimi-k2.6"
    KIMI_K2_5 = "kimi-k2.5"

    # MiMo (Xiaomi) — vision model
    MIMO_V2_5 = "mimo-v2.5"

    # GLM (Zhipu)
    GLM_5V_TURBO = "GLM-5V-Turbo"
    GLM_4_5V = "glm-4.5v"

    # DeepSeek — the vision variant
    DEEPSEEK_V4_FLASH_VISION_EXP = "deepseek-v4-flash-vision-exp"

    # Qwen (DashScope) — latest: qwen3.8-max (verified multimodal)
    QWEN3_8_MAX = "qwen3.8-max"
    QWEN3_7_MAX = "qwen3.7-max"
    QWEN3_7_PLUS = "qwen3.7-plus"
    QWEN3_7_FLASH = "qwen3.7-flash"
    QWEN3_6_PLUS = "qwen3.6-plus"
    QWEN3_5_PLUS = "qwen3.5-plus"
    QWEN_VL_MAX = "qwen-vl-max"
    QWEN3_VL_PLUS = "qwen3-vl-plus"
    QWEN3_VL_FLASH = "qwen3-vl-flash"
