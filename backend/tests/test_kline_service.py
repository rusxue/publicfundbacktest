"""kline_service 新鲜度跳过、增量拉取与节流测试。

全程 monkeypatch akshare，无真实网络。日历相关被桩替换以隔离 today 依赖。
"""
from __future__ import annotations

import asyncio

import pandas as pd
import pytest

from app.core.errors import NotFoundError
from app.services import calendar_service, kline_service, throttle


def _make_local(latest_date: str, instrument_type: str = "ETF", name: str = "测试ETF") -> pd.DataFrame:
    """构造 _load_local 同构的本地 DataFrame。"""
    return pd.DataFrame([{
        "date": latest_date,
        "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 100.0,
        "nav": None, "instrument_type": instrument_type, "name": name,
    }])


def _stub_calendar(monkeypatch, target):
    """桩掉日历：ensure 不做事，target 返回固定值（None 表示未就绪）。"""
    async def noop():
        return None
    monkeypatch.setattr(calendar_service, "ensure_trade_calendar", noop)
    monkeypatch.setattr(calendar_service, "target_trade_date", lambda now: target)


def test_refresh_skips_when_local_is_latest(tmp_db, monkeypatch):
    """本地最新日期 >= target → 跳过远端拉取。"""
    _stub_calendar(monkeypatch, "2026-06-25")
    local = _make_local("2026-06-25")
    calls = {"n": 0}

    def boom(*a, **k):
        calls["n"] += 1
        return pd.DataFrame()

    monkeypatch.setattr(kline_service.datasource, "fetch_etf_daily", boom)
    monkeypatch.setattr(kline_service, "throttle_remote", lambda: asyncio.sleep(0))

    name = asyncio.run(kline_service._refresh("159915", "ETF", local))
    assert calls["n"] == 0
    assert name == "测试ETF"


def test_refresh_fetches_when_no_local(tmp_db, monkeypatch):
    """无本地数据 → 走全量拉取（不依赖 today 比较，路径稳定）。"""
    _stub_calendar(monkeypatch, "2026-06-25")
    calls = {"n": 0}

    def fake(*a, **k):
        calls["n"] += 1
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

    monkeypatch.setattr(kline_service.datasource, "fetch_etf_daily", fake)
    monkeypatch.setattr(kline_service, "throttle_remote", lambda: asyncio.sleep(0))
    # name 未知时会调 resolve_instrument 取名，一并桩掉避免真实网络
    monkeypatch.setattr(
        kline_service.datasource,
        "resolve_instrument",
        lambda code, t: (code, t, "测试ETF"),
    )

    name = asyncio.run(kline_service._refresh("159915", "ETF", None))
    assert calls["n"] == 1
    assert name == "测试ETF"


def test_refresh_type_mismatch_raises(tmp_db, monkeypatch):
    """本地 ETF、请求 FUND 且日历未就绪(target=None,不跳过) → 类型校验 → NOT_FOUND。"""
    _stub_calendar(monkeypatch, None)
    local = _make_local("2026-06-25", instrument_type="ETF")
    with pytest.raises(NotFoundError):
        asyncio.run(kline_service._refresh("159915", "FUND", local))


def test_throttle_skips_first_sleeps_second(monkeypatch):
    """reset 后首次不 sleep（距上次很远），紧接第二次补足间隔。"""
    throttle.reset_throttle()
    sleeps = []

    async def fake_sleep(s):
        sleeps.append(s)

    monkeypatch.setattr(throttle.asyncio, "sleep", fake_sleep)
    asyncio.run(throttle.throttle_remote())
    assert sleeps == []
    asyncio.run(throttle.throttle_remote())
    assert len(sleeps) == 1
    assert sleeps[0] > 0
