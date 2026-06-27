# MA 均线策略量化回测 — 后端开发规范

> **用途**：本文档是后端回测功能的设计契约与开发指引。前端已落地（配置页 + 回测结果页），本文档作为下次开发后端回测功能的起点，照此实现即可与前端联调。
>
> **状态**：前端已就绪，后端待开发。请求/响应模型以前端 `frontend/src/stores/backtest.ts` 与 `frontend/src/api/backtest.ts` 为契约基准。

## 1. 背景与范围

实现「收盘价 > MA 均线」单均线策略的回测引擎，支持 A/C 份额费率、阶梯赎回、锁仓冷却、非交易日兜底，输出净值/回撤曲线、技术指标、交易明细。策略规则与界面配置项见 [`docs/MA均线策略量化回测界面配置.md`](./MA均线策略量化回测界面配置.md)，本文档聚焦后端实现。

**不在范围**：前端改造（已完成）、多策略组合、实时回测、回测结果持久化（当前为请求级，结果存内存经 store 传递）。

## 2. 接口契约

### 2.1 接口

```
POST /api/v1/backtest/run
Content-Type: application/json
```

挂载点：`backend/app/api/v1/backtest.py`，在 `app/main.py` 以 `app.include_router(backtest_router, prefix="/api/v1")` 注册（与 `market_router` 并列）。

### 2.2 请求体

```json
{
  "code": "159915",
  "type": "ETF",
  "config": {
    "period": "weekly",
    "maPeriod": 5,
    "shareClass": "A",
    "aPurchaseFee": 0.15,
    "aManagementFee": 2.0,
    "cServiceFee": 0.5,
    "redemption": {
      "lt7": 1.5,
      "lt30": 0.75,
      "lt365": 0.5,
      "lt730": 0.25,
      "gte730": 0.0
    },
    "initialCapital": 10000,
    "lockupDays": 7,
    "buyDeviation": 0.0,
    "sellDeviation": 0.0,
    "closeRatio": 100,
    "startDate": "2023-06-26",
    "endDate": "2026-06-26"
  }
}
```

字段说明：

| 字段 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `code` | string | — | 6 位标的代码（必填） |
| `type` | `"ETF"` \| `"FUND"` | — | 标的类型（必填，复用行情接口语义） |
| `config.period` | `"daily"` \| `"weekly"` | `"weekly"` | K 线周期 |
| `config.maPeriod` | `5\|10\|20\|30\|60` | `5` | MA 均线周期 |
| `config.shareClass` | `"A"` \| `"C"` | `"A"` | 份额类别 |
| `config.aPurchaseFee` | number | `0.15` | A 类申购费率(%) |
| `config.aManagementFee` | number | `2.0` | A 类年化管理费(%) |
| `config.cServiceFee` | number | `0.5` | C 类年化销售服务费(%)；C 类申购费固定 0 |
| `config.redemption.lt7` | number | `1.5` | 持仓<7天赎回费率(%) |
| `config.redemption.lt30` | number | `0.75` | 7≤持仓<30天(%) |
| `config.redemption.lt365` | number | `0.5` | 30≤持仓<365天（A 类）(%) |
| `config.redemption.lt730` | number | `0.25` | 365≤持仓<730天（A 类）(%) |
| `config.redemption.gte730` | number | `0.0` | 持仓≥730天（A 类）(%) |
| `config.initialCapital` | number | `10000` | 初始本金(元) |
| `config.lockupDays` | number | `7` | 锁仓冷却期(自然日，买入后 N 天内禁止平仓) |
| `config.buyDeviation` | number | `0.0` | 买入价格偏离率(%) |
| `config.sellDeviation` | number | `0.0` | 卖出价格偏离率(%) |
| `config.closeRatio` | number | `100` | 平仓比例(占持仓%，0~100) |
| `config.startDate` | string | 近3年 | 起始日 `YYYY-MM-DD` |
| `config.endDate` | string | 今日 | 结束日 `YYYY-MM-DD` |

**固定逻辑（不由请求传入，引擎内置）**：
- 买入条件 = 收盘价 > MA 均线
- 信号判定日 = 每周五收盘
- 买入成交价 = 信号产生后下周一收盘价
- 卖出成交价 = 信号产生后下周一收盘价
- 持仓天数口径 = 自然日历天数（开仓成交日至平仓成交日，含周末/节假日）

### 2.3 成功响应（200）

```json
{
  "metrics": {
    "totalReturn": 42.36,
    "annualReturn": 12.18,
    "maxDrawdown": -8.74,
    "sharpe": 1.32,
    "tradeCount": 18,
    "winRate": 61.11,
    "avgHoldingDays": 52,
    "totalFee": 312.40
  },
  "curve": [
    {
      "date": "2023-06-26",
      "nav": 1.0000,
      "benchmark": 1.0000,
      "drawdown": 0.0,
      "benchmarkDrawdown": 0.0,
      "excess": 0.0
    }
  ],
  "trades": [
    {
      "seq": 1,
      "direction": "买入",
      "signalDate": "2023-07-07",
      "tradeDate": "2023-07-10",
      "price": 1.023,
      "shares": 9766,
      "amount": 10000.0,
      "holdingDays": null,
      "fee": null,
      "returnPct": null
    }
  ],
  "summary": {
    "netProfit": 4236.0,
    "totalFee": 312.40,
    "tradeCount": 18,
    "winRate": 61.11
  },
  "snapshot": {
    "code": "159915",
    "name": "创业板ETF",
    "type": "ETF",
    "period": "weekly",
    "maPeriod": 5,
    "shareClass": "A",
    "startDate": "2023-06-26",
    "endDate": "2026-06-26"
  }
}
```

字段语义：

- `metrics`：技术指标数字面板（8 项）。百分比类以「数值」表示（`42.36` 即 42.36%），正负号语义为红涨绿跌（正=盈利）。
  - `totalReturn` 总收益率(%)、`annualReturn` 年化收益率(%)、`maxDrawdown` 最大回撤(%,负值)、`sharpe` 夏普比率、`tradeCount` 交易次数、`winRate` 胜率(%)、`avgHoldingDays` 平均持仓天数、`totalFee` 手续费合计(元)。
- `curve`：逐 bar 净值/回撤曲线点，按时间升序。`nav`/`benchmark` 归一化为 1.0 起始；`drawdown`/`benchmarkDrawdown` 为负值百分比；`excess = nav - benchmark`。
- `trades`：交易明细，按成交日升序。买入行 `holdingDays/fee/returnPct` 为 `null`；卖出行填持仓天数、手续费、本次收益率。
- `summary`：表格置底汇总。`netProfit` 净收益(元)。
- `snapshot`：实际回测所用参数快照（结果页顶栏展示）。

### 2.4 错误响应

沿用统一结构 `{"detail": {"code", "message"}}`（见 `app/core/errors.py`）。回测新增/复用业务码：

| 场景 | HTTP | code | message |
| --- | --- | --- | --- |
| 标的代码格式不合法 | 404 | `NOT_FOUND` | 输入的代码不存在或无数据 |
| 标的区间无数据（库无缓存且拉取失败/无数据） | 404 | `NOT_FOUND` | 输入的代码不存在或无数据 |
| 数据源故障且本地无缓存 | 503 | `DATA_SOURCE_ERROR` | 数据源请求失败，且本地无缓存 |
| 回测区间无效（起≥止等） | 422 | `VALIDATION_ERROR` | 参数校验失败 |
| 回测计算异常 | 500 | `INTERNAL_ERROR` | 服务器内部错误 |

> 标的取数复用行情链路，因此 `NOT_FOUND`/`DATA_SOURCE_ERROR` 由 `kline_service` 自然抛出，回测层不重复造。

## 3. 回测引擎算法

引擎位于 `backend/app/services/backtest/engine.py`（或拆为 `engine.py` + `fees.py` + `metrics.py`）。核心流程：

```
取数(日线) → 按周期重采样 → 计算 MA → 逐 bar 信号扫描 → 兜底成交日 → 成交+费率 → 净值/回撤序列 → 指标 → 组装结果
```

### 3.1 取数（复用现有链路）

调用 `kline_service` 取该标的区间日线原始 DataFrame，**不经 MA、不经降级标记**，仅取 OHLCV/nav。建议为回测新增一个轻量入口，避免复用 `get_kline`（它会算 MA 并组装响应）：

- 新增 `kline_service.load_raw_daily(code, instrument_type, start, end) -> pd.DataFrame`：内部调用 `_load_local` + `_refresh`（增量刷新），返回含 `date/open/high/low/close/volume/nav` 的全量日线，并按 `start/end` 过滤。
- 复用 `_refresh` 的增量、节流、降级（`DataSourceError` 上抛、本地缓存降级）逻辑。
- 仍在 `asyncio.to_thread` 外可异步调用；引擎计算本身是 CPU 密集，建议在路由层用 `await asyncio.to_thread(engine.run, ...)` 包裹，避免阻塞事件循环。

基准列（MA 与信号基于哪一列）：
- ETF（任意周期）：`close`
- 基金周线：`close`（伪 K 线由 `resample_fund_weekly` 生成）
- 基金日线：`nav`（仅有净值）

> 基准列与 `kline_service.get_kline` 的 `base_col` 逻辑完全一致，引擎内提取为同一 helper 复用，避免漂移。

### 3.2 周期重采样

- `period=weekly`：调用 `resample.resample_weekly(df, instrument_type)`（已有，W-FRI 边界）。
- `period=daily`：直接用日线。

### 3.3 MA 计算

调用 `services.ma.compute_ma(df, base_col)`（已有，周期 5/10/20/30/60）。引擎**只取 `maPeriod` 对应那一列**（如 `ma5`）做信号判定。前 N-1 期 MA 为 `None`，对应 bar 不产生信号。

### 3.4 信号扫描与成交（核心）

对每个 bar（按时间升序），仅当 `maPeriod` 列在该 bar 有值时判定：

1. **信号判定**：若 `close > ma{maPeriod}`（基准列值 > MA），记该 bar 为「信号日」。
   - 周线模式：每个 bar 即一根周线，信号判定日固定为「该周末（周五）收盘」。
   - 日线模式：信号判定日为每个交易日，**但文档固定逻辑为「每周五收盘」**——日线模式下仍只在周五 bar 判定信号。实现：日线模式按 `date` 的星期过滤，仅周五 bar 进入信号判定。
2. **信号日兜底**（非交易日）：
   - 周线模式天然以周五为界，不存在「周五非交易日」问题（resample 的 W-FRI 已把该周归到周五标签；若整周无数据则无该 bar）。
   - 日线模式下若基准周五为非交易日（节假日），用 `calendar_service.last_trade_date_on_or_before(周五日期)` 取本周最后一个交易日作为信号判定日，以该日收盘价计算 MA 与信号。
3. **成交日**：信号产生后的「下周一收盘价」。
   - 成交日兜底：若下周一为非交易日，用 `calendar_service.last_trade_date_before(下下周一)`？——规范表述为「向后顺延至首个开盘交易日」，实现：从下周一起逐日向后，用 `calendar_service.is_trade_day(d)` 找首个交易日，取其收盘价。
   - 用 `calendar_service.is_trade_day` / `last_trade_date_on_or_before` 实现，**禁止自行推断交易日历**。
4. **买卖配对**：首个买入信号 → 建仓；其后首个卖出信号 → 平仓；循环。锁仓冷却期内（见 3.5）的卖出信号忽略，顺延到冷却期后的首个卖出信号。

### 3.5 成交价与费率

- 买入成交价 = 成交日收盘价 × (1 + `buyDeviation`/100)
- 卖出成交价 = 成交日收盘价 × (1 + `sellDeviation`/100)（`sellDeviation` 默认 0，文档示例 `-0%`，即允许负偏离）
- 平仓比例 `closeRatio`：卖出时按持仓份额 × `closeRatio/100` 平仓（默认 100% 全平）。部分平仓时需拆分多笔卖出明细。
- 锁仓冷却：买入成交日后 `lockupDays`（自然日）内禁止平仓；冷却期内的卖出信号忽略。

**费率（`services/backtest/fees.py`）**：

- **建仓（买入）**：
  - 申购费 = 成交金额 × `aPurchaseFee`/100（A 类）；C 类申购费固定 0。
  - 实际买入份额 = (成交金额 - 申购费) / 成交价。或按「金额→份额」口径：份额 = 成交金额 × (1 - 申购费率) / 成交价。
- **持仓期**：
  - A 类：管理费按年化 `aManagementFee`% 摊销，按持仓自然日折算扣减净值（或期末一次性扣除，二选一并文档化）。
  - C 类：销售服务费按年化 `cServiceFee`% 摊销，同上。
  - **建议**：管理费/服务费按「持仓天数 × 年化费率 / 365」从净值线性扣减，体现在 `curve.nav` 上，而非单笔交易费。
- **平仓（卖出）**：
  - 持仓天数 = 自然日（卖出成交日 - 买入成交日）。
  - 赎回费率按持仓天数查阶梯（A 类 5 档 / C 类 2 档 + ≥30 天自动 0）：
    - `<7` → `lt7`；`7≤<30` → `lt30`；`30≤<365` → `lt365`（A 类）；`365≤<730` → `lt730`（A 类）；`≥730` → `gte730`（A 类）。
    - C 类：`<7` → `lt7`；`7≤<30` → `lt30`；`≥30` → 0（固定，不读配置）。
  - 赎回费 = 卖出成交金额 × 赎回费率。
  - 卖出明细 `fee` 字段记该笔赎回费；买入明细 `fee` 字段记该笔申购费（前端表格「手续费」列）。

> 费率口径（金额→份额、管理费摊销方式）需在实现时确定并与前端表格字段对齐；若与本文档默认不一致，回头同步本文档。

### 3.6 净值/回撤序列（`curve`）

按每个 bar（与信号扫描同一时间轴）输出：

- `nav`：策略归一净值。起始 1.0，每段持仓期间按标的价格变动 + 管理费/服务费摊销调整；空仓期间净值不变（持有现金）。建议按「账户权益 / 初始本金」归一。
- `benchmark`：基准归一净值。买入持有策略（起始全仓买入，持有至期末）的归一净值，作对比。
- `drawdown`：策略回撤(%) = (当前 nav / 历史峰值 nav - 1) × 100，负值。
- `benchmarkDrawdown`：基准回撤(%)，同法。
- `excess`：`nav - benchmark`（归一差值，非百分比）。

### 3.7 技术指标（`metrics`，`services/backtest/metrics.py`）

| 指标 | 公式 |
| --- | --- |
| `totalReturn` | (期末账户权益 / 初始本金 - 1) × 100 |
| `annualReturn` | (1 + totalReturn/100)^(365/持仓自然日) - 1) × 100；不足 1 年时按实际天数年化 |
| `maxDrawdown` | min(drawdown 序列)（负值） |
| `sharpe` | 年化收益率 / 年化波动率（净值日收益的年化标准差，√252） |
| `tradeCount` | 完成的买卖对数 ×2，或按明细行数计（卖出行数即平仓次数） |
| `winRate` | 收益为正的卖出笔数 / 总卖出笔数 × 100 |
| `avgHoldingDays` | 各卖出笔持仓天数均值 |
| `totalFee` | 累计申购费 + 赎回费（元） |

- 无交易或数据不足时指标可为 `None`（前端 `—`）。
- 基准收益率未单独列出（前端指标面板未要求），如需可加在 `metrics` 扩展字段，前端忽略未知字段。

## 4. 新增/改动文件清单

```
backend/app/
├── api/v1/backtest.py            # 新增：POST /backtest/run 路由
├── schemas/backtest.py           # 新增：BacktestRequest/Config/RedemptionTiers/Response 等模型
├── services/
│   ├── kline_service.py          # 改动：新增 load_raw_daily(code,type,start,end) 供回测取数
│   └── backtest/                 # 新增包
│       ├── __init__.py
│       ├── engine.py             # 主流程：取数→重采样→MA→信号→成交→序列→指标→组装
│       ├── signals.py            # 信号扫描 + 兜底（依赖 calendar_service）
│       ├── fees.py               # 申购/赎回/管理费/服务费
│       └── metrics.py            # 指标与曲线计算
├── main.py                       # 改动：include_router(backtest_router)
└── config.py                     # 改动（可选）：回测相关可调参数（如无理必要不加）
backend/tests/
└── test_backtest.py              # 新增：引擎单元/集成测试
```

### 4.1 Pydantic 模型（`schemas/backtest.py`）

与前端 `stores/backtest.ts` 类型一一对应（字段名 camelCase 与前端一致，或用 Pydantic alias 映射）。建议用 `populate_by_name` + `alias` 兼容 camelCase 请求体，响应也输出 camelCase 以免前端二次适配。

关键模型：

- `RedemptionTiers`：`lt7/lt30/lt365/lt730/gte730`。
- `BacktestConfig`：含 `shareClass: Literal["A","C"]`、`maPeriod: Literal[5,10,20,30,60]`、`period: Literal["daily","weekly"]` 等；C 类时 `lt365/lt730/gte730` 字段允许缺省（前端仍发，后端忽略）。
- `BacktestRequest`：`code: str`、`type: Literal["ETF","FUND"]`、`config: BacktestConfig`。
- `BacktestMetrics / CurvePoint / TradeRow / BacktestSummary / BacktestSnapshot / BacktestResult`：响应模型，字段与前端契约一致。

校验：`code` 6 位数字、`startDate < endDate`、`closeRatio ∈ [0,100]`、各费率 ≥ 0、`initialCapital > 0`。校验失败由 FastAPI 自动 422（已统一处理为 `VALIDATION_ERROR`）。

### 4.2 路由（`api/v1/backtest.py`）

```python
from fastapi import APIRouter
from app.schemas.backtest import BacktestRequest, BacktestResult
from app.services.backtest.engine import run_backtest
import asyncio, time
from loguru import logger

router = APIRouter(prefix="/backtest", tags=["回测"])

@router.post("/run", response_model=BacktestResult, summary="运行 MA 均线策略回测")
async def run(req: BacktestRequest) -> BacktestResult:
    start = time.perf_counter()
    # 引擎为 CPU 密集，放线程池避免阻塞事件循环
    result = await asyncio.to_thread(run_backtest, req.code, req.type, req.config)
    logger.info("POST /backtest/run code={} type={} 耗时={:.1f}ms", req.code, req.type, (time.perf_counter()-start)*1000)
    return result
```

## 5. 复用的现有服务

| 复用项 | 来源 | 用途 |
| --- | --- | --- |
| 增量取数 + 降级 | `kline_service._refresh` / `_load_local` | 回测取数（新增 `load_raw_daily` 包装） |
| 周线重采样 | `resample.resample_weekly` | `period=weekly` |
| MA 计算 | `ma.compute_ma` | 取 `maPeriod` 列 |
| 交易日历 | `calendar_service.is_trade_day` / `last_trade_date_on_or_before` | 非交易日兜底 |
| 统一错误 | `core/errors.py` (`NotFoundError`/`DataSourceError`) | 标的/数据源错误 |
| 节流 | `services/throttle.throttle_remote` | 取数时防封（已在 `_refresh` 内） |

**禁止**：在回测引擎里重写交易日历推断、重写 MA、重写取数——全部走现有服务，保证与行情链路一致。

## 6. 测试要点（`tests/test_backtest.py`）

复用 `tests/` 现有 fixture（httpx + ASGI，参考现有 market 接口测试）：

1. **信号与成交日**：构造一段已知 K 线，断言信号日=周五、成交日=下一交易日、成交价=成交日收盘价（含偏离率）。
2. **非交易日兜底**：构造周五为节假日的场景，断言信号判定日回退到本周最后交易日；下周一为节假日时断言顺延到首个交易日（依赖 `calendar_service` mock 或真实日历）。
3. **费率阶梯**：构造持仓 5/20/100/400/800 天的卖出，断言赎回费率命中正确档位；C 类 ≥30 天断言 0。
4. **锁仓冷却**：买入后 7 天内的卖出信号被忽略，冷却期外首个卖出信号才平仓。
5. **指标**：构造全涨/全跌序列，断言 `totalReturn`/`maxDrawdown`/`winRate` 符号与值。
6. **API 集成**：`POST /backtest/run` 返回结构含 `metrics/curve/trades/summary/snapshot`；无效 code → 404 `NOT_FOUND`；起≥止 → 422。
7. **幂等/性能**：同一请求两次结果一致；冷启动取数后命中本地缓存的二次请求耗时应大幅下降（复用 `_refresh` 新鲜度判断）。

## 7. 与前端的契约核对

- 请求/响应字段名以 `frontend/src/stores/backtest.ts`（`BacktestConfig`/`BacktestResult` 等 interface）与 `frontend/src/api/backtest.ts`（`runBacktest` 发 `{code, type, config}`）为准。
- 前端 `BacktestChart` 消费 `curve`：净值模式用 `nav/benchmark/excess`，回撤模式用 `drawdown/benchmarkDrawdown`，买卖点用 `trades.tradeDate/price`。确保这些字段名与后端输出**完全一致**。
- 前端 `TradeTable` 表格列：`seq/direction/signalDate/tradeDate/price/shares/amount/holdingDays/fee/returnPct`，汇总行用 `summary.netProfit/totalFee/winRate/tradeCount`。
- 前端导出 CSV/Excel 在前端生成，后端无需提供导出接口。

## 8. 开放问题（实现前需敲定）

1. **管理费/服务费摊销口径**：线性按日扣净值 vs 期末一次性扣。建议线性，需在 `fees.py` 文档化并同步本文档。
2. **部分平仓（`closeRatio<100`）的份额追踪**：需维护「持仓批次」队列（FIFO），每批独立算持仓天数与赎回档位。默认 100% 可简化为单批。
3. **基准净值定义**：买入持有 vs 标的本身归一价格。建议「同时段买入持有，同样扣除管理费」以公平对比。
4. **日线模式信号频率**：文档固定「每周五收盘」——日线模式下是否真的只周五判定？与用户确认（当前文档与前端配置页说明一致：信号判定日固定每周五）。
5. **夏普无风险利率**：默认 0，如需可加配置。
6. **回测结果是否持久化**：当前请求级，刷新结果页需重跑。若要持久化，新增 `backtest_results` 表 + GET 接口，属后续迭代。

## 9. 开发顺序建议

1. `schemas/backtest.py` 模型 + `api/v1/backtest.py` 路由壳（返回 mock 数据）→ 前端联调通联通。
2. `kline_service.load_raw_daily` → 引擎取数打通。
3. `engine.py` 信号 + 兜底 + 成交（无费率）→ `trades`/`curve` 基本正确。
4. `fees.py` 费率 → `metrics.py` 指标。
5. `tests/test_backtest.py` 全量用例。
6. 同步本文档第 8 节开放问题的最终决策。
