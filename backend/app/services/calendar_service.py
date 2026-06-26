"""交易日历服务。

职责：
1. 维护本地 ``trade_calendar`` 表（交易日历），按 TTL 周期性从数据源刷新。
2. 提供"目标交易日"计算：交易日收盘后含今天，否则取上一交易日——供
   ``kline_service`` 判断本地行情是否已最新，命中则跳过远端拉取。

新鲜度判定完全由"本地最新日期 >= 目标交易日"驱动，比固定时间窗口更精确，
且与交易日历语义一致。目标交易日的收盘感知逻辑见 ``target_trade_date``。
"""
from __future__ import annotations

import asyncio
from datetime import datetime, time as dtime
from typing import Optional

import pandas as pd
from loguru import logger

from app.config import get_settings
from app.core.db import get_conn
from app.services import datasource
from app.services.throttle import throttle_remote


META_KEY_UPDATED_AT = "trade_calendar_updated_at"


# ---------- 查询 ----------

def last_trade_date_on_or_before(date: str) -> Optional[str]:
    """``<= date`` 的最近交易日（含 date）。表空返回 None。"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT MAX(calendar_date) AS d FROM trade_calendar "
            "WHERE calendar_date <= ?",
            (date,),
        ).fetchone()
    return row["d"] if row and row["d"] is not None else None


def last_trade_date_before(date: str) -> Optional[str]:
    """严格早于 ``date`` 的最近交易日。表空返回 None。"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT MAX(calendar_date) AS d FROM trade_calendar "
            "WHERE calendar_date < ?",
            (date,),
        ).fetchone()
    return row["d"] if row and row["d"] is not None else None


def is_trade_day(date: str) -> bool:
    """某自然日是否为交易日。"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM trade_calendar WHERE calendar_date = ?",
            (date,),
        ).fetchone()
    return row is not None


def _parse_close_time(raw: str) -> dtime:
    """解析 ``trade_close_time``（如 "15:00"）为 time。失败回退 15:00。"""
    try:
        parts = raw.strip().split(":")
        return dtime(int(parts[0]), int(parts[1]))
    except Exception:
        return dtime(15, 0)


def target_trade_date(now: datetime) -> Optional[str]:
    """计算目标最新交易日（收盘感知）。

    - 今天是交易日且 ``now`` 已过收盘时间 → 今天（收盘后允许拉取当天数据）；
    - 否则 → 上一交易日（严格早于今天）。

    表空（交易日历尚未就绪）返回 None，调用方据此走"无新鲜度信息"的兜底
    （即按原增量逻辑拉取）。
    """
    today = now.strftime("%Y-%m-%d")
    close = _parse_close_time(get_settings().trade_close_time)
    if is_trade_day(today) and now.time() >= close:
        return last_trade_date_on_or_before(today)
    return last_trade_date_before(today)


# ---------- meta ----------

def _meta_get(key: str) -> Optional[str]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM meta WHERE key = ?", (key,)
        ).fetchone()
    return row["value"] if row else None


def _meta_set(key: str, value: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (key, value),
        )


def _calendar_count() -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM trade_calendar").fetchone()
    return int(row["c"]) if row else 0


def _is_stale() -> bool:
    """交易日表是否需要刷新：空表，或距上次更新超过 TTL。"""
    if _calendar_count() == 0:
        return True
    updated = _meta_get(META_KEY_UPDATED_AT)
    if not updated:
        return True
    try:
        updated_dt = datetime.fromisoformat(updated)
    except ValueError:
        return True
    ttl = get_settings().trade_calendar_ttl_days
    return (datetime.now() - updated_dt).days >= ttl


def _replace_calendar(df: pd.DataFrame) -> None:
    """全量替换交易日表。"""
    records = [(str(r["calendar_date"]), int(r["is_trade_day"])) for _, r in df.iterrows()]
    with get_conn() as conn:
        conn.execute("DELETE FROM trade_calendar")
        conn.executemany(
            "INSERT INTO trade_calendar (calendar_date, is_trade_day) VALUES (?, ?)",
            records,
        )


async def ensure_trade_calendar() -> None:
    """确保交易日表就绪且新鲜。已新鲜则直接返回，不触发任何远端请求。

    需要刷新时经 ``throttle_remote`` 节流后拉取（防封），失败仅告警不抛——
    后续请求会重试，避免交易日历故障阻断行情查询。
    """
    if not _is_stale():
        return

    await throttle_remote()
    try:
        df = await asyncio.to_thread(datasource.fetch_trade_calendar)
    except Exception as exc:
        logger.warning("交易日历刷新失败，沿用现有缓存: {}", exc)
        return

    _replace_calendar(df)
    _meta_set(META_KEY_UPDATED_AT, datetime.now().isoformat(timespec="seconds"))
    logger.info("交易日历已刷新 行数={}", len(df))
