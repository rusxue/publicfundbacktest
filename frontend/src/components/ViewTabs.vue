<script setup lang="ts">
/**
 * 视图顶栏：行情 / 量化回测 Tab 切换 + 当前标的提示 + 主题切换。
 * 通过 RouterLink 激活态高亮；点击行情页若侧边栏无标的，亦允许进入。
 */
import { computed } from 'vue'
import { useMarketStore } from '@/stores/market'
import ThemeToggle from './ThemeToggle.vue'

const store = useMarketStore()
const inst = computed(() => store.currentInstrument)
</script>

<template>
  <div class="flex items-center gap-2 px-4 py-2 border-b bg-bg-surface border-border text-sm">
    <!-- 视图切换 Tab -->
    <div class="flex items-center bg-bg-elevated rounded overflow-hidden border border-border">
      <RouterLink
        to="/market"
        class="px-3 py-1 text-xs transition-colors duration-150"
        active-class="bg-accent text-white"
        >行情</RouterLink
      >
      <RouterLink
        to="/backtest"
        class="px-3 py-1 text-xs transition-colors duration-150"
        active-class="bg-accent text-white"
        >量化回测</RouterLink
      >
    </div>

    <!-- 当前标的提示 -->
    <span
      v-if="inst"
      class="text-xs text-fg-muted font-mono ml-1"
    >当前标的：{{ inst.name }} {{ inst.code }} · {{ inst.type }}</span>
    <span v-else class="text-xs text-fg-faint ml-1">未选择标的</span>

    <div class="ml-auto flex items-center gap-2">
      <ThemeToggle />
    </div>
  </div>
</template>
