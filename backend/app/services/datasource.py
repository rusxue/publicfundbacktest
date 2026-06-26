"""akshare 数据源适配器。

职责：把 akshare 返回的原始 DataFrame 规范化为统一结构，上游不接触 akshare 原始列名。
所有字段名漂移只影响本文件。

akshare 是同步阻塞库，调用方应用 ``asyncio.to_thread`` 包裹。

统一输出结构（DataFrame）：
- ETF 日线：columns = [date, open, high, low, close, volume]
- 基金净值：columns = [date, nav]
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal, Optional

import akshare as ak
import pandas as pd
from loguru import logger

from app.config import get_settings
from app.core.errors import DataSourceError, NotFoundError


InstrumentType = Literal["ETF", "FUND"]


def _to_date_str(dt: datetime) -> str:
    return dt.strftime("%Y%m%d")


def _date_range(years: int) -> tuple[str, str]:
    """返回 [起始日, 今日]，格式 YYYYMMDD。"""
    end = datetime.now()
    start = end - timedelta(days=365 * years)
    return _to_date_str(start), _to_date_str(end)


def classify_instrument(code: str) -> InstrumentType:
    """按代码前缀粗分类型（仅作前缀约定参考，非主流程依据）。

    约定：场内 ETF/股票代码以 1 或 5 开头（如 159915、510300）；
    开放式基金以 0 开头（如 000001）。

    主流程的标的类型由前端选项条的 ``type`` 参数指定，后端不再据此猜测；
    本函数仅保留供名称查询的先验推断等辅助场景使用。
    """
    code = code.strip()
    if code and code[0] in ("1", "5"):
        return "ETF"
    return "FUND"


def resolve_instrument(code: str, instrument_type: InstrumentType) -> tuple[str, InstrumentType, str]:
    """按指定类型尝试取名称。

    :param instrument_type: 标的类型（由前端选项条指定），名称查询先查对应类型表，
        失败再跨表兜底；返回的 type 直接沿用传入值。
    代码格式不合法抛 NotFoundError。

    返回 (code, type, name)。
    """
    code = code.strip()
    if not code or not code.isdigit() or len(code) != 6:
        raise NotFoundError("代码格式不正确，需为 6 位数字")

    primary_name = _etf_name if instrument_type == "ETF" else _fund_name
    fallback_name = _fund_name if instrument_type == "ETF" else _etf_name

    name = code
    try:
        name = primary_name(code)
    except Exception as exc:
        logger.debug("名称查询失败 code={}: {}", code, exc)
    if not name:
        # 跨表兜底：主表查不到时试另一张表
        try:
            name = fallback_name(code)
        except Exception:
            pass
    return code, instrument_type, name or code


def fetch_etf_daily(code: str, start: str, end: str) -> pd.DataFrame:
    """拉取 ETF 日线 OHLCV。

    数据源由配置 ``etf_data_source`` 控制：
    - ``sina`` — 新浪源，需带交易所前缀，返回全量历史后按区间过滤。
    - ``em``   — 东方财富源，已参数化起止日期，但可能被远端重置。

    :param code: 6 位代码
    :param start: YYYYMMDD
    :param end: YYYYMMDD
    :return: DataFrame[date, open, high, low, close, volume]，date 为 YYYY-MM-DD
    :raises NotFoundError: 代码无数据
    :raises DataSourceError: 数据源异常
    """
    source = get_settings().etf_data_source
    if source == "em":
        return _fetch_etf_daily_em(code, start, end)
    return _fetch_etf_daily_sina(code, start, end)


def _fetch_etf_daily_sina(code: str, start: str, end: str) -> pd.DataFrame:
    """新浪源 ETF 日线。

    新浪需带 sx + 6 位前缀，返回全量历史在 Pandas 中过滤区间。
    """
    sina_symbol = _to_sina_symbol(code)
    try:
        raw = ak.fund_etf_hist_sina(symbol=sina_symbol)
    except Exception as exc:
        logger.warning("新浪 ETF 行情拉取失败 code={}: {}", code, exc)
        raise DataSourceError("数据源请求失败") from exc

    if raw is None or raw.empty:
        raise NotFoundError()

    keep = ["date", "open", "high", "low", "close", "volume"]
    missing = [c for c in keep if c not in raw.columns]
    if missing:
        logger.error("新浪 ETF 返回字段缺失: {}，实际列={}", missing, list(raw.columns))
        raise DataSourceError("数据源返回字段不匹配")

    df = raw[keep].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["close"]).sort_values("date").reset_index(drop=True)

    start_iso = f"{start[:4]}-{start[4:6]}-{start[6:]}"
    end_iso = f"{end[:4]}-{end[4:6]}-{end[6:]}"
    df = df[(df["date"] >= start_iso) & (df["date"] <= end_iso)].reset_index(drop=True)
    return df


def _fetch_etf_daily_em(code: str, start: str, end: str) -> pd.DataFrame:
    """东方财富源 ETF 日线。

    fund_etf_hist_em 直接支持起止日期参数，但某些网络下可能被远端重置。
    """
    try:
        raw = ak.fund_etf_hist_em(
            symbol=code,
            period="daily",
            start_date=start,
            end_date=end,
            adjust="",
        )
    except Exception as exc:
        logger.warning("东方财富 ETF 行情拉取失败 code={}: {}", code, exc)
        raise DataSourceError("数据源请求失败") from exc

    if raw is None or raw.empty:
        raise NotFoundError()

    col_map = {
        "日期": "date",
        "开盘": "open",
        "收盘": "close",
        "最高": "high",
        "最低": "low",
        "成交量": "volume",
    }
    df = raw.rename(columns=col_map)
    missing = [c for c in col_map.values() if c not in df.columns]
    if missing:
        logger.error("东方财富 ETF 返回字段缺失: {}，实际列={}", missing, list(raw.columns))
        raise DataSourceError("数据源返回字段不匹配")

    df = df[list(col_map.values())].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.sort_values("date").reset_index(drop=True)
    return df


def _to_sina_symbol(code: str) -> str:
    """6 位代码转新浪带前缀符号：5 开头（沪市）→ sh，其余（深市 159 等）→ sz。"""
    return f"sh{code}" if code.startswith("5") else f"sz{code}"


def _is_parse_error(exc: BaseException) -> bool:
    """判断异常是否为上游返回非 JSON（HTML 错误页）导致的解析错误。

    这类错误通常是无效代码触发，应映射为 NotFoundError。
    """
    name = type(exc).__name__
    if name in ("JSParseException", "JSExceptionFactory", "SyntaxError", "ValueError"):
        return True
    msg = str(exc)
    return any(kw in msg for kw in ("SyntaxError", "Unexpected token", "<!doctype", "Expecting value"))


def fetch_fund_nav(code: str, start: str, end: str) -> pd.DataFrame:
    """拉取开放式基金单位净值序列。

    :return: DataFrame[date, nav]，date 为 YYYY-MM-DD
    :raises NotFoundError: 代码无数据
    :raises DataSourceError: 数据源异常
    """
    try:
        raw = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
    except Exception as exc:
        # 解析类错误（如 mini-racer JSParseException）通常是无效代码——上游返回 HTML 错误页
        if _is_parse_error(exc):
            logger.warning("akshare 基金净值解析失败（疑似无效代码）code={}: {}", code, exc)
            raise NotFoundError() from exc
        logger.warning("akshare 基金净值拉取失败 code={}: {}", code, exc)
        raise DataSourceError("数据源请求失败") from exc

    if raw is None or raw.empty:
        raise NotFoundError()

    # 列名：净值日期/单位净值/日增长率
    col_map = {"净值日期": "date", "单位净值": "nav"}
    df = raw.rename(columns=col_map)
    if "date" not in df.columns or "nav" not in df.columns:
        logger.error("akshare 基金净值返回字段不匹配: {}", list(raw.columns))
        raise DataSourceError("数据源返回字段不匹配")

    df = df[["date", "nav"]].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df = df.dropna(subset=["nav"]).sort_values("date").reset_index(drop=True)

    # 区间过滤：无新数据返回空 df
    start_iso = f"{start[:4]}-{start[4:6]}-{start[6:]}"
    end_iso = f"{end[:4]}-{end[4:6]}-{end[6:]}"
    df = df[(df["date"] >= start_iso) & (df["date"] <= end_iso)].reset_index(drop=True)
    return df


def _etf_name(code: str) -> Optional[str]:
    """从 ETF 基础信息表取名称。失败返回 None。"""
    try:
        df = ak.fund_etf_category_sina(symbol="ETF基金")
    except Exception:
        return None
    if df is None or df.empty:
        return None
    # 新浪 ETF 列名含 代码/名称
    name_col = "名称" if "名称" in df.columns else df.columns[1]
    code_col = "代码" if "代码" in df.columns else df.columns[0]
    row = df[df[code_col].astype(str) == code]
    if not row.empty:
        return str(row.iloc[0][name_col])
    return None


def _fund_name(code: str) -> Optional[str]:
    """从开放式基金信息表取名称。失败返回 None。"""
    try:
        df = ak.fund_name_em()
    except Exception:
        return None
    if df is None or df.empty:
        return None
    # 列名：基金代码/基金简称/...
    code_col = "基金代码" if "基金代码" in df.columns else df.columns[0]
    name_col = "基金简称" if "基金简称" in df.columns else df.columns[1]
    row = df[df[code_col].astype(str) == code]
    if not row.empty:
        return str(row.iloc[0][name_col])
    return None


def fetch_trade_calendar() -> pd.DataFrame:
    """拉取 A 股交易日历。

    调用 ``ak.tool_trade_date_hist_sina()``，返回全量交易日（历史 + 未来若干年）。
    akshare 仅返回交易日，故规范化后 ``is_trade_day`` 恒为 1。

    :return: DataFrame[calendar_date, is_trade_day]，calendar_date 为 YYYY-MM-DD
    :raises DataSourceError: 数据源异常
    """
    try:
        raw = ak.tool_trade_date_hist_sina()
    except Exception as exc:
        logger.warning("交易日历拉取失败: {}", exc)
        raise DataSourceError("数据源请求失败") from exc

    if raw is None or raw.empty:
        raise DataSourceError("交易日历为空")

    # akshare 返回列名为 trade_date，类型为 datetime
    date_col = "trade_date" if "trade_date" in raw.columns else raw.columns[0]
    df = pd.DataFrame({
        "calendar_date": pd.to_datetime(raw[date_col]).dt.strftime("%Y-%m-%d"),
        "is_trade_day": 1,
    })
    df = df.dropna(subset=["calendar_date"]).drop_duplicates(
        subset=["calendar_date"]
    ).sort_values("calendar_date").reset_index(drop=True)
    return df
