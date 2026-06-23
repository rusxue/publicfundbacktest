# 基金/ETF 行情可视化与量化分析系统

个人投资辅助工具。前后端分离 Monorepo。

## 目录结构

```
publicfundbacktest/
├── backend/    # FastAPI + Pandas + akshare + SQLite，uv 管理依赖
├── frontend/   # Vue 3 + Vite + TailwindCSS + Pinia + klinecharts
├── scripts/run_dev.py  # 一键启动前后端
└── docs/
```

## 环境要求

- Python 3.10+（推荐 3.11）
- [uv](https://docs.astral.sh/uv/)（Python 依赖管理）
- Node.js 18+

## 快速开始

### 1. 配置

```bash
cp backend/.env.example backend/.env   # 按需修改参数
```

### 2. 开发模式（前后端热更新）

```bash
python scripts/run_dev.py
```

- 后端 API：http://localhost:8000，OpenAPI 文档 http://localhost:8000/docs
- 前端：http://localhost:5173（Vite Proxy 将 `/api` 转发至后端）
- Ctrl+C 统一终止

### 3. 本地生产模式（单进程同供 API+UI）

```bash
cd frontend && npm run build          # 输出 frontend/dist
cd backend && uv run uvicorn app.main:app --port 8000
# 浏览器访问 http://localhost:8000
```

## 主要接口

`GET /api/v1/market/kline/{code}?period=daily|weekly`

- 支持 ETF（OHLCV 蜡烛图）与开放式基金（日线净值折线 / 周线净值重采样伪 K 线）。
- 返回 MA5/10/20/30/60（前 N-1 期为 null，图表断线）。
- 数据源不可用时返回本地缓存并置 `is_degraded: true`；无缓存返回 503。

详见 [PRD.md](PRD.md)。
