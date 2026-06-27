/**
 * 回测参数与结果状态。
 * 配置页写入 backtestConfig，结果页只读消费。
 * 回测页不支持就地改参（只展示结果）。
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Period } from '@/api/kline'

/** 份额类别：A 类 / C 类，单选互斥 */
export type ShareClass = 'A' | 'C'

/** 赎回费率档位（自然日历持仓天数） */
export interface RedemptionTiers {
  /** 持仓 < 7 天 */
  lt7: number
  /** 7 ≤ 持仓 < 30 天 */
  lt30: number
  /** 30 ≤ 持仓 < 365 天（A 类专用） */
  lt365: number
  /** 365 ≤ 持仓 < 730 天（A 类专用） */
  lt730: number
  /** 持仓 ≥ 730 天（A 类专用） */
  gte730: number
}

/** 完整回测配置（覆盖 docs/MA均线策略量化回测界面配置.md 全部字段） */
export interface BacktestConfig {
  // ① 策略参数
  period: Period // K 线周期：日线 / 周线
  maPeriod: 5 | 10 | 20 | 30 | 60 // MA 均线周期（单选，默认 5）
  // 买入条件=收盘价>MA、信号判定日=每周五、成交价=信号后下周一收盘 —— 均为固定逻辑，不存可编辑字段

  // ② 份额费率
  shareClass: ShareClass
  // A 类
  aPurchaseFee: number // 申购费率 %，默认 0.15
  aManagementFee: number // 年化管理费 %，默认 2.00
  // C 类
  cServiceFee: number // 年化销售服务费 %，默认 0.50（C 类申购费固定 0）
  // 赎回费率档位（A 类 5 档 / C 类 2 档 + ≥30 天自动 0）
  redemption: RedemptionTiers

  // ③ 公共回测参数
  initialCapital: number // 初始本金，默认 10000
  lockupDays: number // 锁仓冷却期（买入 N 天内禁止平仓），默认 7
  buyDeviation: number // 买入价格偏离率 %，默认 +0
  sellDeviation: number // 卖出价格偏离率 %，默认 -0
  closeRatio: number // 平仓比例（占初始持仓 %），默认 100
  startDate: string // 回测起始日期 YYYY-MM-DD，默认近 3 年
  endDate: string // 回测结束日期 YYYY-MM-DD，默认今日
}

/** 技术指标数字面板项 */
export interface BacktestMetrics {
  totalReturn: number | null // 总收益率 %
  annualReturn: number | null // 年化收益率 %
  maxDrawdown: number | null // 最大回撤 %
  sharpe: number | null // 夏普比率
  tradeCount: number | null // 交易次数
  winRate: number | null // 胜率 %
  avgHoldingDays: number | null // 平均持仓天数
  totalFee: number | null // 手续费合计（元）
}

/** 净值/回撤曲线点 */
export interface CurvePoint {
  date: string
  nav: number | null // 策略净值（归一化）
  benchmark: number | null // 基准净值
  drawdown: number | null // 策略回撤 %（负值）
  benchmarkDrawdown: number | null // 基准回撤 %
  excess: number | null // 超额收益（nav - benchmark）
}

/** 交易明细行 */
export interface TradeRow {
  seq: number
  direction: '买入' | '卖出'
  signalDate: string
  tradeDate: string
  price: number
  shares: number
  amount: number
  holdingDays: number | null // 买入行无
  fee: number | null
  returnPct: number | null
}

/** 回测结果（结果页消费） */
export interface BacktestResult {
  metrics: BacktestMetrics
  curve: CurvePoint[]
  trades: TradeRow[]
  // 结果摘要（表格汇总行用）
  summary: {
    netProfit: number
    totalFee: number
    tradeCount: number
    winRate: number
  }
  // 实际回测所用参数快照（结果页顶部展示）
  snapshot: {
    code: string
    name: string
    type: 'ETF' | 'FUND'
    period: Period
    maPeriod: number
    shareClass: ShareClass
    startDate: string
    endDate: string
  }
}

/** 默认配置（与文档默认值一致） */
function defaultConfig(): BacktestConfig {
  const end = new Date()
  const start = new Date(end)
  start.setFullYear(start.getFullYear() - 3)
  const fmt = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  return {
    period: 'weekly',
    maPeriod: 5,
    shareClass: 'A',
    aPurchaseFee: 0.15,
    aManagementFee: 2.0,
    cServiceFee: 0.5,
    redemption: {
      lt7: 1.5,
      lt30: 0.75,
      lt365: 0.5,
      lt730: 0.25,
      gte730: 0,
    },
    initialCapital: 10000,
    lockupDays: 7,
    buyDeviation: 0,
    sellDeviation: 0,
    closeRatio: 100,
    startDate: fmt(start),
    endDate: fmt(end),
  }
}

export const useBacktestStore = defineStore('backtest', () => {
  const config = ref<BacktestConfig>(defaultConfig())
  const result = ref<BacktestResult | null>(null)
  const loading = ref(false)
  const errorMsg = ref('')

  /** 当前标的（复用 market store 选中标的;回测页只读） */
  function resetConfig() {
    config.value = defaultConfig()
  }

  function setConfig(patch: Partial<BacktestConfig>) {
    config.value = { ...config.value, ...patch }
  }

  return {
    config,
    result,
    loading,
    errorMsg,
    resetConfig,
    setConfig,
  }
})
