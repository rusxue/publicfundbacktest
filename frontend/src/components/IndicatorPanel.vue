<script setup lang="ts">
/**
 * 技术指标数字面板：8 项核心指标卡片。
 * 数字大字号 font-mono，涨跌着色 up/down，标签灰。
 */
import type { BacktestMetrics } from '@/stores/backtest'
import { computed } from 'vue'

const props = defineProps<{ metrics: BacktestMetrics | null }>()

interface Cell {
  label: string
  value: string
  tone: 'up' | 'down' | 'neutral'
}

const cells = computed<Cell[]>(() => {
  const m = props.metrics
  const fmt = (v: number | null, suffix = '', digits = 2) =>
    v == null ? '—' : `${v.toFixed(digits)}${suffix}`
  const tone = (v: number | null, invert = false): Cell['tone'] => {
    if (v == null) return 'neutral'
    if (v > 0) return invert ? 'down' : 'up'
    if (v < 0) return invert ? 'up' : 'down'
    return 'neutral'
  }
  if (!m) return Array(8).fill({ label: '', value: '—', tone: 'neutral' }) as Cell[]
  return [
    { label: '总收益率', value: fmt(m.totalReturn, '%'), tone: tone(m.totalReturn) },
    { label: '年化收益率', value: fmt(m.annualReturn, '%'), tone: tone(m.annualReturn) },
    { label: '最大回撤', value: fmt(m.maxDrawdown, '%'), tone: tone(m.maxDrawdown, true) },
    { label: '夏普比率', value: fmt(m.sharpe, ''), tone: tone(m.sharpe) },
    { label: '交易次数', value: m.tradeCount == null ? '—' : String(m.tradeCount), tone: 'neutral' },
    { label: '胜率', value: fmt(m.winRate, '%'), tone: tone(m.winRate) },
    { label: '平均持仓(天)', value: m.avgHoldingDays == null ? '—' : m.avgHoldingDays.toFixed(0), tone: 'neutral' },
    { label: '手续费合计(元)', value: m.totalFee == null ? '—' : m.totalFee.toFixed(2), tone: 'neutral' },
  ]
})
</script>

<template>
  <div class="grid grid-cols-2 md:grid-cols-4 gap-2 p-3">
    <div
      v-for="(c, i) in cells"
      :key="i"
      class="rounded border border-border bg-bg-surface px-3 py-2.5"
    >
      <div class="text-xs text-fg-muted">{{ c.label }}</div>
      <div
        class="text-2xl font-mono font-semibold mt-0.5"
        :class="c.tone === 'up' ? 'text-up' : c.tone === 'down' ? 'text-down' : 'text-fg'"
      >{{ c.value }}</div>
    </div>
  </div>
</template>
