<script setup lang="ts">
/**
 * K 线图组件(单图模式,ECharts 5)。
 * - K 线(蜡烛图/净值折线)为主图,MA 均线直接叠加在主图区域
 * - 无成交量副图、无 MA 副图,保持界面简洁
 * - 支持明暗双主题联动
 * - 基金日线:净值 area 折线
 * - MA 由后端预计算(ma5/10/20/30/60),前端零计算压力,遇 null 断线
 */
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { CandlestickChart, LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  AxisPointerComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { ComposeOption, ECharts } from 'echarts/core'
import type { CandlestickSeriesOption, LineSeriesOption } from 'echarts/charts'
import type {
  GridComponentOption,
  TooltipComponentOption,
  DataZoomComponentOption,
  AxisPointerComponentOption,
} from 'echarts/components'
import { useMarketStore } from '@/stores/market'
import type { KlineItem } from '@/api/kline'

echarts.use([
  CandlestickChart,
  LineChart,
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  AxisPointerComponent,
  CanvasRenderer,
])

type ChartOption = ComposeOption<
  | CandlestickSeriesOption
  | LineSeriesOption
  | GridComponentOption
  | TooltipComponentOption
  | DataZoomComponentOption
  | AxisPointerComponentOption
>

const store = useMarketStore()
const chartRef = ref<HTMLDivElement | null>(null)
let chart: ECharts | null = null
let resizeObserver: ResizeObserver | null = null

/** 缓存当前 K 线数据,供 tooltip formatter 闭包访问 */
let currentItems: KlineItem[] = []

// MA 可见性
const maToggles = ref<Record<string, boolean>>({
  MA5: true,
  MA10: true,
  MA20: true,
  MA30: true,
  MA60: true,
})

const MA_LABELS = [5, 10, 20, 30, 60] as const
const MA_COLORS: Record<string, string> = {
  MA5: '#ef4444',
  MA10: '#f59e0b',
  MA20: '#eab308',
  MA30: '#a855f7',
  MA60: '#3b82f6',
}
const MA_FIELDS: Record<string, keyof KlineItem> = {
  MA5: 'ma5',
  MA10: 'ma10',
  MA20: 'ma20',
  MA30: 'ma30',
  MA60: 'ma60',
}

/** 现值相对各 MA 的偏离率(%)。现值取末根 close??nav;MA 为 null 时偏离率为 null */
const maDeviations = computed(() => {
  const ks = store.current?.klines ?? []
  const last = ks[ks.length - 1]
  const price = last?.close ?? last?.nav ?? null
  return MA_LABELS.map((label) => {
    const ma = last ? (last[MA_FIELDS[`MA${label}`]] as number | null) : null
    let dev: number | null = null
    if (price != null && ma != null && ma !== 0) {
      dev = ((price - ma) / ma) * 100
    }
    return { label, dev }
  })
})

/** 基金日线 → 净值折线模式 */
function isLineMode(): boolean {
  const inst = store.currentInstrument
  return inst?.type === 'FUND' && store.period === 'daily'
}

/** 蜡烛图数据项 [open, close, low, high] */
function buildCandleData(items: KlineItem[]): [number, number, number, number][] {
  return items.map((k): [number, number, number, number] => {
    const c = k.close ?? k.nav ?? 0
    const o = k.open ?? c
    const h = k.high ?? c
    const l = k.low ?? c
    return [o, c, l, h]
  })
}

/** MA / 净值折线数据(null 保留以断线) */
function buildLineData(items: KlineItem[], field: keyof KlineItem): (number | null)[] {
  return items.map((k) => (k[field] as number | null) ?? null)
}

function buildOption(): ChartOption {
  const items = currentItems
  const dates = items.map((k) => k.date)
  const isDark = store.theme === 'dark'
  const lineMode = isLineMode()

  // 与 style.css CSS 变量一致的配色
  const axisColor = isDark ? '#262629' : '#e5e7eb'
  const textColor = isDark ? '#9ca3af' : '#6b7280'
  const tipBg = isDark ? 'rgba(26,26,31,0.92)' : 'rgba(255,255,255,0.92)'
  const tipText = isDark ? '#f3f4f6' : '#0f172a'

  const series: NonNullable<ChartOption['series']> = []

  if (lineMode) {
    // 基金日线:净值 area 折线
    series.push({
      name: '净值',
      type: 'line',
      showSymbol: false,
      smooth: false,
      connectNulls: false,
      lineStyle: { width: 1.5, color: '#ef4444' },
      itemStyle: { color: '#ef4444' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(239,68,68,0.25)' },
            { offset: 1, color: 'rgba(239,68,68,0.02)' },
          ],
        } as any,
      },
      data: buildLineData(items, 'nav'),
    })
  } else {
    // 蜡烛图(ETF / 基金周线伪 K 线),红涨绿跌(中国习惯)
    series.push({
      name: 'K线',
      type: 'candlestick',
      itemStyle: {
        color: '#ef4444', // 阳/涨
        color0: '#22c55e', // 阴/跌
        borderColor: '#ef4444',
        borderColor0: '#22c55e',
      },
      data: buildCandleData(items),
    })
  }

  // MA 均线(后端预计算,按开关过滤)
  for (const label of MA_LABELS) {
    if (!maToggles.value[`MA${label}`]) continue
    series.push({
      name: `MA${label}`,
      type: 'line',
      showSymbol: false,
      smooth: false,
      connectNulls: false,
      lineStyle: { width: 1.5, color: MA_COLORS[`MA${label}`] },
      data: buildLineData(items, MA_FIELDS[`MA${label}`]),
    })
  }

  return {
    backgroundColor: 'transparent',
    animation: false,
    grid: { left: 8, right: 12, top: 12, bottom: 40, containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: true,
      axisLine: { lineStyle: { color: axisColor } },
      axisTick: { show: false },
      axisLabel: { color: textColor, fontSize: 11 },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: textColor, fontSize: 11 },
      splitLine: { lineStyle: { color: axisColor } },
    },
    dataZoom: [
      { type: 'inside', start: 60, end: 100 },
      {
        type: 'slider',
        start: 60,
        end: 100,
        height: 18,
        bottom: 8,
        borderColor: axisColor,
        textStyle: { color: textColor, fontSize: 10 },
      },
    ],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross', lineStyle: { color: axisColor } },
      backgroundColor: tipBg,
      borderWidth: 1,
      borderColor: axisColor,
      textStyle: { color: tipText, fontSize: 12 },
      formatter: (params: any) => formatTooltip(params),
    },
    series,
  }
}

function formatTooltip(params: any): string {
  if (!Array.isArray(params) || !params.length) return ''
  const idx = params[0].dataIndex
  const k = currentItems[idx]
  if (!k) return ''

  const lines: string[] = []
  lines.push(`<div style="font-weight:600;margin-bottom:2px">${k.date}</div>`)
  const f = (v: number | null) => (v == null ? '—' : v.toFixed(3))

  if (isLineMode()) {
    if (k.nav != null) lines.push(`<span style="color:#9ca3af">净值</span> ${k.nav.toFixed(4)}`)
  } else {
    lines.push(`<span style="color:#9ca3af">开</span> ${f(k.open)}　<span style="color:#9ca3af">高</span> ${f(k.high)}`)
    lines.push(`<span style="color:#9ca3af">低</span> ${f(k.low)}　<span style="color:#9ca3af">收</span> ${f(k.close)}`)
  }

  const mas = MA_LABELS
    .filter((l) => maToggles.value[`MA${l}`])
    .map((l) => {
      const v = k[MA_FIELDS[`MA${l}`]] as number | null
      return `<span style="color:${MA_COLORS[`MA${l}`]}">MA${l}</span> ${v == null ? '—' : v.toFixed(3)}`
    })
  if (mas.length) lines.push(mas.join('　'))
  return lines.join('<br/>')
}

function render() {
  if (!chart) return
  currentItems = store.current?.klines ?? []
  chart.setOption(buildOption(), { notMerge: true })
}

onMounted(() => {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  render()

  resizeObserver = new ResizeObserver(() => chart?.resize())
  resizeObserver.observe(chartRef.value)
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
  chart?.dispose()
  chart = null
})

watch(
  () => [
    store.current,
    store.period,
    store.theme,
    maToggles.value.MA5,
    maToggles.value.MA10,
    maToggles.value.MA20,
    maToggles.value.MA30,
    maToggles.value.MA60,
  ],
  () => render(),
)
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- MA 图例开关栏 -->
    <div class="flex flex-wrap items-center gap-1 px-3 py-1.5 text-xs border-b bg-bg-surface border-border">
      <span class="text-fg-muted mr-1 font-medium">MA</span>
      <button
        v-for="label in MA_LABELS"
        :key="label"
        class="px-2 py-0.5 rounded transition-colors duration-150 font-mono cursor-pointer"
        :class="maToggles['MA' + label] ? 'text-white' : 'text-fg-faint line-through'"
        :style="maToggles['MA' + label] ? { backgroundColor: MA_COLORS['MA' + label] } : {}"
        @click="maToggles['MA' + label] = !maToggles['MA' + label]"
      >MA{{ label }}</button>
    </div>
    <!-- 现值相对各 MA 的偏离率(按均线颜色) -->
    <div
      v-if="maDeviations.length"
      class="flex flex-wrap items-center gap-x-3 gap-y-0.5 px-3 py-1 text-xs bg-bg-surface border-b border-border font-mono"
    >
      <span
        v-for="d in maDeviations"
        :key="d.label"
        :style="{ color: MA_COLORS['MA' + d.label] }"
      >MA{{ d.label }} {{ d.dev == null ? '—' : (d.dev >= 0 ? '+' : '') + d.dev.toFixed(2) + '%' }}</span>
    </div>
    <!-- 图表容器 -->
    <div ref="chartRef" class="flex-1 min-h-0"></div>
  </div>
</template>
