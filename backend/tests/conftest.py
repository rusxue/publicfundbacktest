"""pytest 公共夹具。

每个测试用独立临时 SQLite 库，避免污染真实 data.db。通过环境变量
``DB_PATH`` 指向临时文件并清 ``get_settings`` 缓存，使配置生效。
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.config import get_settings
from app.core.db import init_db


@pytest.fixture
def tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """使用临时库并初始化表结构。返回库文件路径。"""
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_file))
    # 配置带 lru_cache，需清除以使新的 DB_PATH 生效
    get_settings.cache_clear()
    init_db()
    yield db_file
    get_settings.cache_clear()
