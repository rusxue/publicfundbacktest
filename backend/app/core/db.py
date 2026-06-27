"""SQLite 数据库初始化。

启用 WAL 模式支持读写并发。仅存储原始日线数据，周线与 MA 在 Pandas 内存计算。
表 klines 采用 (code, date) 复合主键，INSERT OR REPLACE 实现幂等写入。
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.config import get_settings


_CREATE_KLINES = """
CREATE TABLE IF NOT EXISTS klines (
    code           TEXT    NOT NULL,
    date           TEXT    NOT NULL,
    open           REAL,
    high           REAL,
    low            REAL,
    close          REAL,
    volume         REAL,
    nav            REAL,
    instrument_type TEXT   NOT NULL,
    name           TEXT,
    PRIMARY KEY (code, date)
);
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_klines_code_date ON klines (code, date);
"""

_CREATE_TRADE_CALENDAR = """
CREATE TABLE IF NOT EXISTS trade_calendar (
    calendar_date TEXT    NOT NULL PRIMARY KEY,  -- 自然日 YYYY-MM-DD
    is_trade_day  INTEGER NOT NULL               -- 0/1（akshare 仅返回交易日，入库恒为 1）
);
"""

_CREATE_META = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT NOT NULL PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    """建立连接并设置 WAL 模式。"""
    settings = get_settings()
    db_file = settings.db_file
    conn = sqlite3.connect(
        str(db_file),
        timeout=30.0,
        isolation_level=None,  # 自动提交
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    """初始化表结构。应用启动时调用一次。"""
    with _connect() as conn:
        conn.execute(_CREATE_KLINES)
        conn.execute(_CREATE_INDEX)
        conn.execute(_CREATE_TRADE_CALENDAR)
        conn.execute(_CREATE_META)


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """获取数据库连接上下文管理器。"""
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()
