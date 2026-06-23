"""周线重采样。

按金融标准：周线以周五为界。
- 开 = 首日值
- 收 = 末日值
- 高 = 区间最高
- 低 = 区间最低
- 成交量 = 区间求和（ETF）

ETF 用真实 OHLCV 重采样；基金从日净值序列重采样为伪 K 线
（open=first nav, close=last nav, high=max nav, low=min nav, volume=None）。
"""
from __future__ import annotations

import pandas as pd

from app.schemas.kline import Instrument


def resample_etf_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """ETF 周线重采样。输入含 date/open/high/low/close/volume。"""
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])
    d = d.set_index("date")
    weekly = d.resample("W-FRI").agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
    ).dropna(subset=["open"])
    weekly = weekly.reset_index()
    weekly["date"] = weekly["date"].dt.strftime("%Y-%m-%d")
    weekly["nav"] = None
    return weekly[["date", "open", "high", "low", "close", "volume", "nav"]]


def resample_fund_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """基金周线：从日净值序列重采样为伪 K 线。输入含 date/nav。"""
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])
    d = d.set_index("date")
    weekly = d.resample("W-FRI").agg(
        {
            "nav": "last",  # 周末净值，保留供 MA 计算
        }
    )
    # 构造伪 OHLC
    weekly["open"] = d.resample("W-FRI")["nav"].first()
    weekly["close"] = d.resample("W-FRI")["nav"].last()
    weekly["high"] = d.resample("W-FRI")["nav"].max()
    weekly["low"] = d.resample("W-FRI")["nav"].min()
    weekly["volume"] = None
    weekly = weekly.dropna(subset=["nav"]).reset_index()
    weekly["date"] = weekly["date"].dt.strftime("%Y-%m-%d")
    return weekly[["date", "open", "high", "low", "close", "volume", "nav"]]


def resample_weekly(df: pd.DataFrame, instrument_type: str) -> pd.DataFrame:
    """按标的类型分派重采样。"""
    if instrument_type == "ETF":
        return resample_etf_weekly(df)
    return resample_fund_weekly(df)
