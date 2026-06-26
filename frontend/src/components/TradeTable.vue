<script setup lang="ts">
/**
 * 交易明细表格：支持 CSV / Excel 导出（前端生成）。
 * 表头 sticky，移动端横向滚动，汇总行置底。
 * 空态/加载态(skeleton)。
 */
import { computed } from 'vue'
import { exportCSV, exportExcel } from '@/utils/export'
import type { TradeRow, BacktestResult } from '@/stores/backtest'
const props = defineProps<{
  trades: TradeRow[]
  summary: BacktestResult['summary'] | null
  loading?: boolean
}>()

const COLUMNS = [
  { key: 'seq', label: '序号' },
  { key: 'direction', label: '方向' },
  { key: 'signalDate', label: '信号日' },
  { key: 'tradeDate', label: '成交日' },
  { key: 'price', label: '成交价' },
  { key: 'shares', label: '份额' },
  { key: 'amount', label: '金额(元)' },
  { key: 'holdingDays', label: '持仓天数' },
  { key: 'fee', label: '手续费(元)' },
  { key: 'returnPct', label: '收益率' },
] as const

function fmt(v: number | null | undefined, digits = 2) {
  if (v == null || v === undefined) return '—'
  return `${v.toFixed(digits)}`
}

function dirClass(d: '买入' | '卖出') {
  // 红涨绿跌：买入(建仓)用绿、卖出(平仓)用红，与方向语义一致
  return d === '买入' ? 'text-down' : 'text-up'
}
function retClass(v: number | null) {
  if (v == null) return 'text-fg-faint'
  return v >= 0 ? 'text-up' : 'text-down'
}

const rows = computed(() => props.trades)
const isEmpty = computed(() => !props.loading && rows.value.length === 0)

function buildExportRows(): (string | number | null)[][] {
  const header = COLUMNS.map((c) => c.label)
  const body = rows.value.map((r) => COLUMNS.map((c) => (r as any)[c.key] ?? ''))
  const s = props.summary
  if (s) {
    body.push([])
    body.push([
      '汇总', '', '', '', '', '', s.netProfit.toFixed(2), '', s.totalFee.toFixed(2),
      `胜率 ${s.winRate.toFixed(2)}% · ${s.tradeCount} 笔`,
    ])
  }
  return [header, ...body]
}

const stamp = 'backtest-trades'

function onExportCSV() {
  exportCSV(stamp, buildExportRows())
}
function onExportExcel() {
  exportExcel(stamp, buildExportRows())
}
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- 表格工具栏 -->
    <div class="flex items-center justify-between px-3 py-1.5 border-b bg-bg-surface border-border">
      <span class="text-xs text-fg-muted font-medium">交易明细</span>
      <div class="flex items-center gap-2">
        <button
          class="flex items-center gap-1 px-2.5 py-1 text-xs text-fg-muted bg-bg-elevated rounded border border-border hover:bg-bg-hover transition-colors duration-150 cursor-pointer disabled:opacity-50"
          :disabled="isEmpty"
          @click="onExportCSV"
        >
          <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          导出 CSV
        </button>
        <button
          class="flex items-center gap-1 px-2.5 py-1 text-xs text-fg-muted bg-bg-elevated rounded border border-border hover:bg-bg-hover transition-colors duration-150 cursor-pointer disabled:opacity-50"
          :disabled="isEmpty"
          @click="onExportExcel"
        >
          <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          导出 Excel
        </button>
      </div>
    </div>

    <!-- 表格 -->
    <div class="flex-1 overflow-auto">
      <!-- skeleton -->
      <div v-if="loading" class="p-3 space-y-2">
        <div v-for="i in 6" :key="i" class="h-8 bg-bg-elevated rounded animate-pulse"></div>
      </div>

      <table v-else-if="!isEmpty" class="w-full text-xs font-mono">
        <thead class="sticky top-0 bg-bg-surface border-b border-border">
          <tr>
            <th
              v-for="c in COLUMNS"
              :key="c.key"
              class="px-2 py-1.5 text-left text-fg-muted font-medium whitespace-nowrap"
            >{{ c.label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(r, i) in rows"
            :key="r.seq"
            :class="i % 2 ? 'bg-bg-elevated/40' : ''"
          >
            <td class="px-2 py-1.5 text-fg-faint">{{ r.seq }}</td>
            <td class="px-2 py-1.5 font-medium" :class="dirClass(r.direction)">{{ r.direction }}</td>
            <td class="px-2 py-1.5 text-fg">{{ r.signalDate }}</td>
            <td class="px-2 py-1.5 text-fg">{{ r.tradeDate }}</td>
            <td class="px-2 py-1.5 text-fg">{{ fmt(r.price, 3) }}</td>
            <td class="px-2 py-1.5 text-fg">{{ r.shares.toFixed(0) }}</td>
            <td class="px-2 py-1.5 text-fg">{{ fmt(r.amount) }}</td>
            <td class="px-2 py-1.5 text-fg-muted">{{ r.holdingDays == null ? '—' : r.holdingDays }}</td>
            <td class="px-2 py-1.5 text-fg-muted">{{ r.fee == null ? '—' : fmt(r.fee) }}</td>
            <td class="px-2 py-1.5" :class="retClass(r.returnPct)">{{ r.returnPct == null ? '—' : (r.returnPct >= 0 ? '+' : '') + r.returnPct.toFixed(2) + '%' }}</td>
          </tr>
        </tbody>
        <tfoot v-if="summary" class="sticky bottom-0 bg-bg-surface border-t border-border font-medium">
          <tr>
            <td colspan="6" class="px-2 py-1.5 text-fg-muted">汇总</td>
            <td class="px-2 py-1.5 text-fg">{{ summary.netProfit.toFixed(2) }}</td>
            <td class="px-2 py-1.5 text-fg-muted"></td>
            <td class="px-2 py-1.5 text-fg-muted">{{ summary.totalFee.toFixed(2) }}</td>
            <td class="px-2 py-1.5 text-fg-muted">胜率 {{ summary.winRate.toFixed(2) }}%</td>
          </tr>
        </tfoot>
      </table>

      <!-- 空态 -->
      <div v-else class="flex items-center justify-center h-full text-sm text-fg-faint">
        暂无交易记录
      </div>
    </div>
  </div>
</template>
