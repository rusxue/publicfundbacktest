"""统一错误处理。

所有错误返回统一结构：{"detail": {"code": "<业务码>", "message": "<中文提示>"}}。
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger


class BizError(Exception):
    """业务异常基类。"""

    http_status: int = 400
    code: str = "BIZ_ERROR"
    message: str = "业务错误"

    def __init__(self, message: str | None = None, code: str | None = None):
        self.message = message or self.message
        self.code = code or self.code
        super().__init__(self.message)


class NotFoundError(BizError):
    http_status = 404
    code = "NOT_FOUND"
    message = "输入的代码不存在或无数据"


class DataSourceError(BizError):
    http_status = 503
    code = "DATA_SOURCE_ERROR"
    message = "数据源请求失败，且本地无缓存"


def _detail(code: str, message: str) -> dict:
    return {"detail": {"code": code, "message": message}}


def register_error_handlers(app: FastAPI) -> None:
    """注册统一异常处理。"""

    @app.exception_handler(BizError)
    async def _biz_handler(_: Request, exc: BizError):
        logger.warning("业务异常 code={} msg={}", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.http_status,
            content=_detail(exc.code, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError):
        logger.info("参数校验失败: {}", exc.errors())
        return JSONResponse(
            status_code=422,
            content=_detail("VALIDATION_ERROR", "参数校验失败"),
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(_: Request, exc: Exception):
        logger.exception("未处理异常: {}", exc)
        return JSONResponse(
            status_code=500,
            content=_detail("INTERNAL_ERROR", "服务器内部错误"),
        )
