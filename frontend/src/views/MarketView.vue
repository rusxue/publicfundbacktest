<script setup lang="ts">
/**
 * 主视图：桌面双栏 / 移动端上下布局。
 */
import Sidebar from '@/components/Sidebar.vue'
import TopBar from '@/components/TopBar.vue'
import InfoCard from '@/components/InfoCard.vue'
import KlineChart from '@/components/KlineChart.vue'
</script>

<template>
  <div class="flex flex-col md:flex-row h-screen overflow-hidden bg-bg-900">
    <Sidebar />
    <main class="flex flex-col flex-1 min-w-0">
      <TopBar />
      <InfoCard />
      <div class="flex-1 min-h-0">
        <KlineChart />
      </div>
    </main>
  </div>
</template>
