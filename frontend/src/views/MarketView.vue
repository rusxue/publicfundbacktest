<script setup lang="ts">
/**
 * 行情视图：视图顶栏（含 Tab 切换）+ 行情专属顶栏（周期/最新价）+ 信息卡片 + K 线图。
 */
import ViewTabs from '@/components/ViewTabs.vue'
import TopBar from '@/components/TopBar.vue'
import InfoCard from '@/components/InfoCard.vue'
import KlineChart from '@/components/KlineChart.vue'
import { useMarketStore } from '@/stores/market'
import { onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'

const store = useMarketStore()
const route = useRoute()

function maybeQuery(code: string | undefined, type: 'ETF' | 'FUND' | undefined) {
  if (!code || !type) return
  const cur = store.currentInstrument
  if (!cur || cur.code !== code) store.query(code, type)
}

onMounted(() => {
  // 首次进入行情页且无当前标的时，尝试用 URL query(code/type) 触发查询，
  // 便于侧边栏点击跳转 /market?code=...&type=... 时自动加载。
  const code = route.query.code as string | undefined
  const type = route.query.type === 'ETF' ? 'ETF' : route.query.type === 'FUND' ? 'FUND' : undefined
  maybeQuery(code, type)
})

// 监听 route.query 变化（侧边栏点击同页跳转时 onMounted 不再触发）
watch(
  () => route.query,
  (q) => {
    if (route.name !== 'market') return
    const code = q.code as string | undefined
    const type = q.type === 'ETF' ? 'ETF' : q.type === 'FUND' ? 'FUND' : undefined
    maybeQuery(code, type)
  },
)
</script>

<template>
  <div class="flex flex-col h-full">
    <ViewTabs />
    <TopBar />
    <InfoCard />
    <div class="flex-1 min-h-0">
      <KlineChart />
    </div>
  </div>
</template>
