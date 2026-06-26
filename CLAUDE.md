# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# rule
- 交互、文档和注释均使用中文


## 项目状态

基金/ETF 行情可视化与量化分析系统,个人投资辅助工具。PRD 以中文撰写,面向用户文案与错误信息(如 `输入的代码不存在或无数据`)也使用中文。代码已落地核心链路(行情查询、增量更新、MA/周线计算、前后端联调);PRD 持续作为设计契约,代码须与其一致,设计演进时同步更新 PRD。

## 环境要求

- Python 3.10+(推荐 3.11),[uv](https://docs.astral.sh/uv/) 管理依赖
- Node.js 18+

## 架构

前后端分离的 Monorepo:

- **backend/** — Python 3.10+(uv 管理依赖),FastAPI(异步 API、自动 OpenAPI 文档)、Pydantic v2(校验)、Pandas(计算)、Loguru(日志)、akshare(数据源)。存储用 SQLite(WAL 模式)。
- **frontend/** — Vue 3(Composition API)、Vite、TailwindCSS、Pinia、axios。图表库为 **ECharts**(支持蜡烛图/折线、十字准星、缩放/平移、MA 叠加)。
- **scripts/run_dev.py** — 一键同时拉起 uvicorn(8000)与 vite(5173),Ctrl+C 统一终止。
- **docs/** — 文档。

后端包结构:
```
backend/app/{main.py, config.py, api/v1/market.py, core/{db,errors,logger}.py, services/{datasource,kline_service,ma,resample}.py, schemas/kline.py}
backend/{tests/, data/ (data.db), logs/, pyproject.toml, .env(.example)}
```

### 关键设计决策(来自 PRD——无充分理由不要偏离)

- **存储与计算分离**:SQLite `klines` 表(`(code, date)` 复合主键,`INSERT OR REPLACE` 幂等写入)只存**原始日线**数据。周线重采样与 MA 计算在从库中取出后于 **Pandas 内存**中完成(`services/resample.py`、`services/ma.py`),而非用 SQL。
- **MA 由后端预计算**(`services/ma.py`),随 OHLCV 一并返回。MA 周期为 5/10/20/30/60。前 N-1 期为 `None`(由 `rolling(min_periods=p)` 实现,不前向填充),图表库遇 null 须断线。基准列:`ETF` 与基金周线基于 `close`;开放式基金日线仅有净值,基于 `nav` 计算。
- **基金数据处理**:开放式基金日线返回单位净值 `nav`(OHLCV 为 null),前端绘净值折线;基金周线由日净值按金融标准重采样为伪 K 线(`resample_fund_weekly`:开=首日净值、收=末日净值、高/低=区间极值、volume=null)。ETF 周线用真实 OHLCV 重采样(`resample_etf_weekly`,W-FRI 边界)。
- **增量数据更新**(`kline_service._refresh`):优先读本地库;无数据拉近 3 年全量(`history_years`),否则从本地最新日期次日起只拉增量。写入幂等。数据源请求间隔可配置(默认 1.5s)以防 IP 封禁——任何拉取循环都须遵守。
- **降级策略**:上游数据源不可用时返回本地缓存并置 `is_degraded: true`,前端提示"数据可能非最新";无缓存抛 503。
- **配置管理**:所有参数走 `.env` / `app/config.py`(`pydantic-settings` 的 `Settings`,单例 `get_settings()` 带 `lru_cache`)——禁止硬编码。
- **本地"生产"模式**:`npm run build` → `frontend/dist`,由 FastAPI 在 `APP_ENV != dev` 时挂载 `StaticFiles` 托管。单条 `uvicorn app.main:app --port 8000` 同时提供 API 与 UI。开发期 Vite Proxy(`/api` → 后端)消除跨域。

### 后端数据流(关键)

`api/v1/market.py:fetch_kline` → `services/kline_service.get_kline`:
1. 按前端 `type` 查询参数确定标的类型(`etf`/`fund` → `ETF`/`FUND`),不再按代码前缀猜测。
2. 增量刷新本地库(`_refresh`)。akshare 同步阻塞,均经 `asyncio.to_thread` 包裹。
3. 严格按指定类型路由数据源,拉取无数据即返回 `NOT_FOUND`,不在 ETF/基金两类间回退。
4. 从库取全量日线 →(周线重采样)→ MA → 组装 `KlineResponse`。

**数据源适配器** `services/datasource.py` 是 akshare 字段名的唯一隔离层——上游只接触规范化后的 DataFrame(`ETF 日线:[date,open,high,low,close,volume]`,`基金净值:[date,nav]`)。ETF 行情源由 `etf_data_source` 配置切换:`sina`(新浪,需带 sh/sz 前缀,返回全量后按区间过滤)或 `em`(东方财富,参数化起止日期,但可能被远端重置)。akshare 对无效基金代码常抛 JS 解析异常(HTML 错误页),`_is_parse_error` 将其映射为 `NotFoundError`。

**错误处理** `core/errors.py`:业务异常基类 `BizError` 携带 `http_status/code/message`,统一处理器输出 `{"detail":{"code","message"}}`。三大业务码:`NOT_FOUND`(404)、`DATA_SOURCE_ERROR`(503)、`VALIDATION_ERROR`(422,FastAPI 校验失败)。未捕获异常兜底为 500 `INTERNAL_ERROR`。

### 前端结构

- `stores/market.ts`(Pinia)管理当前标的、周期、搜索历史(localStorage,最近 5 条)、星标列表(可手动排序)。`switchPeriod` 会重新拉取。
- `api/kline.ts` 封装 axios,`baseURL=/api/v1`,`extractError` 从统一错误结构提取中文文案。
- 组件:`KlineChart`、`InfoCard`、`Sidebar`、`TopBar`;视图 `MarketView`。

### API 契约

主接口:`GET /api/v1/market/kline/{code}?type=etf|fund&period=daily|weekly`

成功响应(200):
```json
{
  "instrument": {"code": "159915", "name": "创业板ETF", "type": "ETF"},
  "is_degraded": false,
  "klines": [{"date": "...", "open": ..., "high": ..., "low": ..., "close": ..., "volume": ..., "nav": null, "ma5": ..., "ma10": ..., "ma20": ..., "ma30": ..., "ma60": null}]
}
```

统一错误结构:`{"detail": {"code": "<业务码>", "message": "<中文提示>"}}`。详见上表。

### 前端交互约束(来自 PRD)

- 深色主题(黑色/深灰背景)。
- 桌面端双栏:左侧边栏(搜索 + 标的列表,含代码/名称/当前价/涨跌幅,红涨绿跌),右侧主区(信息卡片 + K 线图)。移动端自动转为上下布局。
- 搜索历史默认显示最近 5 条;可加星标移入可手动排序的星标列表。
- 图表:OHLCV 蜡烛图 + MA5/10/20/30/60、悬停十字准星、滚轮缩放、拖拽平移、点击图例隐藏/显示。基金日线绘净值折线,周线由日净值重采样为伪 K 线;无成交量副图、无 MA 副图,保持界面简洁。
- 顶部控制栏:周期切换(1日 / 1周)、指标开关。

## 常用命令

```bash
# 开发——同时启动后端(8000)+ 前端(5173)
python scripts/run_dev.py

# 后端测试(pytest)。dev 依赖需安装:cd backend && uv sync --extra dev
cd backend && uv run pytest
cd backend && uv run pytest tests/path_to_test.py::test_name   # 单个测试

# 后端单进程(开发期热更新)
cd backend && uv run python -m uvicorn app.main:app --reload --port 8000

# 前端
cd frontend && npm run dev
cd frontend && npm run build        # 输出 frontend/dist

# 本地生产模式(单进程同供 API+UI):先 build 前端,再设 APP_ENV=prod 跑 uvicorn
cd frontend && npm run build
cd backend && APP_ENV=prod uv run python -m uvicorn app.main:app --port 8000
# 浏览器访问 http://localhost:8000
```

## 约定

- 后端依赖在 `backend/pyproject.toml`;`[tool.uv] package = false`(非打包项目,仅管理依赖)。pytest 与 httpx 在 `dev` extra 中。
- 前端构建含 `vue-tsc -b` 类型检查;`@` 别名指向 `src`(`vite.config.ts` 与 `tsconfig.json`)。
- Vite Proxy 把 `/api` 转发到 `http://localhost:${BACKEND_PORT}`;后端在 dev 模式额外对 `localhost:5173` 开启 CORS 兜底。
- 保持 `PRD.md` 与代码同步——PRD 是设计契约,不是历史档案。
- 所有可调参数(端口、请求间隔、MA 周期、历史窗口、数据源)经 `backend/app/config.py` / 环境变量管理,严禁内联字面量。
- 按 Phase 2 可观测性要求,用 Loguru 将请求耗时 + 状态码按级别输出到文件(`core/logger.py`,按日滚动保留 14 天)。
