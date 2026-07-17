"""Draw located nodes onto a screenshot for debugging."""
from __future__ import annotations

import io
import os

from PIL import Image, ImageDraw, ImageFont

from .located import Located

_COLORS = [
    (255, 0, 0), (0, 180, 0), (0, 0, 255), (255, 128, 0),
    (128, 0, 255), (0, 180, 180), (255, 0, 200), (80, 80, 80),
]
_PICKED_COLOR = (0, 200, 0)


def _font(size: int) -> ImageFont.ImageFont:
    for path in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/arial.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _label_width(label: str, font) -> int:
    try:
        return font.getlength(label)
    except Exception:
        return len(label) * 18


def draw_nodes(
    screenshot_png: bytes,
    nodes: list[Located],
    *,
    command: str | None = None,
    picked_index: int | None = None,
) -> Image.Image:
    """Annotate the screenshot with node bboxes.

    - ``command`` given (trace mode): the picked box is labeled with the user's
      command (e.g. ``description='...'``) and drawn bold green; other matched
      boxes are thin gray with just their index. No OCR text is drawn — so you
      can verify the prompt actually matched the right control.
    - ``command`` None (dump mode): every box is labeled with its OCR text.
    """
    img = Image.open(io.BytesIO(screenshot_png)).convert("RGB")
    w, h = img.size
    draw = ImageDraw.Draw(img)
    font = _font(max(16, min(28, w // 40)))
    bold_w = max(6, w // 250)
    thin_w = max(2, w // 500)

    for i, node in enumerate(nodes):
        b = node.bbox  # BBox in canonical [0,1]
        x1, y1 = int(b.x1 * w), int(b.y1 * h)
        x2, y2 = int(b.x2 * w), int(b.y2 * h)
        is_picked = picked_index is not None and i == picked_index

        if command is not None:
            if is_picked:
                color, width, label = _PICKED_COLOR, bold_w, command
            else:
                color, width, label = (160, 160, 160), thin_w, f"#{i}"
        else:
            color = _COLORS[i % len(_COLORS)]
            width = bold_w
            label = (node.text or "").strip()

        draw.rectangle([x1, y1, x2, y2], outline=color, width=width)
        if label:
            lw = max(_label_width(label, font) + 8, len(label) * 10)
            top = max(0, y1 - 28)
            draw.rectangle([x1, top, x1 + lw, top + 28], fill=color)
            draw.text((x1 + 4, top + 2), label, fill=(255, 255, 255), font=font)
    return img
