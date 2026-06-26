"""交易日历服务测试。

不依赖真实 akshare，trade_calendar 表由测试直接播种。
"""
from __future__ import annotations

import asyncio
from datetime import datetime

import pandas as pd

from app.core.db import get_conn
from app.services import calendar_service


# 测试用交易日序列（不依赖真实星期，是否交易日完全由表内容决定）
TRADE_DAYS = ["2026-06-22", "2026-06-23", "2026-06-24", "2026-06-25", "2026-06-26"]


def _seed_calendar(dates: list[str]) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM trade_calendar")
        conn.executemany(
            "INSERT INTO trade_calendar (calendar_date, is_trade_day) VALUES (?, 1)",
            [(d,) for d in dates],
        )


def test_last_trade_date_on_or_before(tmp_db):
    _seed_calendar(TRADE_DAYS)
    # 含当天
    assert calendar_service.last_trade_date_on_or_before("2026-06-26") == "2026-06-26"
    # 周六查询，最近交易日是周五
    assert calendar_service.last_trade_date_on_or_before("2026-06-27") == "2026-06-26"
    # 早于所有交易日
    assert calendar_service.last_trade_date_on_or_before("2026-06-21") is None


def test_last_trade_date_before(tmp_db):
    _seed_calendar(TRADE_DAYS)
    assert calendar_service.last_trade_date_before("2026-06-26") == "2026-06-25"
    # 最早交易日之前无数据
    assert calendar_service.last_trade_date_before("2026-06-22") is None


def test_is_trade_day(tmp_db):
    _seed_calendar(TRADE_DAYS)
    assert calendar_service.is_trade_day("2026-06-26") is True
    assert calendar_service.is_trade_day("2026-06-27") is False


def test_empty_calendar(tmp_db):
    assert calendar_service.last_trade_date_on_or_before("2026-06-26") is None
    assert calendar_service.is_trade_day("2026-06-26") is False


def test_target_trade_date_after_close(tmp_db):
    _seed_calendar(TRADE_DAYS)
    # 交易日 15:00 后 → 今天
    now = datetime(2026, 6, 26, 15, 0)
    assert calendar_service.target_trade_date(now) == "2026-06-26"


def test_target_trade_date_before_close(tmp_db):
    _seed_calendar(TRADE_DAYS)
    # 交易日 15:00 前 → 上一交易日
    now = datetime(2026, 6, 26, 14, 59)
    assert calendar_service.target_trade_date(now) == "2026-06-25"


def test_target_trade_date_non_trade_day(tmp_db):
    _seed_calendar(TRADE_DAYS)
    # 非交易日（周六）全天 → 上一交易日
    now = datetime(2026, 6, 27, 16, 0)
    assert calendar_service.target_trade_date(now) == "2026-06-26"


def test_target_trade_date_empty(tmp_db):
    # 日历未就绪 → None，调用方据此走兜底
    now = datetime(2026, 6, 26, 16, 0)
    assert calendar_service.target_trade_date(now) is None


def test_ensure_trade_calendar_fresh_no_fetch(tmp_db, monkeypatch):
    """表已新鲜时不应触发远端拉取。"""
    _seed_calendar(TRADE_DAYS)
    calendar_service._meta_set(
        calendar_service.META_KEY_UPDATED_AT,
        datetime.now().isoformat(timespec="seconds"),
    )
    calls = {"n": 0}

    def boom(*a, **k):
        calls["n"] += 1
        raise RuntimeError("不应拉取")

    monkeypatch.setattr(calendar_service.datasource, "fetch_trade_calendar", boom)
    asyncio.run(calendar_service.ensure_trade_calendar())
    assert calls["n"] == 0


def test_ensure_trade_calendar_stale_refreshes(tmp_db, monkeypatch):
    """空表（stale）时应拉取并替换。"""
    monkeypatch.setattr(calendar_service, "throttle_remote", lambda: asyncio.sleep(0))
    fake = pd.DataFrame({
        "calendar_date": ["2026-07-01", "2026-07-02"],
        "is_trade_day": [1, 1],
    })
    monkeypatch.setattr(calendar_service.datasource, "fetch_trade_calendar", lambda: fake)
    asyncio.run(calendar_service.ensure_trade_calendar())
    assert calendar_service.is_trade_day("2026-07-01") is True
    assert calendar_service.is_trade_day("2026-07-02") is True
