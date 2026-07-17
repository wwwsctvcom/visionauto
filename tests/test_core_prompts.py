"""Test visionauto's three core prompts against a real device screenshot.

The screenshot is captured from the default adb-connected device via
`adb exec-out screencap -p`. Each prompt is sent to the configured provider,
the returned nodes are drawn on the screenshot, and the annotated image is
saved under ``out/`` so you can eyeball the recognition.

All parameters come through the framework's generic Config (one set of env
vars, no per-provider specifics — works with any OpenAI-compatible model):
  VISIONAUTO_PROVIDER  glm | qwen | openai   (default glm)
  VISIONAUTO_API_KEY    api key
  VISIONAUTO_MODEL      model name (defaults from the provider if any)
  VISIONAUTO_BASE_URL   endpoint (defaults from the provider if any)
  VISIONAUTO_DESC_QUERY description query for the description-prompt test

Run:
    pytest -v -s tests/test_core_prompts.py
"""
from __future__ import annotations

import io
import os
import subprocess

import pytest
from PIL import Image, ImageDraw, ImageFont

from visionauto.config import Config
from visionauto.prompts import (
    DESCRIPTION_PROMPT_TEMPLATE,
    IMAGE_PROMPT,
    TEXT_PROMPT,
)
from visionauto.providers import get_provider
from visionauto.utils import parse_json

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "out")
DEFAULT_DESC_QUERY = "屏幕中的原神图标"


# Distinct colors per node so overlaps are visible.
_COLORS = [
    (255, 0, 0), (0, 180, 0), (0, 0, 255), (255, 128, 0),
    (128, 0, 255), (0, 180, 180), (255, 0, 200), (80, 80, 80),
]


def _font(size: int) -> ImageFont.ImageFont:
    for path in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/arial.ttf"):
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _adb_screenshot() -> bytes:
    """Capture a PNG screenshot from the default adb device."""
    res = subprocess.run(
        ["adb", "exec-out", "screencap", "-p"],
        capture_output=True,
        timeout=30,
    )
    if res.returncode != 0 or not res.stdout.startswith(b"\x89PNG"):
        pytest.skip(f"adb screencap failed: {res.stderr.decode(errors='replace')[:200]}")
    return res.stdout


def _provider():
    cfg = Config.from_env()
    if not cfg.api_key:
        pytest.skip("set VISIONAUTO_API_KEY")
    return get_provider(cfg)


def _draw(screenshot_png: bytes, nodes: list[dict], out_name: str) -> None:
    """Draw bboxes (+ text labels) on the screenshot and save to out/<out_name>."""
    os.makedirs(OUT_DIR, exist_ok=True)
    img = Image.open(io.BytesIO(screenshot_png)).convert("RGB")
    w, h = img.size
    draw = ImageDraw.Draw(img)
    font = _font(max(16, min(28, w // 40)))
    for i, node in enumerate(nodes):
        bbox = node.get("bbox")
        if not bbox or len(bbox) < 4:
            continue
        # values come in 0-999; map to pixels
        x1, y1, x2, y2 = (
            int(bbox[0] / 999 * w), int(bbox[1] / 999 * h),
            int(bbox[2] / 999 * w), int(bbox[3] / 999 * h),
        )
        color = _COLORS[i % len(_COLORS)]
        draw.rectangle([x1, y1, x2, y2], outline=color, width=max(3, w // 400))
        label = (node.get("text") or "").strip()
        if label:
            draw.rectangle([x1, max(0, y1 - 28), x1 + len(label) * 18, y1], fill=color)
            draw.text((x1 + 4, max(0, y1 - 26)), label, fill=(255, 255, 255), font=font)
    out_path = os.path.join(OUT_DIR, out_name)
    img.save(out_path)
    print(f"\nsaved {out_path} ({len(nodes)} nodes)")


@pytest.fixture(scope="module")
def screenshot_png() -> bytes:
    return _adb_screenshot()


@pytest.fixture(scope="module")
def provider():
    return _provider()


def test_text_prompt(screenshot_png: bytes, provider):
    """TEXT_PROMPT: list all clickable controls with OCR text."""
    raw = provider.chat([screenshot_png], TEXT_PROMPT, json_mode=True)
    data = parse_json(raw)
    nodes = data.get("nodes", [])
    assert isinstance(nodes, list), f"unexpected response: {raw[:200]}"
    _draw(screenshot_png, nodes, "text_prompt.png")
    print(f"\nTEXT_PROMPT returned {len(nodes)} nodes")


def test_description_prompt(screenshot_png: bytes, provider):
    """DESCRIPTION_PROMPT: locate a control by natural-language description."""
    desc = os.environ.get("VISIONAUTO_DESC_QUERY", DEFAULT_DESC_QUERY)
    prompt = DESCRIPTION_PROMPT_TEMPLATE.replace("{desc}", desc)
    raw = provider.chat([screenshot_png], prompt, json_mode=True)
    data = parse_json(raw)
    nodes = data.get("nodes", [])
    assert isinstance(nodes, list), f"unexpected response: {raw[:200]}"
    _draw(screenshot_png, nodes, "description_prompt.png")
    print(f"\nDESCRIPTION_PROMPT ({desc!r}) returned {len(nodes)} nodes")


def test_image_prompt(screenshot_png: bytes, provider):
    """IMAGE_PROMPT: crop a template from the screenshot and find it back."""
    img = Image.open(io.BytesIO(screenshot_png)).convert("RGB")
    w, h = img.size
    # Crop the top-right quadrant as a template (usually has distinctive icons).
    crop = img.crop((w // 2, 0, w, h // 2))
    buf = io.BytesIO()
    crop.save(buf, format="PNG")
    template_png = buf.getvalue()
    # also save the template for reference
    os.makedirs(OUT_DIR, exist_ok=True)
    crop.save(os.path.join(OUT_DIR, "_image_template.png"))

    raw = provider.chat([screenshot_png, template_png], IMAGE_PROMPT, json_mode=True)
    data = parse_json(raw)
    nodes = data.get("nodes", [])
    assert isinstance(nodes, list), f"unexpected response: {raw[:200]}"
    _draw(screenshot_png, nodes, "image_prompt.png")
    print(f"\nIMAGE_PROMPT returned {len(nodes)} nodes")
