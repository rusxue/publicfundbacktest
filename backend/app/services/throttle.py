"""远端请求节流器。

数据源请求间隔（``data_source_interval``，默认 1.5s）用于防止共享 IP 被封禁。
原实现是"每次请求开头无条件 sleep"，会拖慢命中缓存的请求；这里改为
"距上次远端请求不足间隔才 sleep"，并用锁串行化，避免并发请求穿透间隔。

节流器为进程内状态（``_last_remote_ts``），重启归零——可接受，重启后首次
请求本就要拉取。命中新鲜度而跳过刷新的路径根本不进入节流器，因此不会
被这 1.5s 拖慢。
"""
from __future__ import annotations

import asyncio
import time

from app.config import get_settings


_last_remote_ts: float = 0.0
_remote_lock: asyncio.Lock | None = None
_remote_loop: object | None = None


def _get_lock() -> asyncio.Lock:
    """懒初始化锁，并在事件循环变化时重建（测试用 asyncio.run 会切换循环）。"""
    global _remote_lock, _remote_loop
    loop = asyncio.get_running_loop()
    if _remote_lock is None or _remote_loop is not loop:
        _remote_lock = asyncio.Lock()
        _remote_loop = loop
    return _remote_lock


async def throttle_remote() -> None:
    """距上次远端请求不足 ``data_source_interval`` 才 sleep；串行化避免并发穿透。

    任何对 akshare 的远端调用（行情增量、交易日历拉取）前都应调用本函数。
    """
    global _last_remote_ts
    interval = get_settings().data_source_interval
    async with _get_lock():
        elapsed = time.monotonic() - _last_remote_ts
        gap = interval - elapsed
        if gap > 0:
            await asyncio.sleep(gap)
        _last_remote_ts = time.monotonic()


def reset_throttle() -> None:
    """重置节流状态（测试用）。"""
    global _last_remote_ts, _remote_lock, _remote_loop
    _last_remote_ts = 0.0
    _remote_lock = None
    _remote_loop = None
