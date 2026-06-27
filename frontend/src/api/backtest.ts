/**
 * 回测 API 封装（预留：后端接口未定时，前端先以契约型封装）。
 * 错误结构沿用行情接口统一格式 { detail: { code, message } }。
 */
import axios from 'axios'
import type { BacktestConfig, BacktestResult } from '@/stores/backtest'
import type { Instrument } from '@/api/kline'

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
})

/** 从统一错误结构提取中文文案 */
export function extractBacktestError(err: unknown): string {
  const detail = (err as any)?.response?.data?.detail
  if (detail?.message) return detail.message
  if (typeof detail === 'string') return detail
  if ((err as any)?.message) return (err as any).message
  return '回测请求异常，请稍后重试'
}

/**
 * 提交回测。
 * @param instrument 回测标的（来自 market store 当前选中）
 * @param config 回测参数
 * @param signal 支持取消
 */
export async function runBacktest(
  instrument: Instrument,
  config: BacktestConfig,
  signal?: AbortSignal,
): Promise<BacktestResult> {
  const { data } = await http.post<BacktestResult>(
    '/backtest/run',
    {
      code: instrument.code,
      type: instrument.type,
      config,
    },
    { signal },
  )
  return data
}
