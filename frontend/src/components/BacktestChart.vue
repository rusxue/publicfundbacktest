<script setup lang="ts">
/**
 * 回测核心可视化图表（ECharts 5）。
 * - 顶部 segment 切换：净值曲线 / 回撤曲线
 * - 净值曲线：策略净值 vs 基准净值双折线，可选超额收益柱副图，交易点 scatter 标注
 * - 回撤曲线：策略/基准回撤 area 折线（y 轴反向，向下为负），最大回撤 markPoint
 * - 切换 setOption 复用同一实例，保留 dataZoom 缩放区间
 * - 明暗双主题联动
 */
import { onMounted, onBeforeUnmount, ref, watch, computed } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart, BarChart, ScatterChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  AxisPointerComponent,
  MarkPointComponent,
  LegendComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { ComposeOption, ECharts } from 'echarts/core'
import type { LineSeriesOption, BarSeriesOption, ScatterSeriesOption } from 'echarts/charts'
import type {
  GridComponentOption,
  TooltipComponentOption,
  DataZoomComponentOption,
  AxisPointerComponentOption,
  MarkPointComponentOption,
  LegendComponentOption,
} from 'echarts/components'
import { useMarketStore } from '@/stores/market'
import type { CurvePoint, TradeRow } from '@/stores/backtest'

echarts.use([
  LineChart,
  BarChart,
  ScatterChart,
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  AxisPointerComponent,
  MarkPointComponent,
  LegendComponent,
  CanvasRenderer,
])

type ChartOption = ComposeOption<
  | LineSeriesOption
  | BarSeriesOption
  | ScatterSeriesOption
  | GridComponentOption
  | TooltipComponentOption
  | DataZoomComponentOption
  | AxisPointerComponentOption
  | MarkPointComponentOption
  | LegendComponentOption
>

const props = defineProps<{
  curve: CurvePoint[]
  trades: TradeRow[]
}>()

const market = useMarketStore()
const chartRef = ref<HTMLDivElement | null>(null)
let chart: ECharts | null = null
let resizeObserver: ResizeObserver | null = null

type ChartType = 'nav' | 'drawdown'
const chartType = ref<ChartType>('nav')
const showExcess = ref(true)

const isDark = computed(() => market.theme === 'dark')
const axisColor = computed(() => (isDark.value ? '#262629' : '#e5e7eb'))
const textColor = computed(() => (isDark.value ? '#9ca3af' : '#6b7280'))
const tipBg = computed(() => (isDark.value ? 'rgba(26,26,31,0.92)' : 'rgba(255,255,255,0.92)'))
const tipText = computed(() => (isDark.value ? '#f3f4f6' : '#0f172a'))

const COLOR_STRATEGY = '#ef4444'
const COLOR_BENCHMARK = '#3b82f6'
const COLOR_DOWN = '#22c55e'

function buildOption(): ChartOption {
  const dates = props.curve.map((p) => p.date)
  const nav = props.curve.map((p) => p.nav)
  const bench = props.curve.map((p) => p.benchmark)
  const dd = props.curve.map((p) => p.drawdown)
  const ddBench = props.curve.map((p) => p.benchmarkDrawdown)
  const excess = props.curve.map((p) => p.excess)

  const baseGrid = { left: 8, right: 16, top: 36, bottom: 48, containLabel: true }
  const dataZoom = [
    { type: 'inside', start: 0, end: 100 },
    {
      type: 'slider',
      start: 0,
      end: 100,
      height: 18,
      bottom: 10,
      borderColor: axisColor.value,
      textStyle: { color: textColor.value, fontSize: 10 },
    },
  ]
  const tooltip: TooltipComponentOption = {
    trigger: 'axis',
    axisPointer: { type: 'cross', lineStyle: { color: axisColor.value } },
    backgroundColor: tipBg.value,
    borderWidth: 1,
    borderColor: axisColor.value,
    textStyle: { color: tipText.value, fontSize: 12 },
  }

  if (chartType.value === 'nav') {
    const series: NonNullable<ChartOption['series']> = [
      {
        name: '策略净值',
        type: 'line',
        showSymbol: false,
        connectNulls: false,
        lineStyle: { width: 1.8, color: COLOR_STRATEGY },
        itemStyle: { color: COLOR_STRATEGY },
        data: nav,
      },
      {
        name: '基准净值',
        type: 'line',
        showSymbol: false,
        connectNulls: false,
        lineStyle: { width: 1.5, color: COLOR_BENCHMARK, type: 'dashed' },
        itemStyle: { color: COLOR_BENCHMARK },
        data: bench,
      },
    ]

    // 交易点 scatter（买卖标注）
    const buys = props.trades.filter((t) => t.direction === '买入').map((t) => [t.tradeDate, t.price])
    const sells = props.trades.filter((t) => t.direction === '卖出').map((t) => [t.tradeDate, t.price])
    series.push({
      name: '买入',
      type: 'scatter',
      symbol: 'triangle',
      symbolSize: 8,
      itemStyle: { color: COLOR_DOWN },
      data: buys,
    })
    series.push({
      name: '卖出',
      type: 'scatter',
      symbol: 'pin',
      symbolSize: 28,
      itemStyle: { color: COLOR_STRATEGY },
      data: sells,
    })

    // 超额收益柱副图
    const grids: GridComponentOption[] = [baseGrid]
    const xAxes: any[] = [
      {
        type: 'category',
        data: dates,
        boundaryGap: true,
        axisLine: { lineStyle: { color: axisColor.value } },
        axisTick: { show: false },
        axisLabel: { color: textColor.value, fontSize: 11 },
        splitLine: { show: false },
      },
    ]
    const yAxes: any[] = [
      {
        type: 'value',
        scale: true,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: textColor.value, fontSize: 11 },
        splitLine: { lineStyle: { color: axisColor.value } },
      },
    ]

    if (showExcess.value) {
      grids.push({ left: 8, right: 16, top: '62%', bottom: 48, containLabel: true })
      xAxes.push({
        type: 'category',
        gridIndex: 1,
        data: dates,
        boundaryGap: true,
        axisLine: { lineStyle: { color: axisColor.value } },
        axisTick: { show: false },
        axisLabel: { show: false },
      })
      yAxes.push({
        type: 'value',
        gridIndex: 1,
        scale: true,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: textColor.value, fontSize: 10 },
        splitLine: { show: false },
      })
      const baseGridAdjusted = { ...baseGrid, bottom: '38%' }
      grids[0] = baseGridAdjusted
      series.push({
        name: '超额收益',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        itemStyle: {
          color: (p: any) => (p.value >= 0 ? 'rgba(239,68,68,0.5)' : 'rgba(34,197,94,0.5)'),
        },
        data: excess,
      })
    }

    return {
      backgroundColor: 'transparent',
      animation: false,
      legend: {
        top: 4,
        textStyle: { color: textColor.value, fontSize: 11 },
        data: ['策略净值', '基准净值', '买入', '卖出', showExcess.value ? '超额收益' : ''],
      },
      grid: grids,
      xAxis: xAxes,
      yAxis: yAxes,
      dataZoom,
      tooltip,
      series,
    }
  }

  // 回撤曲线
  // 找最大回撤点
  let maxDD = 0
  let maxDDIdx = 0
  props.curve.forEach((p, i) => {
    if (p.drawdown != null && p.drawdown < maxDD) {
      maxDD = p.drawdown
      maxDDIdx = i
    }
  })

  return {
    backgroundColor: 'transparent',
    animation: false,
    legend: {
      top: 4,
      textStyle: { color: textColor.value, fontSize: 11 },
      data: ['策略回撤', '基准回撤'],
    },
    grid: baseGrid,
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: true,
      axisLine: { lineStyle: { color: axisColor.value } },
      axisTick: { show: false },
      axisLabel: { color: textColor.value, fontSize: 11 },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      inverse: true,
      max: 0,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: textColor.value, fontSize: 11, formatter: '{value}%' },
      splitLine: { lineStyle: { color: axisColor.value } },
    },
    dataZoom,
    tooltip: {
      ...tooltip,
      valueFormatter: (v: any) => (v == null ? '—' : `${Number(v).toFixed(2)}%`),
    },
    series: [
      {
        name: '策略回撤',
        type: 'line',
        showSymbol: false,
        connectNulls: false,
        lineStyle: { width: 1.8, color: COLOR_DOWN },
        itemStyle: { color: COLOR_DOWN },
        areaStyle: { color: 'rgba(34,197,94,0.2)' },
        data: dd,
        markPoint: maxDDIdx
          ? {
              data: [
                {
                  name: '最大回撤',
                  coord: [maxDDIdx, maxDD],
                  value: `最大回撤 ${maxDD.toFixed(2)}%`,
                  itemStyle: { color: COLOR_STRATEGY },
                  label: { color: '#fff', fontSize: 10 },
                },
              ],
            }
          : undefined,
      },
      {
        name: '基准回撤',
        type: 'line',
        showSymbol: false,
        connectNulls: false,
        lineStyle: { width: 1.5, color: COLOR_BENCHMARK, type: 'dashed' },
        itemStyle: { color: COLOR_BENCHMARK },
        areaStyle: { color: 'rgba(59,130,246,0.12)' },
        data: ddBench,
      },
    ],
  }
}

function render() {
  if (!chart) return
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
  () => [props.curve, props.trades, chartType.value, showExcess.value, isDark.value],
  () => render(),
)
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- 图表控制栏 -->
    <div class="flex flex-wrap items-center gap-3 px-3 py-1.5 text-xs border-b bg-bg-surface border-border">
      <span class="text-fg-muted font-medium">图表类型</span>
      <div class="flex items-center bg-bg-elevated rounded overflow-hidden border border-border">
        <button
          class="px-3 py-1 transition-colors duration-150 cursor-pointer"
          :class="chartType === 'nav' ? 'bg-accent text-white' : 'text-fg-muted hover:bg-bg-hover'"
          @click="chartType = 'nav'"
        >净值曲线</button>
        <button
          class="px-3 py-1 transition-colors duration-150 cursor-pointer"
          :class="chartType === 'drawdown' ? 'bg-accent text-white' : 'text-fg-muted hover:bg-bg-hover'"
          @click="chartType = 'drawdown'"
        >回撤曲线</button>
      </div>
      <label v-if="chartType === 'nav'" class="flex items-center gap-1.5 text-fg-muted cursor-pointer">
        <input type="checkbox" v-model="showExcess" class="accent-accent" />
        超额收益副图
      </label>
    </div>
    <div ref="chartRef" class="flex-1 min-h-0"></div>
  </div>
</template>
