<script setup lang="ts">
/**
 * 顶部控制栏：周期切换、指标开关、最新价、降级提示。
 */
import { computed } from 'vue'
import { useMarketStore } from '@/stores/market'

const store = useMarketStore()

const period = computed(() => store.period)
const lastPrice = computed(() => {
  const ks = store.current?.klines ?? []
  const last = ks[ks.length - 1]
  if (!last) return null
  return last.close ?? last.nav ?? null
})
const changePct = computed(() => {
  const ks = store.current?.klines ?? []
  if (ks.length < 2) return null
  const last = ks[ks.length - 1]
  const prev = ks[ks.length - 2]
  const cur = last.close ?? last.nav
  const p = prev.close ?? prev.nav
  if (cur == null || p == null) return null
  return ((cur - p) / p) * 100
})
</script>

<template>
  <div class="flex items-center gap-3 px-4 py-2 bg-bg-800 border-b border-bg-600 text-sm">
    <!-- 周期切换 -->
    <div class="flex items-center bg-bg-700 rounded overflow-hidden">
      <button
        class="px-3 py-1"
        :class="period === 'daily' ? 'bg-accent text-white' : 'text-gray-400'"
        @click="store.switchPeriod('daily')"
      >1日</button>
      <button
        class="px-3 py-1"
        :class="period === 'weekly' ? 'bg-accent text-white' : 'text-gray-400'"
        @click="store.switchPeriod('weekly')"
      >1周</button>
    </div>

    <!-- 降级提示 -->
    <span
      v-if="store.isDegraded"
      class="text-yellow-400 text-xs"
    >⚠ 数据可能非最新</span>

    <!-- 错误 -->
    <span v-if="store.errorMsg" class="text-red-400 text-xs">{{ store.errorMsg }}</span>
    <span v-if="store.loading" class="text-gray-400 text-xs">加载中…</span>

    <!-- 最新价 -->
    <div class="ml-auto flex items-center gap-2">
      <template v-if="lastPrice != null">
        <span class="text-gray-400">{{ lastPrice.toFixed(3) }}</span>
        <span
          v-if="changePct != null"
          :class="changePct >= 0 ? 'text-up' : 'text-down'"
        >{{ changePct >= 0 ? '+' : '' }}{{ changePct.toFixed(2) }}%</span>
      </template>
    </div>
  </div>
</template>
