# visionauto

[![PyPI version](https://img.shields.io/pypi/v/visionauto.svg)](https://pypi.org/project/visionauto/)
[![Python](https://img.shields.io/pypi/pyversions/visionauto.svg)](https://pypi.org/project/visionauto/)
[![License](https://img.shields.io/pypi/l/visionauto.svg)](https://github.com/wwwsctvcom/visionauto/blob/main/LICENSE)
[![Status](https://img.shields.io/pypi/status/visionauto.svg)](https://pypi.org/project/visionauto/)

uiautomator2 设备控制 + AI 视觉选择器。用 u2 做"手"（截图、点击坐标、手势、弹窗 watcher），用 VLM 做"眼"（定位元素）。用法对齐 u2：`d(text="你好").click()`，但定位走视觉，能识别自绘/Canvas/图标按钮等无障碍树拿不到的控件。

## 安装

```bash
pip install visionauto            # 从 PyPI 安装
# 或开发模式：pip install -e ".[dev]"
adb devices                       # 确认有一台设备在线
```

## 快速开始

一个入口 `VisionDevice(sn=, base_url=, api_key=, model=)`，无需单独 connect。**任何 OpenAI 兼容端点 + 多模态模型填进去就能用**，框架内部处理一切封装：

```python
from visionauto import VisionDevice

d = VisionDevice(
    sn="emulator-5554",                        # USB 序列号 / WiFi adb "192.168.1.10:5555"
    base_url="https://api.deepseek.com/v1",    # 任意 OpenAI 兼容端点
    api_key="sk-xxx",
    model="deepseek-v4-flash-vision-exp",      # 任意多模态(VL)模型名
)

d.app_start("com.tencent.mm")
d(text="微信").wait(timeout=15)

d(description="右上角的搜索按钮").click()             # 图标无文字 -> 语义定位
d(description="搜索输入框").input("你好")
d(text="发送").click()
```

不想记 base_url？用**预设名**（等价于帮你填 base_url + 默认视觉模型，均可覆盖）：

```python
d = VisionDevice(sn, provider="qwen", api_key="sk-xxx")            # 阿里 DashScope
d = VisionDevice(sn, provider="deepseek", api_key="sk-xxx")        # DeepSeek
d = VisionDevice(sn, provider="glm", api_key="xxx.yyy")            # 智谱
d = VisionDevice(sn, provider="kimi", api_key="sk-xxx")            # Moonshot 国际站
d = VisionDevice(sn, provider="kimi-cn", api_key="sk-xxx")         # Moonshot 国内站
d = VisionDevice(sn, provider="mimo", api_key="sk-xxx")            # 小米
d = VisionDevice(sn, provider="openrouter", api_key="sk-or-...",
                 model="moonshotai/kimi-k3")                       # 一把 key 用 100+ 模型
```

全部省略时走环境变量：`VISIONAUTO_API_KEY / _MODEL / _BASE_URL`（可选 `VISIONAUTO_PROVIDER` 指定预设名）。

### 错误反馈（不用猜）

模型调用失败时抛**具体的异常**，直接告诉你该改什么：

| 异常 | 场景 |
| --- | --- |
| `ProviderConfigError` | 没给 api_key / model |
| `ProviderAuthError` | api_key 无效（401/403），或 key 与平台不匹配（如 .cn/.ai 不互通） |
| `ModelNotFoundError` | 模型名拼错 / 该平台无此模型（404 或 400 "Unsupported model"） |
| `ImageNotSupportedError` | 该模型是**纯文本模型**（如 `deepseek-v4-flash`、`mimo-v2.5-pro`、MiniMax M 系列），不能用于视觉定位 |
| `InsufficientBalanceError` | 账户余额不足/欠费（402 或 "insufficient balance"） |
| `ProviderRateLimitError` | 触发限流（429） |
| `ProviderConnectionError` | 连不上 base_url（网络/DNS/端点写错） |

```python
from visionauto import VisionDevice, ImageNotSupportedError, ProviderAuthError

try:
    d = VisionDevice(sn="emulator-5554", base_url="...", api_key="...", model="...")
    d(text="设置").click()
except ImageNotSupportedError as e:
    print("换个多模态模型：", e)
except ProviderAuthError as e:
    print("检查 api_key：", e)
```

## 配置（两层分离）

- **模型连接（传参即用）**：`base_url / api_key / model`（或预设名 `provider=`），框架内部统一封装：temperature 怪癖按模型名自动处理（thinking/reasoner 类不传、kimi-k2.7 系列强制 1.0），端点拒绝 `response_format`/`temperature` 时自动降级重试。也可用环境变量 `VISIONAUTO_API_KEY / _MODEL / _BASE_URL / _PROVIDER`。
- **`Config`**（`visionauto/config.py`）--框架行为层：`implicit_wait / resolve_retries / cache_ttl / default_timeout / opencv_* / normalize_text / debug / fail_dir`。

优先级：传参 > 环境变量 > 默认值。**不需要任何配置文件**。

模型连接参数（`VisionDevice` 构造参数 / 环境变量）：

| 参数 | 环境变量 | 说明 |
| --- | --- | --- |
| `base_url` | `VISIONAUTO_BASE_URL` | OpenAI 兼容端点；用预设名时可省 |
| `api_key` | `VISIONAUTO_API_KEY` | 平台 API key（必填） |
| `model` | `VISIONAUTO_MODEL` | 模型名，需为多模态(VL)模型（必填，预设名有默认值） |
| `provider` | `VISIONAUTO_PROVIDER` | 预设名（可选便利） |
| `timeout` | `VISIONAUTO_TIMEOUT` | 单次请求超时秒数，默认 120 |

框架行为 Config 字段：

| 字段 | 环境变量 | 默认 | 说明 |
| --- | --- | --- | --- |
| `opencv_threshold` | `VISIONAUTO_OPENCV_THRESHOLD` | `0.8` | image 兜底置信度 |
| `opencv_method` | `VISIONAUTO_OPENCV_METHOD` | `auto` | `auto/template/multiscale/keypoint` |
| `opencv_rgb` | `VISIONAUTO_OPENCV_RGB` | `True` | OpenCV 兜底 RGB 二次校验 |
| `cache_ttl` | `VISIONAUTO_CACHE_TTL` | `2.0` | 截图复用秒数 |
| `default_timeout` | `VISIONAUTO_DEFAULT_TIMEOUT` | `10.0` | `wait()` 默认超时 |
| `normalize_text` | `VISIONAUTO_NORMALIZE_TEXT` | `True` | 文字匹配前折叠空白 |
| `implicit_wait` | `VISIONAUTO_IMPLICIT_WAIT` | `0.0` | 隐式等待秒数（exists/动作自动轮询，0=关） |
| `resolve_retries` | `VISIONAUTO_RESOLVE_RETRIES` | `2` | AI 空结果/异常时换帧重试次数 |
| `fail_dir` | `VISIONAUTO_FAIL_DIR` | `out/fail` | 断言失败截图目录 |
| `debug` | `VISIONAUTO_DEBUG` | `False` | 调试追踪开关 |
| `debug_dir` | `VISIONAUTO_DEBUG_DIR` | `out/trace` | 追踪输出目录 |

内置预设名（只是 base_url + 默认视觉模型的速记，完全可不用）：

| 预设名 | 默认模型 | 端点 |
| --- | --- | --- |
| `glm` | `GLM-5V-Turbo` | 智谱 `open.bigmodel.cn` |
| `qwen` | `qwen3.8-max` | 阿里 DashScope |
| `kimi` | `kimi-k3` | Moonshot 国际站 `api.moonshot.ai` |
| `kimi-cn` | `kimi-k3` | Moonshot 国内站 `api.moonshot.cn`（与 .ai key 不互通） |
| `mimo` | `mimo-v2.5` | 小米 `api.xiaomimimo.com` |
| `deepseek` | `deepseek-v4-flash-vision-exp` | DeepSeek `api.deepseek.com` |
| `openrouter` | （需指定，如 `qwen/qwen3.7-max`） | 聚合端点，一把 key 覆盖 100+ 模型 |
| `openai` | （需指定） | OpenAI 官方端点 |

模型名直接写字符串即可；也可用 `Models` 常量速记（`from visionauto import Models`）：`Models.KIMI_K3`、`Models.MIMO_V2_5`、`Models.GLM_5V_TURBO`、`Models.QWEN3_7_MAX`、`Models.DEEPSEEK_V4_FLASH_VISION_EXP` 等。

**注意（已实测）**：
- 必须使用**支持图像输入**的多模态模型；纯文本模型（如 `mimo-v2.5-pro`、`deepseek-v4-flash`、MiniMax M 系列、`glm-4.6`）会抛 `ImageNotSupportedError`。
- Kimi 国际站（`.ai`）与国内站（`.cn`）key 不互通；国内站没有 `kimi-k2.7` 常规 ID，请用 `kimi-k2.7-code` / `kimi-k2.7-code-highspeed`。
- `openrouter` 的 `model` 用"上游/模型"格式（如 `moonshotai/kimi-k3`、`xiaomi/mimo-v2.5`），视觉支持取决于具体模型（选 VLM）。

## 选择器

`d(**query)` 返回 `Selector`，懒执行。定位方式由传入的键决定：

| 键 | 定位方式 | 示例 |
| --- | --- | --- |
| `text` / `textContains` / `textStartsWith` / `textMatches` | AI 识别所有可点击控件 + OCR 文字，客户端按模式过滤 | `d(text="设置")`、`d(textMatches=r"设置.*")` |
| `description` | 语义定位：把自然语言描述直接喂 AI 选目标 | `d(description="左上角的红色图标")` |
| `image` | VLM 优先；找不到时 airtest OpenCV（template/multiscale/keypoint）兜底 | `d(image="./btn.png")` |
| `index` | 在匹配结果里取第 n 个（从 0） | `d(text="删除", index=2)` |

文字匹配默认折叠空白（`normalize_text=True`），"设置 中心" 仍能匹配 "设置中心"，规避 AI 拆字。

## Selector 方法

查询类：

| 方法 | 说明 |
| --- | --- |
| `exists()` | 是否存在 |
| `wait(timeout=None, interval=0.5)` | 轮询等待出现，返回是否出现 |
| `wait_gone(timeout=None)` | 轮询等待消失 |
| `count()` | 匹配数量 |
| `all()` | 返回全部匹配 `Located` |
| `get_text()` | 元素文字（text 必有；description/image 命中时 AI 会 OCR 回填） |
| `center()` | 中心点 `(x, y)`（绝对像素） |
| `bounds()` | `(x1, y1, x2, y2)` 绝对像素 |

动作类（任意 locator 通用，找不到抛 `ElementNotFound`）：

| 方法 | 说明 |
| --- | --- |
| `click()` | 点击中心 |
| `long_click(duration=None)` | 长按 |
| `click_exists(timeout=None)` | 出现就点，返回是否点了 |
| `input(text, clear=False)` | 点击聚焦后输入文字 |
| `drag_to(**query, duration=0.5)` | 拖到另一个元素（同张截图取两点坐标） |
| `swipe(direction, scale=0.9, duration=0.5)` | 从该元素出发按方向滑，u2 `swipe_ext` 风格 |
| `scroll_to(direction="up", max_swipes=10)` | 整屏滚动直到该元素出现，返回 self 可链式 `.click()` |

```python
d(text="A").drag_to(text="B")              # 注意：目标是 kwargs，不是 d(...)
d(text="搜索框").input("visionauto", clear=True)
d(text="列表项").swipe("left", scale=0.5)   # left/right/up/down
```

## 弹窗处理

直接用 uiautomator2 的 `watcher`（基于无障碍树，即时且不耗 AI）。`d.watcher` 已透传到 u2：

```python
for txt in ["允许", "知道了", "暂不", "关闭"]:
    d.watcher.when(txt).click()   # 出现即点
d.watcher.start(2.0)              # 后台每 2s 检查一次
try:
    d.app_start("com.tencent.mm")  # 主流程；弹窗被自动处理
finally:
    d.watcher.stop()
    d.watcher.reset()
```

标准系统弹窗（有 accessibility text）用 watcher 最稳；自绘/无障碍缺失的弹窗再用 `d(description="...").click()` 视觉处理。完整示例见 `examples/popup_watcher.py`。

## 稳定性与断言

**隐式等待**——开了之后 `exists()` 和所有动作自动轮询到超时，不必每步手动 `wait()`：

```python
d.implicitly_wait(5)              # 或 config(implicit_wait=5)
d(text="提交").click()            # 最多等 5s，出现才点
```

**AI 解析重试**——VLM 这一帧空/异常时自动换帧重试（`resolve_retries` 默认 2），对抗 AI 抽风导致的假阴性，用户无感。

**滚动定位**——长列表里找目标：

```python
d(text="关于手机").scroll_to().click()              # 向上滚直到出现再点
d(text="第100条").scroll_to(direction="up", max_swipes=20).click()
```

**断言助手**（失败自动存截图到 `out/fail/`，CI 排查利器）：

```python
d.assert_exists(text="首页")
d.assert_gone(text="加载中")
d.assert_text("设置", text="设置")          # 元素文字 == 预期
d.assert_count(3, textContains="结果")      # 匹配数 == 3
```

## 直接使用 uiautomator2 API

`d` 透传底层 u2 设备的全部 API，无需 `.u2` 即可调用：

```python
d.app_start("com.android.settings")
d.press("back")                   # home/back/enter/volume_up...
d.swipe(100, 800, 100, 200)
d.window_size()
d.screen_off()
d.app_stop("com.tencent.mm")
```

视觉选择器走 `d(text=...)`（`__call__`），u2 API 走属性访问（`__getattr__` 委托），两者互不冲突。需要显式拿到原始 u2 设备时用 `d.u2`。

## 调试可视化

开启 debug 后**每次 AI 识别自动落盘**，跑完看 `out/trace/` 回放全流程，定位是哪一步识别错了——无需手动调任何 API：

```python
d.start_debug("out/trace")        # 或 config(debug=True)，或 VISIONAUTO_DEBUG=1
d(text="设置").click()
d(description="返回按钮").click()
d.stop_debug()
```

`out/trace/` 产物：

- `trace.log` —— 完整时间线：每步的 query / 定位类型 / 命中节点数 / 是否缓存命中 / 执行的动作。
- `NNNN_<kind>.png` —— 每次识别的标注截图：**被点击的框用绿色粗框 + 写你的指令**（`description='...'`/`text='...'`），其余匹配框灰色标序号；不写 OCR 文字，方便核对"prompt 是否点对了"。

临时看整屏识别结果（视觉版 `dump_hierarchy`）：

```python
nodes = d.dump("out/dump.png")    # 返回所有 clickable 节点并保存标注图（带 OCR 文字）
```

## 坐标约定

VLM 返回 `[x1,y1,x2,y2]`，GLM-V / Qwen-VL 通常归一化到 `0-999`。`coords.py` 自适应量纲并换算到设备像素：

- `max ≤ 1.0` → 视为 `[0,1]`
- `max ≤ norm_scale`（默认 1000，provider 可在 `COORD_NORM_SCALE` 声明）→ 按 `norm_scale` 归一
- `max > norm_scale` → 视为绝对像素，按截图实际尺寸还原

内部统一转成 `[0,1]` 规范坐标，再 `device_x = vx * window_width`。返回的 JSON 先经 `json-repair` 修复（容忍尾逗号、单引号、代码围栏、夹带说明文字）再解析。

## 模型兼容性（框架内部自动处理）

- **temperature 怪癖**按模型名自动解析：thinking/reasoner 类（qwq、`*-thinking`、GLM-Z1、o1/o3、deepseek-r1）不传 `temperature`；`kimi-k2.5/2.6` 服务端管理不传；`kimi-k2.7` 系列强制 `temperature=1.0`；其余默认 `0`。
- **json mode**：默认带 `response_format=json_object`，端点拒绝时自动去掉重试。
- **坐标系量纲**：`coords.py` 自适应 `[0,1]` / `0-999` / 绝对像素。

加一个新预设（只是速记，不写代码也能用）：

```python
from visionauto.providers import register_provider

register_provider("my", base_url="https://api.example.com/v1/", model="my-vl-model")
# 之后：VisionDevice(sn, provider="my", api_key="sk-...")
```

## 架构

```text
visionauto/
├── __init__.py          VisionDevice 单入口 + Models + 全部异常导出
├── config.py            【框架行为】implicit_wait/resolve_retries/cache_ttl/opencv/debug/...
├── device.py            VisionDevice(sn=, base_url/api_key/model 或 provider=, config=)
├── selector.py          Selector: 懒执行链式 API（exists/click/wait/scroll_to/drag_to...）
├── located.py / coords.py / cache.py / utils.py / viz.py / debug.py
├── exceptions.py        异常体系：ElementNotFound + Provider 系列（Auth/NotFound/NoImage/...）
├── matching/            image 兜底：airtest OpenCV（template/multiscale/keypoint）
├── locator/             策略层（text/description/image，prompt 来自 providers.prompts）
└── providers/           【统一传输层：一个 OpenAICompatibleProvider 走天下】
    ├── __init__.py      get_provider(预设名) / get_provider_from_env / register_provider
    ├── presets.py       预设名 -> {base_url, 默认视觉模型}
    ├── config.py        ProviderConfig: api_key/model/base_url/temperature/timeout
    ├── models.py        Models 常量速记（只收录多模态模型）
    ├── prompts.py       三套 prompt（text/description/image）
    └── base.py          OpenAICompatibleProvider：模型怪癖 + 参数自适应降级 + 异常映射
```

设计要点：**用户只需 base_url + api_key + model**；预设名只是速记。所有模型怪癖（temperature/response_format）与失败场景（key 无效/模型不存在/不支持图片/欠费/限流/连不上）都在 `base.py` 统一封装并映射为具体异常；框架行为（Config）与模型连接完全解耦。

## 示例

`examples/` 下：

- `wechat_search.py` —— 打开微信 → 搜索 → 进聊天 → 发消息（完整视觉流程）
- `search_download.py` —— 主页搜索"微信" → 判断第一个结果右侧"下载/打开"按钮 → 点击（含条件分支）
- `popup_watcher.py` —— u2 watcher 自动处理权限/升级弹窗
- `_config.py` —— 示例统一的 provider/model/api_key 配置（默认 qwen，env 可覆盖）

运行：

```bash
python examples/wechat_search.py
python examples/search_download.py
python examples/popup_watcher.py
```

## 测试

```bash
# 用 adb 真机截图跑三个核心 prompt，识别结果画框存到 out/
VISIONAUTO_API_KEY=... VISIONAUTO_PROVIDER=glm pytest -v -s tests/test_core_prompts.py

# 测试多个模型的图像问答能力
VISIONAUTO_PROVIDER=qwen VISIONAUTO_API_KEY=sk-... \
VISIONAUTO_TEST_IMAGE=./x.png \
VISIONAUTO_TEST_MODELS=qwen3.8-max,qwen3.7-plus \
pytest -v -s tests/test_provider_vision.py
```
