"""应用配置管理。

所有可调参数经 `.env` / 环境变量注入，禁止硬编码。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# backend/ 根目录（本文件位于 backend/app/config.py）
BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """全局配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 运行模式：dev / prod
    app_env: str = "dev"

    # 端口
    backend_port: int = 8000
    frontend_port: int = 5173

    # 数据库（相对 backend/ 工作目录）
    db_path: str = "data/data.db"

    # 日志
    log_dir: str = "logs"
    log_level: str = "INFO"

    # 数据源（akshare）
    data_source_interval: float = 1.5
    history_years: int = 3
    # ETF 行情源：sina（新浪，当前环境可用）/ em（东方财富，可能被重置）
    etf_data_source: str = "sina"

    # 交易日历
    trade_calendar_ttl_days: int = 7   # 交易日表新鲜度阈值，超过则重新拉取
    trade_close_time: str = "15:00"    # A 股收盘时间，收盘后 target 含今天

    # 计算参数
    ma_periods: str = "5,10,20,30,60"

    @property
    def ma_periods_list(self) -> list[int]:
        """解析 MA 周期列表。"""
        return [int(p) for p in self.ma_periods.split(",") if p.strip()]

    @property
    def db_file(self) -> Path:
        """数据库文件绝对路径，自动创建父目录。"""
        p = Path(self.db_path)
        if not p.is_absolute():
            p = BACKEND_ROOT / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def log_dir_path(self) -> Path:
        """日志目录绝对路径。"""
        p = Path(self.log_dir)
        if not p.is_absolute():
            p = BACKEND_ROOT / p
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def is_dev(self) -> bool:
        return self.app_env.lower() == "dev"


@lru_cache
def get_settings() -> Settings:
    return Settings()
