/**
 * 行情 API 封装。
 */
import axios from 'axios'

export interface Instrument {
  code: string
  name: string
  type: 'ETF' | 'FUND'
}

export interface KlineItem {
  date: string
  open: number | null
  high: number | null
  low: number | null
  close: number | null
  volume: number | null
  nav: number | null
  ma5: number | null
  ma10: number | null
  ma20: number | null
  ma30: number | null
  ma60: number | null
}

export interface KlineResponse {
  instrument: Instrument
  is_degraded: boolean
  klines: KlineItem[]
}

export type Period = 'daily' | 'weekly'

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

/** 统一错误信息提取 */
export function extractError(err: unknown): string {
  const detail = (err as any)?.response?.data?.detail
  if (detail?.message) return detail.message
  if (typeof detail === 'string') return detail
  if ((err as any)?.message) return (err as any).message
  return '网络异常，请稍后重试'
}

export async function fetchKline(
  code: string,
  period: Period,
): Promise<KlineResponse> {
  const { data } = await http.get<KlineResponse>(
    `/market/kline/${code}`,
    { params: { period } },
  )
  return data
}
