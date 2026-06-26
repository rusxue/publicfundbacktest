<script setup lang="ts">
/**
 * 信息卡片：代码、名称、类型、当前周期、降级提示。
 */
import { computed } from 'vue'
import { useMarketStore } from '@/stores/market'

const store = useMarketStore()
const inst = computed(() => store.currentInstrument)
const periodText = computed(() => (store.period === 'daily' ? '日线' : '周线'))
</script>

<template>
  <div class="px-4 py-2.5 border-b bg-bg-surface border-border">
    <template v-if="inst">
      <div class="flex items-baseline gap-2 flex-wrap">
        <span class="text-base font-semibold text-fg">{{ inst.name }}</span>
        <span class="text-xs text-fg-muted font-mono">{{ inst.code }}</span>
        <span class="text-xs px-1.5 py-0.5 rounded bg-bg-elevated text-fg-muted border border-border">
          {{ inst.type }}
        </span>
        <span class="text-xs text-fg-faint">{{ periodText }}</span>
        <span
          v-if="store.isDegraded"
          class="text-xs text-yellow-500"
        >数据可能非最新</span>
      </div>
    </template>
    <template v-else>
      <div class="text-fg-muted text-sm">
        在左侧输入代码查询行情，示例：159915（创业板ETF）、510300（沪深300ETF）
      </div>
    </template>
  </div>
</template>