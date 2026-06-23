"""FastAPI 应用入口。

- 启动时初始化数据库、日志。
- 挂载 v1 API 路由。
- 生产模式（APP_ENV != dev）挂载 frontend/dist 静态资源，单进程同供 API+UI。
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.market import router as market_router
from app.config import get_settings
from app.core.db import init_db
from app.core.errors import register_error_handlers
from app.core.logger import get_logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：初始化日志与数据库。"""
    setup_logging()
    log = get_logger()
    init_db()
    log.info("应用启动完成：数据库已初始化")
    yield
    log.info("应用关闭")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="基金/ETF 行情系统",
        version="0.1.0",
        lifespan=lifespan,
    )

    # 开发模式允许跨域（Vite 直连后端兜底，主要仍走代理）
    if settings.is_dev:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[f"http://localhost:{settings.frontend_port}"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

    register_error_handlers(app)
    app.include_router(market_router, prefix="/api/v1")

    # 生产模式：挂载前端静态资源
    dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if not settings.is_dev and dist.exists():
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="frontend")
        get_logger().info("已挂载前端静态资源: {}", dist)

    return app


app = create_app()
