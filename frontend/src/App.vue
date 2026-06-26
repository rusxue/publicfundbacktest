<script setup lang="ts">
/**
 * 应用外壳：左侧边栏常驻 + 主区域随路由整体切换。
 * 主区域内各视图自带顶栏（行情 TopBar / ViewTabs）。
 */
import Sidebar from '@/components/Sidebar.vue'
</script>

<template>
  <div class="flex flex-col md:flex-row h-screen overflow-hidden">
    <Sidebar />
    <main class="flex flex-col flex-1 min-w-0">
      <RouterView v-slot="{ Component }">
        <component :is="Component" />
      </RouterView>
    </main>
  </div>
</template>
