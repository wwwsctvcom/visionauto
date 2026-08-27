# visionauto

uiautomator2 device control + AI vision selectors. Use u2 as the "hands"
(screenshots, clicks, gestures, popup watchers) and a VLM as the "eyes"
(element locating). The API mirrors u2 — `d(text="你好").click()` — but
locating is visual, so it can target controls the accessibility tree cannot
see (custom-drawn/Canvas/icon buttons).

## Install

```bash
pip install visionauto
adb devices   # a device must be online
```

## Quick start

One entry point — `VisionDevice(sn=, base_url=, api_key=, model=)`. Three
plain values you already know; the framework handles all the wrapping:

```python
from visionauto import VisionDevice

d = VisionDevice(
    sn="emulator-5554",                        # USB serial / WiFi adb "192.168.1.10:5555"
    base_url="https://api.deepseek.com/v1",    # any model endpoint (see table below)
    api_key="sk-xxx",
    model="deepseek-v4-flash-vision-exp",      # any multimodal model name
)

d.app_start("com.tencent.mm")
d(text="微信").wait(timeout=15)
d(description="右上角的搜索按钮").click()     # icon without text -> semantic
d(description="搜索输入框").input("你好")
d(text="发送").click()
```

Two optional kwargs extend coverage when needed (omit them entirely for the
common case):

```python
from visionauto import VisionDevice, ApiFormat, Sampling, Model

d = VisionDevice(
    sn="emulator-5554",
    base_url="https://api.anthropic.com",
    api_key="sk-ant-xxx",
    model="claude-sonnet-4-5",
    api_format=ApiFormat.MESSAGES,        # default CHAT; MESSAGES/RESPONSES for
                                         # Anthropic / OpenAI native protocols
    sampling=Sampling(max_tokens=4096),   # defaults are sane; None = omit
)
# Model presets are plain strings with IDE completion:
d = VisionDevice(sn, base_url="https://dashscope.../v1", api_key="sk-xxx",
                 model=Model.QWEN3_8_MAX)     # Model.QWEN3_8_MAX == "qwen3.8-max"
```

Omitted connection args fall back to env vars:
`VISIONAUTO_API_KEY / _BASE_URL / _MODEL / _API_FORMAT`.

## Endpoint reference (verified)

| Provider | base_url | Verified vision models |
| --- | --- | --- |
| Aliyun DashScope | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen3.8-max`, `qwen3.7-plus/flash`, `qwen3-vl-plus/flash`, … |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-v4-flash-vision-exp` |
| Zhipu | `https://open.bigmodel.cn/api/paas/v4/` | `GLM-5V-Turbo`, `glm-4.5v`, `glm-4v-plus/flash` |
| Moonshot (intl) | `https://api.moonshot.ai/v1` | `kimi-k3`, `kimi-k2.5/2.6`, `kimi-k2.7-code` |
| Moonshot (CN) | `https://api.moonshot.cn/v1` | same models; keys NOT interchangeable with .ai |
| Xiaomi | `https://api.xiaomimimo.com/v1` | `mimo-v2.5` |
| OpenRouter | `https://openrouter.ai/api/v1` | `moonshotai/kimi-k3`, `qwen/qwen3.8-max`, `xiaomi/mimo-v2.5`, … (one key, 100+ models) |
| OpenAI | (SDK default) | `ApiFormat.CHAT` or `ApiFormat.RESPONSES` |
| Anthropic | `https://api.anthropic.com` | `ApiFormat.MESSAGES` (needs `pip install 'visionauto[anthropic]'`) |
| Any OpenAI-compatible | your endpoint | vLLM, Ollama, LiteLLM/new-api gateways, … |

**Important (verified)**:
- Use a **multimodal** model. Text-only models (`mimo-v2.5-pro`,
  `deepseek-v4-flash`, MiniMax M-series, `glm-4.6`) raise
  `ImageNotSupportedError`.
- Sampling quirks are absorbed by the framework: rejected params are
  auto-dropped with one retry, `max_tokens` is auto-renamed to
  `max_completion_tokens` where required, and truncated output raises
  `OutputTruncatedError` telling you to raise `sampling.max_tokens`.
- `ApiFormat.MESSAGES` appends `/v1/messages` to base_url, so the Anthropic
  official endpoint is `https://api.anthropic.com` (no `/v1` suffix) and
  OpenRouter's is `https://openrouter.ai/api`. Thinking models
  (`deepseek-v4-flash-vision-exp` etc.) need a generous `max_tokens`.

## Errors (no guessing)

Failed model calls raise a specific exception telling you what to fix
(propagated directly out of any selector call - never masked as "not found"):

| Exception | When |
| --- | --- |
| `ProviderConfigError` | missing api_key / model |
| `ProviderAuthError` | invalid api_key (401/403), or key/platform mismatch (.cn/.ai) |
| `ModelNotFoundError` | misspelled/unknown model, or not enabled (404 / 400) |
| `ImageNotSupportedError` | the model is text-only and cannot do vision locating |
| `InsufficientBalanceError` | account balance too low / suspended (402) |
| `ProviderRateLimitError` | rate limited (429) |
| `ProviderConnectionError` | cannot reach base_url (network/DNS/wrong endpoint) |
| `OutputTruncatedError` | output cut off by max_tokens - raise `sampling.max_tokens` |

## Selectors

`d(**query)` returns a lazy `Selector`. The key you pass picks the locating
method:

| Key | Method | Example |
| --- | --- | --- |
| `text` / `textContains` / `textStartsWith` / `textMatches` | AI lists all clickable controls + OCR text, filter client-side | `d(text="设置")`, `d(textMatches=r"设置.*")` |
| `description` | natural-language semantic locating | `d(description="左上角的红色图标")` |
| `image` | VLM first, airtest/OpenCV (template/multiscale/keypoint) fallback | `d(image="./btn.png")` |
| `index` | pick the n-th match (0-based) | `d(text="删除", index=2)` |

Text matching collapses whitespace by default (`normalize_text=True`), so
"设置 中心" still matches "设置中心" (AI sometimes splits labels).

### Selector methods

Query: `exists()`, `wait(timeout=10)`, `wait_gone(timeout=10)`, `count()`,
`all()`, `get_text()`, `center()`, `bounds()`.

Action (raise `ElementNotFound` if absent): `click()`, `long_click()`,
`click_exists()`, `input(text, clear=False)`, `drag_to(**query)`,
`swipe(direction, scale=0.9)`, `scroll_to(direction="up", max_swipes=10)`.

```python
d(text="A").drag_to(text="B")
d(text="搜索框").input("visionauto", clear=True)
d(text="列表项").swipe("left", scale=0.5)
d(text="关于手机").scroll_to().click()
```

## Framework behavior (optional Config)

Set waits/retries/debug via `Config(...)` or env vars
(`VISIONAUTO_IMPLICIT_WAIT`, `VISIONAUTO_RESOLVE_RETRIES`,
`VISIONAUTO_CACHE_TTL`, `VISIONAUTO_DEBUG`, …). No config file required.

```python
d = VisionDevice(sn, base_url="https://dashscope.../v1", api_key="sk-xxx",
                 model="qwen3.8-max", config=Config(implicit_wait=5))
d.implicitly_wait(5)        # or at runtime
```

- `implicit_wait`: `exists()`/actions auto-poll up to N seconds.
- `resolve_retries` (default 2): re-screenshot + re-ask when the VLM returns
  empty/flaky, to avoid false not-found.
- `wait_stable(timeout, stable_frames=2)`: wait until consecutive screenshots
  stop changing (loading/animation finished) before locating - avoids acting
  on a half-rendered page.
- `assert_exists` / `assert_gone` / `assert_text` / `assert_count`: assertions
  that auto-save a screenshot to `fail_dir` (`out/fail/`) on failure.
- `debug=True` / `start_debug()`: every AI resolution is saved to `debug_dir`
  (`out/trace/`) with annotated screenshots + `trace.log` for replay.
- `d.dump("out/dump.png")`: visual `dump_hierarchy` - all clickable nodes +
  annotated image.

## Popups

Use uiautomator2's watcher directly (`d.watcher` is passthrough to u2),
fast and no AI cost. See `examples/popup_watcher.py`.

```python
for txt in ["允许", "知道了", "暂不", "关闭"]:
    d.watcher.when(txt).click()
d.watcher.start(2.0)
try:
    d.app_start("com.tencent.mm")
finally:
    d.watcher.stop(); d.watcher.reset()
```

## uiautomator2 passthrough

`d` delegates any attribute it does not define to the underlying u2 device, so
the full u2 API works directly: `d.app_start`, `d.press("back")`,
`d.swipe(x1,y1,x2,y2)`, `d.window_size()`, `d.screen_off()`, … Visual
selectors go through `__call__`; u2 API goes through attribute access — they
never conflict. Use `d.u2` for explicit access.

## Coordinates

VLM returns `[x1,y1,x2,y2]`; GLM-V / Qwen-VL usually normalize to 0-999.
`coords.py` auto-detects the magnitude and maps to device pixels:

- `max <= 1.0` → treated as `[0,1]`
- `max <= norm_scale` (default 1000) → normalized by `norm_scale`
- `max > norm_scale` → absolute pixels, divided by the screenshot size

Internally everything becomes `[0,1]`, then `device_x = vx * window_width`.
Returned JSON is repaired via `json-repair` (tolerates trailing commas, single
quotes, code fences, surrounding prose) before parsing.

## Extend: any OpenAI-compatible endpoint

No registration needed — any endpoint speaking Chat Completions works by
just passing its base_url + a multimodal model name (vLLM, Ollama, LiteLLM
gateways, private deployments, ...). For the Anthropic Messages / OpenAI
Responses wire protocols, pass `api_format=ApiFormat.MESSAGES / RESPONSES`.

## Examples

`examples/wechat_search.py`, `examples/search_download.py`,
`examples/popup_watcher.py` — run with `--base-url --api-key --model
--sn` flags, env vars, or edit `examples/_config.py` (defaults: DashScope
qwen3.8-max).

```bash
python examples/wechat_search.py --base-url https://api.deepseek.com/v1 \
    --api-key sk-xxx --model deepseek-v4-flash-vision-exp
```
