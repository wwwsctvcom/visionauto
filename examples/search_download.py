"""Home-search example: go home -> search "微信" -> download or open the first result.

Steps:
  1. 进入主页（按 home 键）
  2. 点击页面上方的搜索框
  3. 输入"微信"
  4. 按 enter
  5. 判断第一个搜索结果右侧是否存在"下载"按钮
     - 存在则点击"下载"
     - 否则点击"打开"

Run:
    python examples/search_download.py

A full debug trace is saved to out/trace_search/ for replay.
"""
from __future__ import annotations

import time

from _config import connect

SEARCH_TEXT = "微信"


def main() -> None:
    d = connect()
    d.start_debug("out/trace_search")

    try:
        # 1. 进入主页
        d.press("home")
        time.sleep(0.5)

        # 2. 点击页面上方的搜索框
        d(description="页面上方的搜索框").click_exists(timeout=10)
        time.sleep(0.5)

        # 3. 输入微信
        d(description="搜索输入框").input(SEARCH_TEXT)
        time.sleep(1.0)

        # 4. 按 enter 触发搜索
        d.press("enter")
        time.sleep(1.0)                    # 等结果列表刷新

        # 5. 等第一个结果出现
        d(description=f"第一个搜索结果{SEARCH_TEXT}").wait(timeout=10)

        # 6. 判断第一个结果右侧是"下载"还是"打开"，并点击
        download_btn = d(description=f"第一个搜索结果{SEARCH_TEXT}右侧的下载按钮")
        if download_btn.exists():
            download_btn.click()
            print("clicked 下载")
        else:
            d(description=f"第一个搜索结果{SEARCH_TEXT}右侧的打开按钮").click()
            print("clicked 打开")

        print("done — check out/trace_search/ for the full trace")
    finally:
        d.stop_debug()


if __name__ == "__main__":
    main()
