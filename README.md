# visionauto

[![PyPI version](https://img.shields.io/pypi/v/visionauto.svg)](https://pypi.org/project/visionauto/)
[![Python](https://img.shields.io/pypi/pyversions/visionauto.svg)](https://pypi.org/project/visionauto/)
[![License](https://img.shields.io/pypi/l/visionauto.svg)](https://github.com/wwwsctvcom/visionauto/blob/main/LICENSE)
[![Status](https://img.shields.io/pypi/status/visionauto.svg)](https://pypi.org/project/visionauto/)

uiautomator2 设备控制 + AI 视觉选择器。用 u2 做"手"（截图、点击坐标、手势、弹窗 watcher），用 VLM 做"眼"（定位元素）。用法对齐 u2：`d(text="你好").click()`，但定位走视觉，能识别自绘/Canvas/图标按钮等无障碍树拿不到的控件。

## 安装

```bash
pip install -e ".[dev]"          # dev 含 pytest
adb devices                       # 确认有一台设备在线
```

## 快速开始

```python
import visionauto as va

d = va.connect(api_key="sk-xxx", provider="qwen")   # 或纯走环境变量

d.app_start("com.tencent.mm")
d(text="微信").wait(timeout=15)

d(description="右上角的搜索按钮").click()             # 图标无文字 → 语义定位
d(description="搜索输入框").input("你好")
d(text="发送").click()
```

## 配置

优先级：传参 > 环境变量 > 默认值。所有字段通用，不按 provider 区分。

| 字段 | 环境变量 | 默认 | 说明 |
| --- | --- | --- | --- |
| `provider` | `VISIONAUTO_PROVIDER` | `glm` | `glm` / `qwen` / `openai` |
| `api_key` | `VISIONAUTO_API_KEY` | - | API key |
| `model` | `VISIONAUTO_MODEL` | provider 默认 | 模型名 |
| `base_url` | `VISIONAUTO_BASE_URL` | provider 默认 | OpenAI 兼容端点 |
| `temperature` | `VISIONAUTO_TEMPERATURE` | `0.0` | 不支持的模型自动省略 |
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

内置 provider：

| provider | 默认模型 | 默认端点 |
| --- | --- | --- |
| `glm` | `GLM-5V-Turbo` | 智谱 `open.bigmodel.cn` |
| `qwen` | `qwen3.7-max-2026-06-08` | 阿里 DashScope |
| `openai` | （需自备） | OpenAI 兼容任意端点 |

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

## Provider 与扩展模型

每个 provider 各自实现 `supports_temperature()`，对 thinking/reasoning 类模型（qwq、`*-thinking`、GLM-Z1、o1/o3 等）自动不传 `temperature`，普通模型传 `temperature=0`。

加一个新模型 provider：

```python
from visionauto.providers.base import OpenAICompatibleProvider
from visionauto.providers import register_provider

class MyProvider(OpenAICompatibleProvider):
    DEFAULT_BASE_URL = "https://api.example.com/v1/"
    DEFAULT_MODEL = "my-vl-model"
    def supports_temperature(self) -> bool:
        return "thinking" not in (self._model or "").lower()

register_provider("my", MyProvider)
# 然后 VISIONAUTO_PROVIDER=my
```

## 架构

```text
visionauto/
├── config.py            通用配置（api_key/model/base_url/阈值/超时/debug）
├── device.py            VisionDevice: 包 u2.Device + d(...) 工厂 + 截图缓存 + dump
├── selector.py          Selector: 懒执行链式 API（exists/click/wait/drag_to/swipe...）
├── located.py           Located: bbox + text
├── coords.py            [0,1] 规范坐标 → 设备像素，自适应 0-999/[0,1]/绝对像素
├── cache.py             截图+解析短 TTL 缓存
├── prompts.py           三套 prompt（统一 schema：clickable 节点 + bbox + OCR text）
├── utils.py             json-repair 解析
├── viz.py               标注绘图（trace 指令标签 / dump OCR 标签）
├── debug.py             DebugRecorder: 自动记录每次 AI 识别 + 动作时间线
├── exceptions.py        ElementNotFound 等
├── providers/           传输+鉴权层（OpenAI 兼容）
│   ├── base.py          OpenAICompatibleProvider + supports_temperature
│   ├── glm.py           GLM（智谱）
│   ├── qwen.py          Qwen（阿里 DashScope）
│   └── openai.py        通用 OpenAI 兼容
├── matching/            image 兜底：airtest OpenCV（template/multiscale/keypoint）
│   └── opencv.py
└── locator/             策略层
    ├── text.py          一次 VLM 取全部可点击控件+OCR 文字，客户端按模式过滤
    ├── description.py   语义定位：描述直接喂 AI
    └── image.py         VLM 优先，airtest OpenCV 兜底
```

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
VISIONAUTO_TEST_MODELS=qwen3.7-max-2026-06-08,qwen3.7-plus \
pytest -v -s tests/test_provider_vision.py
```
