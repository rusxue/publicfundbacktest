"""Loguru 日志配置。

按 Phase 2 可观测性要求：请求耗时 + 状态码按级别输出到文件。
"""
from __future__ import annotations

import sys

from loguru import logger

from app.config import get_settings


def setup_logging() -> None:
    """初始化日志：控制台 + 滚动文件。"""
    settings = get_settings()
    logger.remove()

    fmt = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    # 控制台
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format=fmt,
        colorize=True,
    )

    # 文件：按日滚动，保留 14 天
    log_file = settings.log_dir_path / "app.log"
    logger.add(
        str(log_file),
        level=settings.log_level,
        format=fmt,
        rotation="00:00",
        retention="14 days",
        encoding="utf-8",
        enqueue=True,
    )


def get_logger():
    """返回配置好的 logger。"""
    return logger
