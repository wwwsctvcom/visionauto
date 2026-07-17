"""Prompt templates shared across providers.

All three use the SAME schema — a flat list of clickable (tappable) controls,
each with a bbox plus the OCR'd text (when the control has visible text).
Coordinate convention: 0-999 normalized. No "description" field is returned:
the AI's free-form description of a control is not stable enough to be a
localization key, so only bbox + OCR text are kept.
"""
from __future__ import annotations

# Shared JSON shape used by every prompt:
#   {"nodes": [{"bbox": [x1, y1, x2, y2], "text": "<OCR text or empty>"}]}

_COMMON_RULES = """Rules (apply to every node):
- bbox is [x1, y1, x2, y2] normalized to 0-999 across the whole image (0,0 = top-left, 999,999 = bottom-right).
- "text" is the visible text OCR'd from the control; use "" if the control has no text. Always OCR when text is present.
- Return each control's text as ONE contiguous string exactly as displayed — do NOT split a label into multiple nodes or fragments; keep original characters (spaces/no-spaces) verbatim.
- For an icon that carries a text label, return ONE node covering the tappable area (the icon, or icon+label) with the label as "text".
- Only describe what is actually visible on screen; do not invent hidden elements.
- The screen may be any device (phone, tablet, or other); treat whatever is shown as the full screen.
If nothing is found, return {"nodes": []}.
"""

# List ALL clickable controls with their OCR text. The locator then filters
# client-side by text / textContains / textMatches / textStartsWith.
TEXT_PROMPT = """You are a UI element locator.
Look at the screenshot of a device screen and list every tappable (clickable) control as flat nodes.
Return ONLY a JSON object, no markdown, no explanation, in this exact shape:
{"nodes": [{"bbox": [x1, y1, x2, y2], "text": "<OCR text or empty string>"}]}
""" + _COMMON_RULES


DESCRIPTION_PROMPT_TEMPLATE = """You are a UI element locator.
Find the tappable (clickable) control in the screenshot that best matches this natural-language description:
"{desc}"
Return ONLY a JSON object, no markdown, in this exact shape:
{"nodes": [{"bbox": [x1, y1, x2, y2], "text": "<OCR text or empty string>"}]}
- If multiple controls plausibly match, return all, best first.
""" + _COMMON_RULES


IMAGE_PROMPT = """You are a UI element locator.
The FIRST image is a screenshot of a device screen. The SECOND image is a target template.
Locate the tappable (clickable) control in the screenshot that matches the target template.
Return ONLY a JSON object, no markdown, in this exact shape:
{"nodes": [{"bbox": [x1, y1, x2, y2], "text": "<OCR text or empty string>"}]}
- If the target is not present in the screenshot, return {"nodes": []}.
""" + _COMMON_RULES
