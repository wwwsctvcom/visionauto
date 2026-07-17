"""Popup handling example using uiautomator2's watcher (accessibility-based).

visionauto's VisionDevice transparently delegates ``d.watcher`` to u2, so you
handle popups (权限弹窗、"知道了"、"暂不"、广告关闭等) exactly the u2 way — no
vision needed. The watcher runs in a background thread, dumping the UI hierarchy
and auto-clicking matched controls as they appear.

This is the recommended way to dismiss popups: it's instant and free (no AI
calls), and works on standard-system dialogs that have accessibility text.
Use vision (d(text=...)/d(description=...)) only for popups u2 can't see.

Run:
    python examples/popup_watcher.py
"""
from __future__ import annotations

import time

from _config import connect

# Common Chinese popup button texts to auto-dismiss. Add/remove for your apps.
POPUPS = [
    "允许", "始终允许", "仅在使用中允许",
    "知道了", "我知道了", "确定", "确认",
    "暂不", "以后再说", "稍后", "跳过",
    "关闭", "取消", "不升级",
    "Agree", "ALLOW", "Allow",
]


def main() -> None:
    d = connect()

    # 1. register rules: when any of these texts appears, click it.
    #    `when` accepts bare text (matches @text/@content-desc) or an xpath.
    for txt in POPUPS:
        d.watcher.when(txt).click()

    # 2. start the background watcher (polls every 2s by default).
    d.watcher.start(2.0)
    print("watcher running:", d.watcher.running())

    try:
        # 3. your main flow goes here — popups are auto-dismissed in parallel.
        #    Example: open WeChat; any permission/upgrade popup gets clicked away.
        d.app_start("com.tencent.mm")
        time.sleep(6)
        # ...chain vision steps, e.g. d(description="...").click_exists()...
    finally:
        # 4. stop and clear rules when done.
        d.watcher.stop()
        d.watcher.reset()
        print("watcher stopped")


if __name__ == "__main__":
    main()
