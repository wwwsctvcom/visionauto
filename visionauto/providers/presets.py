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
    # Moonshot has two separate platforms with non-interchangeable keys,
    # hence two preset names.
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
    # OpenRouter: one key reaches 100+ models; model uses the
    # "upstream/model" format, e.g. "qwen/qwen3.7-max", "moonshotai/kimi-k3",
    # "xiaomi/mimo-v2.5".
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": None,  # model must be given explicitly
    },
    "openai": {
        "base_url": None,  # use the openai SDK default endpoint
        "model": None,     # model must be given explicitly
    },
}
