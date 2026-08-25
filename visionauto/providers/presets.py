"""Known provider presets: name -> {"base_url", "model"}.

Presets are pure convenience so users don't have to remember base_urls and a
good default vision model. You can always bypass them entirely by passing
``base_url``/``api_key``/``model`` straight to ``VisionDevice``.

Note: the default model for each preset is a *multimodal* (vision) model —
visionauto needs image input. See visionauto/providers/models.py.
"""
from __future__ import annotations

PROVIDER_PRESETS: dict[str, dict[str, str | None]] = {
    "glm": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "model": "GLM-5V-Turbo",
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen3.8-max",
    },
    # Moonshot 国际站与国内站是两个平台、key 不互通，给两个预设名。
    "kimi": {
        "base_url": "https://api.moonshot.ai/v1",
        "model": "kimi-k3",
    },
    "kimi-cn": {
        "base_url": "https://api.moonshot.cn/v1",
        "model": "kimi-k3",
    },
    "mimo": {
        "base_url": "https://api.xiaomimimo.com/v1",
        "model": "mimo-v2.5",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-v4-flash-vision-exp",
    },
    # OpenRouter：一把 key 覆盖 100+ 模型，model 用 "上游/模型" 格式，
    # 如 "qwen/qwen3.7-max"、"moonshotai/kimi-k3"、"xiaomi/mimo-v2.5"。
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": None,  # 必须显式给 model
    },
    "openai": {
        "base_url": None,  # 走 openai SDK 默认端点
        "model": None,     # 必须显式给 model
    },
}
