"""行情接口路由。

GET /api/v1/market/kline/{code}?period=daily|weekly
"""
from __future__ import annotations

import time
from enum import Enum

from fastapi import APIRouter, Path, Query
from loguru import logger

from app.core.errors import NotFoundError
from app.schemas.kline import KlineResponse
from app.services.kline_service import get_kline


router = APIRouter(prefix="/market", tags=["行情"])


class Period(str, Enum):
    daily = "daily"
    weekly = "weekly"


@router.get("/kline/{code}", response_model=KlineResponse, summary="获取 K 线行情")
async def fetch_kline(
    code: str = Path(..., description="6 位标的代码", min_length=6, max_length=6),
    period: Period = Query(Period.daily, description="周期：daily / weekly"),
) -> KlineResponse:
    """获取 ETF 或开放式基金的行情数据。

    - ETF：真实 OHLCV 蜡烛图。
    - 开放式基金日线：单位净值序列（nav）。
    - 基金周线：由日净值重采样为伪 K 线。
    - MA5/10/20/30/60 由后端预计算。
    """
    start = time.perf_counter()
    code = code.strip()
    if not code.isdigit():
        raise NotFoundError("代码格式不正确，需为 6 位数字")

    result = await get_kline(code, period.value)
    cost = (time.perf_counter() - start) * 1000
    logger.info("GET /kline/{} period={} 耗时={:.1f}ms", code, period.value, cost)
    return result
