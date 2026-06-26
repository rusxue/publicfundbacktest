"""行情主流程服务。

职责：
1. 优先读本地库；无数据拉近 3 年全量，否则只拉增量。
2. 写库幂等（INSERT OR REPLACE）。
3. 遵守数据源请求间隔（默认 1.5s）防封禁。
4. 上游不可用时返回本地缓存并置 is_degraded；无缓存抛 503。
5. 从库取全量日线 → 周线重采样 → MA → 组装响应。
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import pandas as pd
from loguru import logger

from app.config import get_settings
from app.core.db import get_conn
from app.core.errors import DataSourceError, NotFoundError
from app.schemas.kline import Instrument, KlineItem, KlineResponse
from app.services import datasource
from app.services.ma import compute_ma
from app.services.resample import resample_weekly


PERIOD_DAILY = "daily"
PERIOD_WEEKLY = "weekly"


# ---------- 本地读写 ----------

def _load_local(code: str) -> pd.DataFrame | None:
    """从本地库读取该 code 全量日线。无数据返回 None。"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT date, open, high, low, close, volume, nav, instrument_type, name "
            "FROM klines WHERE code = ? ORDER BY date",
            (code,),
        ).fetchall()
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=[
        "date", "open", "high", "low", "close", "volume", "nav", "instrument_type", "name"
    ])
    return df


def _local_latest_date(df: pd.DataFrame) -> str | None:
    if df is None or df.empty:
        return None
    return str(df["date"].iloc[-1])


def _upsert(code: str, df: pd.DataFrame, instrument_type: str, name: str) -> int:
    """幂等写入。df 需含 date 与数据列。返回写入行数。"""
    # 标准化列
    records = []
    for _, r in df.iterrows():
        records.append((
            code,
            str(r["date"]),
            _float_or_none(r.get("open")),
            _float_or_none(r.get("high")),
            _float_or_none(r.get("low")),
            _float_or_none(r.get("close")),
            _float_or_none(r.get("volume")),
            _float_or_none(r.get("nav")),
            instrument_type,
            name,
        ))
    if not records:
        return 0
    with get_conn() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO klines "
            "(code, date, open, high, low, close, volume, nav, instrument_type, name) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            records,
        )
    return len(records)


def _float_or_none(v):
    if v is None:
        return None
    try:
        f = float(v)
        if pd.isna(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


# ---------- 增量拉取 ----------

async def _refresh(code: str, instrument_type: str) -> str:
    """按增量策略拉取并入库，返回标的名称。

    :raises NotFoundError: 代码不存在
    :raises DataSourceError: 数据源故障且本地无缓存
    """
    settings = get_settings()
    local = _load_local(code)
    latest = _local_latest_date(local)
    name = local["name"].iloc[0] if (local is not None and not local.empty) else None
    # 标的类型始终以调用方（前端选项条）传入为准，不读本地库 instrument_type，
    # 避免历史脏数据把类型改回去

    # 计算拉取区间
    if latest is None:
        start, end = _range(settings.history_years)
    else:
        # 类型不匹配校验：本地缓存的类型与请求类型不一致时，视为该代码在请求类型下不存在。
        # 避免本地脏数据（如历史误存的 ETF 数据）在按另一类型查询时被原样返回。
        cached_type = str(local["instrument_type"].iloc[0])
        if cached_type != instrument_type:
            logger.info(
                "类型不匹配 code={} cached={} requested={} -> NOT_FOUND",
                code, cached_type, instrument_type,
            )
            raise NotFoundError()
        # 从最新日期次日开始
        start_dt = datetime.strptime(latest, "%Y-%m-%d") + timedelta(days=1)
        start = start_dt.strftime("%Y%m%d")
        end = datetime.now().strftime("%Y%m%d")
        if start > end:
            # 已是最新，无需拉取
            if name is None:
                _, _, name = await asyncio.to_thread(
                    datasource.resolve_instrument, code, instrument_type
                )
            return name

    # 遵守请求间隔
    await asyncio.sleep(settings.data_source_interval)

    try:
        if instrument_type == "ETF":
            fetched = await asyncio.to_thread(datasource.fetch_etf_daily, code, start, end)
            fetched = fetched.copy()
            fetched["nav"] = None
        else:
            fetched = await asyncio.to_thread(datasource.fetch_fund_nav, code, start, end)
            fetched = fetched.copy()
            fetched["open"] = None
            fetched["high"] = None
            fetched["low"] = None
            fetched["close"] = None
            fetched["volume"] = None
    except NotFoundError:
        # 代码不存在；本地若有缓存则仍报不存在（符合 NOT_FOUND 语义）
        raise
    except DataSourceError:
        if local is not None and not local.empty:
            raise
        raise

    # 名称若未知，尝试解析
    if name is None:
        try:
            _, _, name = await asyncio.to_thread(
                datasource.resolve_instrument, code, instrument_type
            )
        except Exception:
            name = code

    # 增量区间内无新数据（本地已是最新）：无操作返回
    if fetched.empty:
        logger.info("增量区间无新数据 code={} type={}", code, instrument_type)
        return name or code

    _upsert(code, fetched, instrument_type, name or code)
    logger.info("增量拉取入库 code={} type={} 行数={}", code, instrument_type, len(fetched))
    return name or code


def _range(years: int) -> tuple[str, str]:
    end = datetime.now()
    start = end - timedelta(days=365 * years)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


# ---------- 主入口 ----------

async def get_kline(code: str, period: str, instrument_type: str) -> KlineResponse:
    """获取 K 线数据。

    :param code: 6 位标的代码
    :param period: daily / weekly
    :param instrument_type: 标的类型 ETF / FUND（由前端选项条指定），
        后端严格按此类型路由数据源，不再按代码前缀猜测，也不在两类间回退。
    """
    code = code.strip()
    is_degraded = False

    # 1. 先尝试增量刷新本地库；失败则降级到本地缓存
    # 标的类型以传入的 instrument_type 为准（本地库 instrument_type 不再驱动主流程）
    local = _load_local(code)

    try:
        await _refresh(code, instrument_type)
    except DataSourceError:
        # 严格按类型：NotFound 直接上抛，不在两类间回退；仅数据源故障时降级本地缓存
        if local is None or local.empty:
            raise
        is_degraded = True
        logger.warning("数据源故障，使用本地缓存降级 code={}", code)

    # 2. 从库取全量
    df = _load_local(code)
    if df is None or df.empty:
        raise NotFoundError()

    name = str(df["name"].iloc[0] or code)

    # 3. 周期处理
    if period == PERIOD_WEEKLY:
        df = resample_weekly(df, instrument_type)
        base_col = "close"  # ETF 与基金周线均有 close
    else:
        base_col = "nav" if instrument_type == "FUND" else "close"

    # 4. MA
    df = compute_ma(df, base_col)

    # 5. 组装响应
    klines: list[KlineItem] = []
    for _, r in df.iterrows():
        klines.append(
            KlineItem(
                date=str(r["date"]),
                open=_float_or_none(r.get("open")),
                high=_float_or_none(r.get("high")),
                low=_float_or_none(r.get("low")),
                close=_float_or_none(r.get("close")),
                volume=_float_or_none(r.get("volume")),
                nav=_float_or_none(r.get("nav")),
                ma5=_float_or_none(r.get("ma5")),
                ma10=_float_or_none(r.get("ma10")),
                ma20=_float_or_none(r.get("ma20")),
                ma30=_float_or_none(r.get("ma30")),
                ma60=_float_or_none(r.get("ma60")),
            )
        )

    instrument = Instrument(code=code, name=name, type=instrument_type)  # type: ignore[arg-type]
    logger.info(
        "行情返回 code={} type={} period={} 条数={} degraded={}",
        code, instrument_type, period, len(klines), is_degraded,
    )
    return KlineResponse(instrument=instrument, is_degraded=is_degraded, klines=klines)
