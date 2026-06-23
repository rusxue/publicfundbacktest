# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# rule
-  交互、文档和注释均使用中文


## 项目状态

全新项目。当前仓库仅含 `PRD.md`(需求与架构文档,中文)与近乎空白的 `README.md`,尚无任何应用代码。下文架构为 `PRD.md` 中规划的**设计蓝图**——以 `PRD.md` 为唯一事实来源,代码须与其保持一致;设计演进时需同步更新 PRD。

产品定位:基金/ETF 行情可视化与量化分析系统,个人投资辅助工具。PRD 以中文撰写,面向用户的文案与错误信息(如 `输入的代码不存在或无数据`)也使用中文。

## 架构(规划中)

前后端分离的 Monorepo:

- **backend/** — Python 3.10+（uv 管理依赖），FastAPI(异步 API、自动 OpenAPI 文档)、Pydantic v2(校验)、Pandas(计算)、Loguru(日志)。存储用 SQLite(WAL 模式)。数据源为 akshare。
- **frontend/** — Vue 3(Composition API)、Vite、TailwindCSS、Pinia。图表库为 **Klinecharts**(原生支持移动端触摸与 MA 叠加)。
- **scripts/run_dev.py** — 一键同时拉起 uvicorn(8000)与 vite(5173),Ctrl+C 统一终止。
- **docs/** — 文档。

规划的后端包结构:
```
backend/app/{main.py, config.py, api/, core/, services/, models/, schemas/}
backend/{tests/, data/ (data.db), logs/, pyproject.toml}
```

### 关键设计决策(来自 PRD——无充分理由不要偏离)

- **存储与计算分离**:SQLite(`klines` 表,`(code, date)` 复合主键,`INSERT OR REPLACE` 幂等写入)只存**原始日线**数据。周线重采样与 MA 计算在从库中取出后于 **Pandas 内存**中完成,而非用 SQL——保证计算高效且易于单元测试。
- **MA 由后端预计算**，随 OHLCV 一并返回。MA 周期为 5/10/20/30/60（`ma5`/`ma10`/`ma20`/`ma30`/`ma60`）。前端零计算。基准列：ETF（任意周期）与基金周线基于 `close`；开放式基金日线仅有净值，基于 `nav` 计算。前 N-1 期的 MA 为 `null`；图表库遇 `null` 须断线(不得前向填充)。
- **基金数据处理**：开放式基金日线返回单位净值 `nav`（OHLCV 为 null），前端绘净值折线；基金周线由日净值按金融标准重采样为伪 K 线（开=首日净值、收=末日净值、高/低=区间极值、volume=null）。ETF 用真实 OHLCV 蜡烛图。
- **增量数据更新**:优先读本地库;无数据拉取近 3 年全量,否则只拉增量。写入幂等。数据源请求间隔可配置(默认 **1.5s**)以防 IP 封禁——任何拉取循环都须遵守。
- **降级策略**:上游数据源不可用时,返回本地缓存并在响应中置 `is_degraded: true`,前端提示"数据可能非最新"。
- **配置管理**:所有参数走 `.env` / 配置文件——禁止硬编码。
- **本地"生产"模式**:`npm run build` → `frontend/dist`,由 FastAPI 挂载 `StaticFiles` 托管。单条 `uvicorn app.main:app --port 8000` 同时提供 API 与 UI。开发期 Vite Proxy(`/api` → 后端)消除跨域。

### API 契约

主接口:`GET /api/v1/market/kline/{code}?period=daily|weekly`

成功响应(200):
```json
{
  "instrument": {"code": "159915", "name": "创业板ETF", "type": "ETF"},
  "is_degraded": false,
  "klines": [{"date": "...", "open": ..., "high": ..., "low": ..., "close": ..., "volume": ..., "nav": null, "ma5": ..., "ma10": ..., "ma20": ..., "ma30": ..., "ma60": null}]
}
```

统一错误结构(所有错误):
```json
{"detail": {"code": "<业务码>", "message": "<面向用户的中文提示>"}}
```
| 场景 | HTTP | `code` |
| --- | --- | --- |
| 代码不存在/无数据 | 404 | `NOT_FOUND` |
| 数据源故障且本地无缓存 | 503 | `DATA_SOURCE_ERROR` |
| 参数校验错误 | 422 | `VALIDATION_ERROR` |

### 前端交互约束(来自 PRD)

- 深色主题(黑色/深灰背景)。
- 桌面端双栏:左侧边栏(搜索 + 标的列表,含代码/名称/当前价/涨跌幅,红涨绿跌),右侧主区(信息卡片 + K 线图)。移动端自动转为上下布局。
- 搜索历史默认显示最近 5 条;可加星标移入可手动排序的星标列表。
- 图表:OHLCV 蜡烛图 + MA5/10/20(日线默认显示 MA5/10/20/30/60 中的后三条)、成交量副图(绿涨红跌)、悬停十字准星、滚轮缩放、拖拽平移、点击图例隐藏/显示。
- 顶部控制栏:周期切换(1日 / 1周)、指标开关。

## 常用命令(代码就位后)

以下为 PRD 约定的命令;此全新仓库中可能尚未可用。

```bash
# 开发——同时启动后端(8000)+ 前端(5173)
python scripts/run_dev.py

# 后端测试(pytest)
cd backend && uv run pytest
cd backend && uv run pytest tests/path_to_test.py::test_name   # 单个测试

# 前端
cd frontend && npm run dev
cd frontend && npm run build

# 本地生产模式（单进程同供 API+UI）
cd frontend && npm run build
cd backend && uv run uvicorn app.main:app --port 8000
```

## 约定

- 保持 `PRD.md` 与代码同步——PRD 是设计契约,不是历史档案。
- 所有可调参数(端口、请求间隔、MA 周期、历史窗口)经 `backend/app/config.py` / 环境变量管理,严禁内联字面量。
- 按 Phase 2 可观测性要求,用 Loguru 将请求耗时 + 状态码按级别输出到文件。
