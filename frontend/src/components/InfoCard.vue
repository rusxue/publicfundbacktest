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
  <div class="px-4 py-3 bg-bg-800 border-b border-bg-600">
    <template v-if="inst">
      <div class="flex items-baseline gap-2">
        <span class="text-lg font-semibold text-white">{{ inst.name }}</span>
        <span class="text-sm text-gray-400">{{ inst.code }}</span>
        <span
          class="text-xs px-1.5 py-0.5 rounded bg-bg-600 text-gray-300"
        >{{ inst.type }}</span>
        <span class="text-xs text-gray-500">{{ periodText }}</span>
        <span
          v-if="store.isDegraded"
          class="text-xs text-yellow-400"
        >数据可能非最新</span>
      </div>
    </template>
    <template v-else>
      <div class="text-gray-500 text-sm">
        在左侧输入代码查询行情，示例：159915（创业板ETF）、510300（沪深300ETF）
      </div>
    </template>
  </div>
</template>
