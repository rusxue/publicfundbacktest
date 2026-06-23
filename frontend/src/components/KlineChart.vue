<script setup lang="ts">
/**
 * K 线图组件。
 * - ETF（任意周期）与基金周线：蜡烛图 + 成交量副图 + MA 叠加。
 * - 基金日线：净值折线（nav）+ MA 叠加（candle.type=area）。
 */
import { onMounted, onBeforeUnmount, ref, watch, computed } from 'vue'
import {
  init,
  dispose,
  type Chart,
  type KLineData,
} from 'klinecharts'
import { useMarketStore } from '@/stores/market'
import type { KlineItem } from '@/api/kline'

const store = useMarketStore()
const chartRef = ref<HTMLDivElement | null>(null)
let chart: Chart | null = null

// MA 总开关
const maVisible = ref(true)
const maToggles = ref<Record<string, boolean>>({
  MA5: true,
  MA10: true,
  MA20: true,
  MA30: true,
  MA60: true,
})

// 基金日线 → 净值折线模式
const isLineMode = computed(() => {
  const inst = store.currentInstrument
  return inst?.type === 'FUND' && store.period === 'daily'
})

function ts(date: string): number {
  return new Date(date + 'T00:00:00').getTime()
}

function buildKLineData(items: KlineItem[]): KLineData[] {
  return items.map((k) => {
    const c = k.close ?? k.nav ?? 0
    // 基金日线无 OHLC，用 nav 填充各字段以构成 area 折线
    const o = k.open ?? c
    const h = k.high ?? c
    const l = k.low ?? c
    return {
      timestamp: ts(k.date),
      open: o,
      high: h,
      low: l,
      close: c,
      volume: k.volume ?? undefined,
    }
  })
}

function render() {
  if (!chart) return
  const resp = store.current
  if (!resp) {
    chart.applyNewData([])
    return
  }
  const items = resp.klines

  // 主图类型：基金日线用 area（净值折线），其余用 candle
  const candleType = isLineMode.value ? 'area' : 'candle_solid'
  chart.setStyles({ candle: { type: candleType } } as any)

  chart.applyNewData(buildKLineData(items))

  // 成交量副图（基金日线无成交量，仍可显示为空）
  if (!isLineMode.value) {
    chart.createIndicator('VOL', false, { id: 'pane_vol' })
  }

  // MA 主图叠加：清除旧的自定义 MA 后重建
  chart.removeIndicator('pane_main', 'MA')
  if (maVisible.value) {
    const periods = [5, 10, 20, 30, 60]
    for (const p of periods) {
      if (!maToggles.value[`MA${p}`]) continue
      chart.createIndicator(
        {
          name: 'MA',
          calcParams: [p],
          shouldOhlc: false,
        } as any,
        true,
        { id: 'pane_main' },
      )
    }
  }
}

function toggleMa(name: string) {
  maToggles.value[name] = !maToggles.value[name]
  render()
}

onMounted(() => {
  if (chartRef.value) {
    chart = init(chartRef.value, {
      styles: {
        grid: {
          horizontal: { color: '#1f1f26' },
          vertical: { color: '#1f1f26' },
        },
        candle: {
          type: 'candle_solid',
          bar: {
            upColor: '#ef4444',
            downColor: '#22c55e',
            noChangeColor: '#888',
            upBorderColor: '#ef4444',
            downBorderColor: '#22c55e',
            upWickColor: '#ef4444',
            downWickColor: '#22c55e',
          },
        },
        xAxis: { color: '#666' },
        yAxis: { color: '#666' },
      },
    } as any)
    render()
  }
})

onBeforeUnmount(() => {
  if (chartRef.value) dispose(chartRef.value)
})

watch(
  () => [store.current, store.period, maVisible.value, maToggles.value],
  () => render(),
  { deep: true },
)
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- 图例 / 指标开关 -->
    <div class="flex flex-wrap items-center gap-2 px-3 py-2 text-xs bg-bg-800 border-b border-bg-600">
      <button
        class="px-2 py-0.5 rounded"
        :class="maVisible ? 'bg-accent text-white' : 'bg-bg-600 text-gray-400'"
        @click="maVisible = !maVisible; render()"
      >MA</button>
      <template v-if="maVisible">
        <button
          v-for="p in [5, 10, 20, 30, 60]"
          :key="p"
          class="px-2 py-0.5 rounded"
          :class="maToggles['MA'+p] ? 'text-yellow-400' : 'text-gray-600 line-through'"
          @click="toggleMa('MA'+p)"
        >MA{{ p }}</button>
      </template>
      <span class="ml-auto text-gray-500">{{ isLineMode ? '净值折线' : 'K 线' }}</span>
    </div>
    <div ref="chartRef" class="flex-1 min-h-0"></div>
  </div>
</template>
