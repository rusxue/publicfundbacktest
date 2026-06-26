<script setup lang="ts">
/**
 * 顶部控制栏：周期切换、主题切换按钮、加载状态、错误提示、最新价。
 */
import { computed } from 'vue'
import { useMarketStore } from '@/stores/market'
import ThemeToggle from './ThemeToggle.vue'

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
  <div class="flex items-center gap-2 px-4 py-2 border-b bg-bg-surface border-border text-sm">
    <!-- 周期切换 -->
    <div class="flex items-center bg-bg-elevated rounded overflow-hidden border border-border">
      <button
        class="px-3 py-1 text-xs transition-colors duration-150"
        :class="period === 'daily'
          ? 'bg-accent text-white'
          : 'text-fg-muted hover:bg-bg-hover'"
        @click="store.switchPeriod('daily')"
      >日线</button>
      <button
        class="px-3 py-1 text-xs transition-colors duration-150"
        :class="period === 'weekly'
          ? 'bg-accent text-white'
          : 'text-fg-muted hover:bg-bg-hover'"
        @click="store.switchPeriod('weekly')"
      >周线</button>
    </div>

    <!-- 主题切换 -->
    <ThemeToggle />

    <!-- 状态提示 -->
    <span
      v-if="store.isDegraded"
      class="flex items-center gap-1 text-xs text-yellow-500"
    >
      <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/>
        <line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
      数据可能非最新
    </span>

    <span v-if="store.errorMsg" class="text-xs text-up">{{ store.errorMsg }}</span>
    <span v-if="store.loading" class="text-xs text-fg-muted">加载中...</span>

    <!-- 最新价 -->
    <div class="ml-auto flex items-center gap-2">
      <template v-if="lastPrice != null">
        <span class="text-fg font-mono text-sm font-medium">{{ lastPrice.toFixed(3) }}</span>
        <span
          v-if="changePct != null"
          class="font-mono text-xs"
          :class="changePct >= 0 ? 'text-up' : 'text-down'"
        >{{ changePct >= 0 ? '+' : '' }}{{ changePct.toFixed(2) }}%</span>
      </template>
    </div>
  </div>
</template>