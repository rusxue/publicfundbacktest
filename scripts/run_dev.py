"""一键启动开发环境。

同时拉起：
- 后端 uvicorn（端口 8000，uv 管理）
- 前端 vite（端口 5173）

Ctrl+C 统一终止所有子进程。

用法：python scripts/run_dev.py
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"

BACKEND_PORT = os.environ.get("BACKEND_PORT", "8000")
FRONTEND_PORT = os.environ.get("FRONTEND_PORT", "5173")

procs: list[subprocess.Popen] = []


def start() -> list[subprocess.Popen]:
    """启动前后端子进程。"""
    # 后端：uv run python -m uvicorn（保证使用 backend 的虚拟环境）
    backend = subprocess.Popen(
        [
            "uv", "run", "python", "-m", "uvicorn", "app.main:app",
            "--reload",
            "--host", "0.0.0.0",
            "--port", BACKEND_PORT,
        ],
        cwd=str(BACKEND_DIR),
        shell=False,
    )
    # 前端：npm run dev
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(FRONTEND_DIR),
        shell=False,
        env={**os.environ, "BACKEND_PORT": BACKEND_PORT},
    )
    return [backend, frontend]


def terminate_all() -> None:
    """终止所有子进程。"""
    for p in procs:
        if p.poll() is None:
            try:
                p.terminate()
            except Exception:
                pass
    # 等待退出
    for p in procs:
        try:
            p.wait(timeout=5)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass


def main() -> None:
    print(f"[run_dev] 后端: http://localhost:{BACKEND_PORT}  (uvicorn)")
    print(f"[run_dev] 前端: http://localhost:{FRONTEND_PORT}  (vite)")
    print("[run_dev] 按 Ctrl+C 终止所有服务\n")

    procs.extend(start())

    def _on_sig(signum, _frame):
        print(f"\n[run_dev] 收到信号 {signum}，终止子进程…")
        terminate_all()
        sys.exit(0)

    # Windows 下 SIGINT 有效；SIGTERM 在部分平台不可用
    signal.signal(signal.SIGINT, _on_sig)
    if hasattr(signal, "SIGTERM"):
        try:
            signal.signal(signal.SIGTERM, _on_sig)
        except (ValueError, OSError):
            pass

    # 主循环：监控子进程，任一退出则全部终止
    try:
        while True:
            for p in procs:
                if p.poll() is not None:
                    print(f"[run_dev] 子进程 {p.args} 已退出，终止全部")
                    terminate_all()
                    return
            time.sleep(0.5)
    except KeyboardInterrupt:
        terminate_all()


if __name__ == "__main__":
    main()
