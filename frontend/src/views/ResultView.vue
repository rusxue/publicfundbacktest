<script setup lang="ts">
/**
 * 回测结果页：指标数字面板 + 图表(净值/回撤切换) + 交易明细表(导出)。
 * 只读消费 store.result；支持「返回配置」与「重新回测」。
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import ViewTabs from '@/components/ViewTabs.vue'
import IndicatorPanel from '@/components/IndicatorPanel.vue'
import BacktestChart from '@/components/BacktestChart.vue'
import TradeTable from '@/components/TradeTable.vue'
import { useBacktestStore } from '@/stores/backtest'

const btStore = useBacktestStore()
const router = useRouter()

const result = computed(() => btStore.result)
const metrics = computed(() => result.value?.metrics ?? null)
const curve = computed(() => result.value?.curve ?? [])
const trades = computed(() => result.value?.trades ?? [])
const summary = computed(() => result.value?.summary ?? null)
const snapshot = computed(() => result.value?.snapshot ?? null)

const periodText = (p: string) => (p === 'daily' ? '日线' : '周线')

function backToConfig() {
  router.push('/backtest')
}
</script>

<template>
  <div class="flex flex-col h-full">
    <ViewTabs />

    <!-- 结果摘要顶栏 -->
    <div class="flex flex-wrap items-center gap-3 px-4 py-2 border-b bg-bg-surface border-border text-sm">
      <button
        class="flex items-center gap-1 text-fg-muted hover:text-fg transition-colors duration-150 cursor-pointer"
        @click="backToConfig"
      >
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="19" y1="12" x2="5" y2="12" />
          <polyline points="12 19 5 12 12 5" />
        </svg>
        返回配置
      </button>
      <template v-if="snapshot">
        <span class="text-fg font-medium">{{ snapshot.name }}</span>
        <span class="text-xs font-mono text-fg-muted">{{ snapshot.code }}</span>
        <span class="text-xs text-fg-muted">· {{ snapshot.type }}</span>
        <span class="text-xs text-fg-muted">· {{ periodText(snapshot.period) }} · MA{{ snapshot.maPeriod }}</span>
        <span class="text-xs text-fg-muted">· {{ snapshot.shareClass }} 类</span>
        <span class="text-xs text-fg-muted">· {{ snapshot.startDate }} ~ {{ snapshot.endDate }}</span>
      </template>
      <button
        class="ml-auto flex items-center gap-1 px-3 py-1 text-xs bg-accent text-white rounded hover:brightness-110 transition-all duration-150 cursor-pointer"
        @click="backToConfig"
      >
        <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="23 4 23 10 17 10" />
          <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
        </svg>
        重新回测
      </button>
    </div>

    <!-- 结果主体 -->
    <div v-if="result" class="flex-1 min-h-0 flex flex-col overflow-y-auto">
      <!-- ① 指标数字面板 -->
      <IndicatorPanel :metrics="metrics" />

      <!-- ② 图表展示 -->
      <div class="h-[340px] border-b border-border">
        <BacktestChart :curve="curve" :trades="trades" />
      </div>

      <!-- ③ 交易明细表格 -->
      <div class="flex-1 min-h-[220px]">
        <TradeTable :trades="trades" :summary="summary" :loading="false" />
      </div>
    </div>

    <!-- 空态：无结果（如直接访问 URL） -->
    <div v-else class="flex-1 flex flex-col items-center justify-center gap-3 text-fg-muted">
      <div class="text-sm">暂无回测结果，请先完成策略配置并运行回测</div>
      <button
        class="px-4 py-1.5 text-sm bg-accent text-white rounded hover:brightness-110 transition-all duration-150 cursor-pointer"
        @click="backToConfig"
      >前往配置页</button>
    </div>
  </div>
</template>
