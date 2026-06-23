"""移动平均线（MA）计算。

前 N-1 期置 None（图表断线，不前向填充）。
基准列选择：
- ETF / 基金周线：基于 close
- 基金日线：基于 nav（因 close 为 None）

MA 周期由配置 MA_PERIODS 决定（默认 5/10/20/30/60）。
当前 schema 固定输出 ma5/10/20/30/60。
"""
from __future__ import annotations

import pandas as pd


# schema 固定字段
MA_FIELDS = [5, 10, 20, 30, 60]


def compute_ma(df: pd.DataFrame, base_col: str) -> pd.DataFrame:
    """在 df 上计算 MA5/10/20/30/60，新增 ma5..ma60 列。

    :param df: 含 base_col 的 DataFrame
    :param base_col: 基准列名（close 或 nav）
    """
    if base_col not in df.columns:
        for p in MA_FIELDS:
            df[f"ma{p}"] = None
        return df

    series = df[base_col].astype(float)
    for p in MA_FIELDS:
        df[f"ma{p}"] = series.rolling(window=p, min_periods=p).mean()
        # 前 N-1 期为 NaN，保持 None（不前向填充）
        df[f"ma{p}"] = df[f"ma{p}"].where(df[f"ma{p}"].notna(), None)
    return df
