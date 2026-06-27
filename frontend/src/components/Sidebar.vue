<script setup lang="ts">
/**
 * 左侧边栏：搜索框、搜索历史、星标列表。
 * 已适配双主题（语义化 token），SVG 图标替换字符图标，触控最小 44px。
 */
import { ref } from 'vue'
import { useMarketStore, type ListItem } from '@/stores/market'
import { useRouter, useRoute } from 'vue-router'

const store = useMarketStore()
const router = useRouter()
const route = useRoute()

const code = ref('')
const searchType = ref<'ETF' | 'FUND'>('ETF')

function goMarket(code: string, type: 'ETF' | 'FUND') {
  // 跳行情页并带 query；MarketView 监听 query 后自动查询。
  router.push({
    path: '/market',
    query: { code, type },
  })
}

/** 在当前视图上下文中应用标的选择 */
function applySelection(code: string, type: 'ETF' | 'FUND') {
  store.query(code, type)
  if (route.name === 'market') return // 行情页：MarketView 监听 query 即刷新
  if (route.name === 'config' || route.name === 'result') {
    // 量化页：仅切换标的，留在配置页；不进行情页
    router.push('/backtest')
    return
  }
  goMarket(code, type)
}

function onSearch() {
  if (!code.value.trim()) return
  const c = code.value.trim()
  applySelection(c, searchType.value)
  code.value = ''
}

function onItemClick(item: ListItem) {
  code.value = item.code
  searchType.value = item.type
  applySelection(item.code, item.type)
}

function fmtPrice(p: number | null) {
  return p == null ? '--' : p.toFixed(3)
}
function fmtPct(p: number | null) {
  return p == null ? '--' : `${p >= 0 ? '+' : ''}${p.toFixed(2)}%`
}
function changeClass(p: number | null) {
  if (p == null) return 'text-fg-faint'
  return p >= 0 ? 'text-up' : 'text-down'
}

// 星标拖拽排序
const dragIndex = ref<number | null>(null)
function onDragStart(i: number) {
  dragIndex.value = i
}
function onDragOver(e: DragEvent) {
  e.preventDefault()
}
function onDrop(to: number) {
  if (dragIndex.value == null || dragIndex.value === to) return
  store.moveStarred(dragIndex.value, to)
  dragIndex.value = null
}
</script>

<template>
  <aside class="flex flex-col w-full md:w-72 bg-bg-surface border-b md:border-b-0 md:border-r border-border">
    <!-- 搜索区 -->
    <div class="p-3 border-b border-border">
      <div class="flex items-center bg-bg-elevated rounded overflow-hidden border border-border">
        <button
          class="px-3 py-1.5 text-xs transition-colors duration-150"
          :class="searchType === 'ETF' ? 'bg-accent text-white' : 'text-fg-muted hover:bg-bg-hover'"
          @click="searchType = 'ETF'"
        >ETF</button>
        <button
          class="px-3 py-1.5 text-xs transition-colors duration-150"
          :class="searchType === 'FUND' ? 'bg-accent text-white' : 'text-fg-muted hover:bg-bg-hover'"
          @click="searchType = 'FUND'"
        >基金</button>
      </div>
      <div class="flex gap-2 mt-2">
        <input
          v-model="code"
          type="text"
          inputmode="numeric"
          maxlength="6"
          placeholder="输入 6 位代码"
          class="flex-1 px-3 py-1.5 text-sm bg-bg-elevated rounded border border-border outline-none transition-shadow duration-150 focus:ring-2 focus:ring-accent/40"
          aria-label="基金代码搜索"
          @keyup.enter="onSearch"
        />
        <button
          class="flex items-center justify-center px-3 py-1.5 text-sm bg-accent text-white rounded hover:brightness-110 transition-all duration-150 cursor-pointer"
          aria-label="查询行情"
          @click="onSearch"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- 列表区 -->
    <div class="flex-1 overflow-y-auto">
      <!-- 星标 -->
      <div class="px-3 pt-3">
        <div class="text-xs text-fg-muted font-medium mb-1.5 flex items-center gap-1">
          <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor" opacity="0.5">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26"/>
          </svg>
          星标
        </div>
        <div v-if="store.starred.length === 0" class="text-xs text-fg-faint py-2">
          点击列表项右侧 ☆ 加星标
        </div>
        <ul>
          <li
            v-for="(item, i) in store.starred"
            :key="item.code"
            :draggable="true"
            class="flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer hover:bg-bg-hover transition-colors duration-150"
            @click="onItemClick(item)"
            @dragstart="onDragStart(i)"
            @dragover="onDragOver"
            @drop="onDrop(i)"
          >
            <span class="text-fg-faint cursor-grab select-none" aria-label="拖拽排序">
              <svg class="w-3 h-3" viewBox="0 0 24 24" fill="currentColor">
                <circle cx="9" cy="5.5" r="1.5"/><circle cx="15" cy="5.5" r="1.5"/>
                <circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/>
                <circle cx="9" cy="18.5" r="1.5"/><circle cx="15" cy="18.5" r="1.5"/>
              </svg>
            </span>
            <div class="flex-1 min-w-0">
                  <div class="flex items-baseline justify-between">
                    <span class="text-sm text-fg truncate font-medium">{{ item.name }}</span>
                    <span class="text-xs font-mono text-fg-faint ml-1.5">{{ fmtPrice(item.price) }}</span>
                  </div>
                  <div class="flex items-baseline justify-between mt-0.5">
                    <span class="text-xs text-fg-faint">{{ item.code }}</span>
                    <span class="text-xs font-mono" :class="changeClass(item.changePct)">{{ fmtPct(item.changePct) }}</span>
                  </div>
                </div>
            <button
              class="flex items-center justify-center w-5 h-5 text-lg cursor-pointer transition-colors duration-150"
              :class="store.isStarred(item.code) ? 'text-yellow-400' : 'text-fg-faint hover:text-yellow-400'"
              aria-label="移除星标"
              @click.stop="store.toggleStar(item)"
            >★</button>
          </li>
        </ul>
      </div>

      <!-- 历史 -->
      <div class="px-3 pt-3 pb-4">
        <div class="flex items-center justify-between mb-1.5">
          <div class="flex items-center gap-1 text-xs text-fg-muted font-medium">
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" opacity="0.5">
          <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
        </svg>
            搜索历史
          </div>
          <button
            v-if="store.history.length"
            class="flex text-xs text-fg-faint hover:text-fg-muted transition-colors duration-150 cursor-pointer"
            @click="store.clearHistory()"
          >清空</button>
        </div>
        <div v-if="store.history.length === 0" class="text-xs text-fg-faint py-2">
          暂无历史
        </div>
        <ul>
          <li
            v-for="item in store.history"
            :key="item.code"
            class="flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer hover:bg-bg-hover transition-colors duration-150"
            @click="onItemClick(item)"
          >
            <div class="flex-1 min-w-0">
                  <div class="flex items-baseline justify-between">
                    <span class="text-sm text-fg truncate font-medium">{{ item.name }}</span>
                    <span class="text-xs font-mono text-fg-faint ml-1.5">{{ fmtPrice(item.price) }}</span>
                  </div>
                  <div class="flex items-baseline justify-between mt-0.5">
                    <span class="text-xs text-fg-faint">{{ item.code }}</span>
                    <span class="text-xs font-mono" :class="changeClass(item.changePct)">{{ fmtPct(item.changePct) }}</span>
                  </div>
                </div>
            <button
              class="flex items-center justify-center w-5 h-5 text-sm cursor-pointer transition-colors duration-150"
              :class="store.isStarred(item.code) ? 'text-yellow-400' : 'text-fg-faint hover:text-yellow-400'"
              aria-label="点击加星标"
              @click.stop="store.toggleStar(item)"
            >{{ store.isStarred(item.code) ? '★' : '☆' }}</button>
          </li>
        </ul>
      </div>
    </div>
  </aside>
</template>