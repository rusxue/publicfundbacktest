"""行情响应 Pydantic 模型。"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class Instrument(BaseModel):
    """标的元信息。"""

    code: str
    name: str
    type: Literal["ETF", "FUND"]


class KlineItem(BaseModel):
    """单根 K 线 / 净值点。

    - ETF：open/high/low/close/volume 有值，nav 为 None。
    - 基金日线：nav 有值，OHLCV 为 None（前端绘净值折线）。
    - 基金周线：由日净值重采样为伪 K 线，open/high/low/close 有值，volume 为 None，nav 取 close。
    """

    date: str
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    nav: Optional[float] = None
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma30: Optional[float] = None
    ma60: Optional[float] = None


class KlineResponse(BaseModel):
    instrument: Instrument
    is_degraded: bool
    klines: list[KlineItem]
