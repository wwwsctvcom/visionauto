"""WeChat example: open WeChat -> search -> enter a chat -> send a message.

Steps:
  1. 打开微信
  2. 点击右上角搜索按钮
  3. 输入测试文本
  4. 点击第一个出现的结果（搜索建议）
  5. 点击"联系人结果"下的第一个结果
  6. 点击文本输入框
  7. 输入"你好"
  8. 点击发送按钮

Run (provider/model/api_key are configured in _config.py; override via env):
    python examples/wechat_search.py

A full debug trace is saved to out/trace_wechat/ so you can replay every
recognition step if something goes wrong.
"""
from __future__ import annotations

import time

from _config import connect

WECHAT_PKG = "com.tencent.mm"
SEARCH_TEXT = "测试文本"
MESSAGE = "你好"


def main() -> None:
    d = connect()                          # 连接默认 adb 设备 + 示例 provider 配置
    d.start_debug("out/trace_wechat")      # 自动记录每次 AI 识别，便于排查

    try:
        # 1. 打开微信
        d.app_start(WECHAT_PKG)
        d(text="微信").wait(timeout=15)    # 等首页加载

        # 2. 点击右上角搜索按钮
        d(description="右上角的搜索按钮").click_exists(timeout=10)
        time.sleep(0.5)

        # 3. 输入测试文本
        d(description="搜索输入框").input(SEARCH_TEXT)
        time.sleep(1.0)                    # 等结果列表刷新

        # 4. 点击第一个出现的结果（通常是"搜索 测试文本"建议行）
        d(description="第一个搜索结果").click_exists(timeout=10)
        time.sleep(1.0)

        # 5. 点击"联系人结果"下的第一个结果，进入聊天
        d(description="联系人结果下的第一个联系人").click_exists(timeout=10)
        time.sleep(0.5)

        # 6. 点击文本输入框
        d(description="聊天输入框").click_exists(timeout=10)

        # 7. 输入你好
        d(description="聊天输入框").input(MESSAGE)

        # 8. 点击发送按钮
        d(text="发送").click_exists(timeout=10)

        print("done — check out/trace_wechat/ for the full trace")
    finally:
        d.stop_debug()


if __name__ == "__main__":
    main()
