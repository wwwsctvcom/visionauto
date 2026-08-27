"""Offline unit tests: no device, no API key, no network.

Covers the selector retry/caching logic and the page-stability hashing with
a fake device + fake provider, so CI can run the framework's core logic.

Run: pytest -v tests/test_offline.py
"""
from __future__ import annotations

import io
import json

import pytest

from visionauto import Config
from visionauto.cache import TTLCache
from visionauto.debug import DebugRecorder
from visionauto.device import _ahash, _wait_frames_stable
from visionauto.exceptions import ImageNotSupportedError, ProviderAuthError
from visionauto.selector import Selector


def _png(mark: bool = False) -> bytes:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (720, 1280), (240, 240, 240))
    if mark:
        ImageDraw.Draw(img).rectangle([100, 100, 600, 400], fill=(200, 30, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


NODES_JSON = json.dumps({"nodes": [
    {"bbox": [80, 90, 920, 160], "text": "发送 Send"},
    {"bbox": [80, 190, 920, 260], "text": "保存 Save"},
    {"bbox": [80, 300, 920, 380], "text": "取消 Cancel"},
]}, ensure_ascii=False)


class FakeProvider:
    norm_scale = 1000.0

    def __init__(self, reply: str | None = None, error: Exception | None = None):
        self.reply = reply if reply is not None else NODES_JSON
        self.error = error
        self.calls = 0

    def chat(self, images, prompt, *, json_mode=True):
        self.calls += 1
        if self.error:
            raise self.error
        return self.reply


class FakeDevice:
    """Minimum surface the Selector needs; serves a static (or advancing) frame."""

    def __init__(self, provider, frames: list[bytes] | None = None):
        self._config = Config()
        self._provider = provider
        self._cache = TTLCache(60.0)
        self._debug = DebugRecorder("out/trace", enabled=False)
        self._frames = frames or [_png()]
        self._i = 0

    def _screenshot(self, force: bool = False):
        if force:
            self._i = min(self._i + 1, len(self._frames) - 1)
        return self._frames[self._i], (720, 1280)


class CyclingDevice(FakeDevice):
    """Never settles: every forced screenshot flips to the other frame."""

    def _screenshot(self, force: bool = False):
        if force:
            self._i = (self._i + 1) % len(self._frames)
        return self._frames[self._i], (720, 1280)


# -- P0-2: one AI call per frame shared by all text queries ------------------


def test_text_queries_share_one_ai_call_per_frame():
    prov = FakeProvider()
    dev = FakeDevice(prov)
    assert Selector(dev, {"text": "发送 Send"}).exists()
    assert Selector(dev, {"textContains": "Save"}).exists()
    assert Selector(dev, {"text": "取消 Cancel"}).count() == 1
    assert prov.calls == 1  # one full-node call served every text query


def test_text_filter_semantics():
    dev = FakeDevice(FakeProvider())
    assert Selector(dev, {"text": "保存 Save"}).exists()
    assert not Selector(dev, {"text": "不存在的按钮"}).exists()
    assert Selector(dev, {"textContains": "Send"}).count() == 1
    assert Selector(dev, {"textStartsWith": "取消"}).count() == 1
    assert Selector(dev, {"textMatches": r"Send.*"}).count() == 1


# -- P0-1: hard provider errors propagate; transient ones retry --------------


@pytest.mark.parametrize("exc", [
    ProviderAuthError("bad key"),
    ImageNotSupportedError("text-only model"),
])
def test_hard_provider_errors_propagate(exc):
    prov = FakeProvider(error=exc)
    dev = FakeDevice(prov)
    with pytest.raises(type(exc)):
        Selector(dev, {"text": "发送 Send"}).exists()
    # raised on the first attempt - no retry loop burning screenshots
    assert prov.calls == 1


def test_flaky_empty_still_retries_then_not_found():
    prov = FakeProvider(reply='{"nodes": []}')
    dev = FakeDevice(prov)
    assert Selector(dev, {"text": "x"}).exists() is False
    assert prov.calls == dev._config.resolve_retries + 1


# -- P1: page stability -------------------------------------------------------


def test_ahash_same_image_zero_diff():
    a = _ahash(_png())
    assert bin(a ^ _ahash(_png())).count("1") == 0


def test_ahash_different_image_large_diff():
    a = _ahash(_png())
    b = _ahash(_png(mark=True))
    assert bin(a ^ b).count("1") > 4


def test_wait_stable_returns_true_when_frames_settle():
    dev = FakeDevice(FakeProvider(), frames=[_png(), _png(mark=True)])
    # frame 0 -> poll forces frame 1 and stays there -> consecutive equal pairs
    assert _wait_frames_stable(
        lambda: dev._screenshot(force=True)[0], timeout=5, interval=0.05
    ) is True


def test_wait_stable_returns_false_when_never_settles():
    dev = CyclingDevice(FakeProvider(), frames=[_png(), _png(mark=True)])
    assert _wait_frames_stable(
        lambda: dev._screenshot(force=True)[0], timeout=0.4, interval=0.05
    ) is False


# -- v0.4.0 transports: request shapes, adaptive params, truncation ------------


class FakeAPIError(Exception):
    def __init__(self, msg: str, status_code: int):
        super().__init__(msg)
        self.status_code = status_code


def _chat_transport(model="kimi-k3", sampling=None):
    from visionauto.providers import create_transport
    return create_transport(
        base_url="https://api.moonshot.cn/v1",
        api_key="sk-x",
        model=model,
        sampling=sampling,
    )


def test_chat_transport_request_shape():
    t = _chat_transport(sampling={"max_tokens": 100, "top_k": 5})
    kw = t._build_request([b"img"], "prompt", json_mode=True)
    assert kw["model"] == "kimi-k3"
    assert kw["temperature"] == 0.0           # no quirk: sampling default
    assert kw["max_tokens"] == 100
    assert kw["top_k"] == 5
    assert kw["response_format"] == {"type": "json_object"}
    content = kw["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "prompt"}
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_chat_transport_thinking_model_omits_temperature():
    t = _chat_transport(model="qwq-32b")
    kw = t._build_request([b"img"], "p", json_mode=False)
    assert "temperature" not in kw


def test_maybe_drop_param_renames_max_tokens():
    t = _chat_transport()
    kw = {"model": "gpt-5", "max_tokens": 100}
    err = FakeAPIError(
        "Unsupported parameter: 'max_tokens' is not supported with this model. "
        "Use 'max_completion_tokens' instead.", 400)
    assert t._maybe_drop_param(err, kw) is True
    assert kw == {"model": "gpt-5", "max_completion_tokens": 100}


def test_maybe_drop_param_drops_top_k():
    t = _chat_transport()
    kw = {"model": "m", "top_k": 5, "temperature": 0}
    err = FakeAPIError("unknown parameter: top_k", 400)
    assert t._maybe_drop_param(err, kw) is True
    assert "top_k" not in kw and kw["temperature"] == 0


def test_maybe_drop_param_ignores_other_errors():
    t = _chat_transport()
    kw = {"model": "m"}
    assert t._maybe_drop_param(FakeAPIError("model not found", 404), kw) is False
    assert t._maybe_drop_param(FakeAPIError("bad image", 400), kw) is False


def test_truncated_output_raises_output_truncated():
    from types import SimpleNamespace
    from visionauto.exceptions import OutputTruncatedError

    t = _chat_transport()
    resp = SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content='{"nodes": ['),
        finish_reason="length",
    )])
    t._request = lambda kwargs: resp
    with pytest.raises(OutputTruncatedError):
        t.chat([b"img"], "prompt")


def test_endpoint_hint_in_error():
    from visionauto.providers.base import _endpoint_hint
    assert _endpoint_hint("qwen3.8-max") == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert _endpoint_hint("claude-sonnet-4-5") == "https://api.anthropic.com"
    assert _endpoint_hint("totally-custom-model") is None


def test_invalid_api_format_rejected():
    from visionauto.exceptions import ProviderConfigError
    from visionauto.providers import create_transport
    with pytest.raises(ProviderConfigError, match="api_format"):
        create_transport(api_key="sk-x", model="m", api_format="anthropic")


def test_responses_transport_request_shape():
    from visionauto.providers import create_transport
    t = create_transport(base_url="https://api.openai.com/v1", api_key="sk-x",
                         model="gpt-5", api_format="responses",
                         sampling={"max_tokens": 512, "top_k": 5})
    kw = t._build_request([b"img"], "p", json_mode=True)
    assert kw["model"] == "gpt-5"
    assert kw["max_output_tokens"] == 512      # protocol-specific key mapping
    assert "top_k" not in kw                   # not part of the Responses API
    assert kw["text"] == {"format": {"type": "json_object"}}
    content = kw["input"][0]["content"]
    assert content[0] == {"type": "input_text", "text": "p"}
    assert content[1]["type"] == "input_image"


def test_messages_transport_request_shape():
    anthropic = pytest.importorskip("anthropic")  # extra: visionauto[anthropic]
    from visionauto.providers import create_transport
    t = create_transport(base_url="https://api.anthropic.com", api_key="sk-ant-x",
                         model="claude-sonnet-4-5", api_format="messages",
                         sampling={"max_tokens": 512, "top_k": 7})
    kw = t._build_request([b"img"], "p", json_mode=True)
    assert kw["model"] == "claude-sonnet-4-5"
    assert kw["max_tokens"] == 512
    # sampling params ride in extra_body (SDK >= 1.0 dropped them from the
    # typed signature, but the HTTP API accepts them)
    assert kw["extra_body"]["top_k"] == 7            # natively supported
    assert "response_format" not in kw               # Messages API has no json mode
    block = kw["messages"][0]["content"][1]
    assert block["type"] == "image"
    assert block["source"]["type"] == "base64"


def test_messages_transport_default_max_tokens():
    pytest.importorskip("anthropic")
    from visionauto.providers import create_transport
    t = create_transport(base_url="https://api.anthropic.com", api_key="sk-ant-x",
                         model="claude-sonnet-4-5", api_format="messages")
    kw = t._build_request([b"img"], "p", json_mode=False)
    assert kw["max_tokens"] == 4096            # Anthropic requires it
