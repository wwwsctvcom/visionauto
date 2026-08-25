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

One entry point — `VisionDevice(sn=, base_url=, api_key=, model=)`. Any
OpenAI-compatible endpoint + any multimodal (VL) model works; the framework
handles all the wrapping:

```python
from visionauto import VisionDevice

d = VisionDevice(
    sn="emulator-5554",                        # USB serial / WiFi adb "192.168.1.10:5555"
    base_url="https://api.deepseek.com/v1",
    api_key="sk-xxx",
    model="deepseek-v4-flash-vision-exp",
)

d.app_start("com.tencent.mm")
d(text="微信").wait(timeout=15)
d(description="右上角的搜索按钮").click()     # icon without text -> semantic
d(description="搜索输入框").input("你好")
d(text="发送").click()
```

Or use a **preset name** to skip remembering base_url (model is overridable):

```python
d = VisionDevice(sn, provider="qwen", api_key="sk-xxx")
d = VisionDevice(sn, provider="deepseek", api_key="sk-xxx")
d = VisionDevice(sn, provider="glm", api_key="xxx.yyy")
d = VisionDevice(sn, provider="kimi", api_key="sk-xxx")        # Moonshot .ai
d = VisionDevice(sn, provider="kimi-cn", api_key="sk-xxx")     # Moonshot .cn
d = VisionDevice(sn, provider="mimo", api_key="sk-xxx")
d = VisionDevice(sn, provider="openrouter", api_key="sk-or-...",
                 model="moonshotai/kimi-k3")
```

If all connection args are omitted, env vars are used:
`VISIONAUTO_API_KEY / _MODEL / _BASE_URL` (optional `VISIONAUTO_PROVIDER`).

## Supported APIs (presets)

| Preset | Default model | Endpoint |
| --- | --- | --- |
| `glm` | `GLM-5V-Turbo` | Zhipu `open.bigmodel.cn` |
| `qwen` | `qwen3.8-max` | Aliyun DashScope |
| `kimi` | `kimi-k3` | Moonshot international `api.moonshot.ai` |
| `kimi-cn` | `kimi-k3` | Moonshot China `api.moonshot.cn` (keys not interchangeable with .ai) |
| `mimo` | `mimo-v2.5` | Xiaomi `api.xiaomimimo.com` |
| `deepseek` | `deepseek-v4-flash-vision-exp` | DeepSeek `api.deepseek.com` |
| `openrouter` | (required, e.g. `qwen/qwen3.8-max`) | Aggregator, one key for 100+ models |
| `openai` | (required) | OpenAI official endpoint |

Model names are plain strings; `Models` constants (`from visionauto import Models`)
are optional shortcuts: `Models.KIMI_K3`, `Models.MIMO_V2_5`, `Models.GLM_5V_TURBO`,
`Models.QWEN3_8_MAX`, `Models.DEEPSEEK_V4_FLASH_VISION_EXP`, …

**Important (verified)**:
- Use a **multimodal** model. Text-only models (`mimo-v2.5-pro`,
  `deepseek-v4-flash`, MiniMax M-series, `glm-4.6`) raise
  `ImageNotSupportedError`.
- `openrouter` model uses the "upstream/model" format
  (`moonshotai/kimi-k3`, `xiaomi/mimo-v2.5`); vision support depends on the model.

## Errors (no guessing)

Failed model calls raise a specific exception telling you what to fix:

| Exception | When |
| --- | --- |
| `ProviderConfigError` | missing api_key / model |
| `ProviderAuthError` | invalid api_key (401/403), or key/platform mismatch (.cn/.ai) |
| `ModelNotFoundError` | misspelled/unknown model, or not enabled (404 / 400) |
| `ImageNotSupportedError` | the model is text-only and cannot do vision locating |
| `InsufficientBalanceError` | account balance too low / suspended (402) |
| `ProviderRateLimitError` | rate limited (429) |
| `ProviderConnectionError` | cannot reach base_url (network/DNS/wrong endpoint) |

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
d = VisionDevice(sn, provider="qwen", api_key="sk-xxx",
                 config=Config(implicit_wait=5))
d.implicitly_wait(5)        # or at runtime
```

- `implicit_wait`: `exists()`/actions auto-poll up to N seconds.
- `resolve_retries` (default 2): re-screenshot + re-ask when the VLM returns
  empty/flaky, to avoid false not-found.
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

## Extend: add a preset

Register a named preset (just base_url + default vision model; no code in the
transport layer needed):

```python
from visionauto.providers import register_provider

register_provider("my", base_url="https://api.example.com/v1/", model="my-vl-model")
# then: VisionDevice(sn, provider="my", api_key="sk-...")
```

## Examples

`examples/wechat_search.py`, `examples/search_download.py`,
`examples/popup_watcher.py` — run with `--provider --api-key --base-url --model
--sn` flags, env vars, or edit `examples/_config.py` (defaults: qwen).

```bash
python examples/wechat_search.py --provider qwen --api-key sk-xxx
```
