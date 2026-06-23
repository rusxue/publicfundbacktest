<script setup lang="ts">
/**
 * 左侧边栏：搜索框（基金/ETF 切换）、搜索历史、星标列表。
 */
import { ref, computed } from 'vue'
import { useMarketStore, type ListItem } from '@/stores/market'

const store = useMarketStore()

const code = ref('')
// 搜索类型：ETF / FUND
const searchType = ref<'ETF' | 'FUND'>('ETF')

function onSearch() {
  if (!code.value.trim()) return
  store.query(code.value, searchType.value)
  code.value = ''
}

function onItemClick(item: ListItem) {
  code.value = item.code
  searchType.value = item.type
  store.query(item.code, item.type)
}

function fmtPrice(p: number | null) {
  return p == null ? '--' : p.toFixed(3)
}
function fmtPct(p: number | null) {
  return p == null ? '--' : `${p >= 0 ? '+' : ''}${p.toFixed(2)}%`
}
function changeClass(p: number | null) {
  if (p == null) return 'text-gray-500'
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
  <aside class="flex flex-col w-full md:w-72 bg-bg-800 border-b md:border-b-0 md:border-r border-bg-600">
    <!-- 搜索区 -->
    <div class="p-3 border-b border-bg-600">
      <div class="flex items-center bg-bg-700 rounded overflow-hidden text-xs">
        <button
          class="px-2 py-1"
          :class="searchType === 'ETF' ? 'bg-accent text-white' : 'text-gray-400'"
          @click="searchType = 'ETF'"
        >ETF</button>
        <button
          class="px-2 py-1"
          :class="searchType === 'FUND' ? 'bg-accent text-white' : 'text-gray-400'"
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
          class="flex-1 px-2 py-1.5 text-sm bg-bg-700 rounded outline-none focus:ring-1 focus:ring-accent"
          @keyup.enter="onSearch"
        />
        <button
          class="px-3 py-1.5 text-sm bg-accent text-white rounded hover:bg-blue-600"
          @click="onSearch"
        >查询</button>
      </div>
    </div>

    <!-- 列表区 -->
    <div class="flex-1 overflow-y-auto">
      <!-- 星标 -->
      <div class="px-3 pt-3">
        <div class="text-xs text-gray-500 mb-1">星标</div>
        <div v-if="store.starred.length === 0" class="text-xs text-gray-600 py-2">
          点击列表项右侧 ☆ 加星标
        </div>
        <ul>
          <li
            v-for="(item, i) in store.starred"
            :key="item.code"
            draggable="true"
            class="flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer hover:bg-bg-700"
            @click="onItemClick(item)"
            @dragstart="onDragStart(i)"
            @dragover="onDragOver"
            @drop="onDrop(i)"
          >
            <span class="text-gray-600 cursor-grab">⋮⋮</span>
            <div class="flex-1 min-w-0">
              <div class="flex items-baseline justify-between">
                <span class="text-sm text-white truncate">{{ item.name }}</span>
                <span class="text-xs text-gray-400">{{ fmtPrice(item.price) }}</span>
              </div>
              <div class="flex items-baseline justify-between">
                <span class="text-xs text-gray-500">{{ item.code }}</span>
                <span class="text-xs" :class="changeClass(item.changePct)">{{ fmtPct(item.changePct) }}</span>
              </div>
            </div>
            <button
              class="text-yellow-400 text-sm"
              @click.stop="store.toggleStar(item)"
            >★</button>
          </li>
        </ul>
      </div>

      <!-- 历史 -->
      <div class="px-3 pt-3 pb-4">
        <div class="flex items-center justify-between mb-1">
          <span class="text-xs text-gray-500">搜索历史</span>
          <button
            v-if="store.history.length"
            class="text-xs text-gray-600 hover:text-gray-400"
            @click="store.clearHistory()"
          >清空</button>
        </div>
        <div v-if="store.history.length === 0" class="text-xs text-gray-600 py-2">
          暂无历史，默认显示最近 5 条
        </div>
        <ul>
          <li
            v-for="item in store.history"
            :key="item.code"
            class="flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer hover:bg-bg-700"
            @click="onItemClick(item)"
          >
            <div class="flex-1 min-w-0">
              <div class="flex items-baseline justify-between">
                <span class="text-sm text-white truncate">{{ item.name }}</span>
                <span class="text-xs text-gray-400">{{ fmtPrice(item.price) }}</span>
              </div>
              <div class="flex items-baseline justify-between">
                <span class="text-xs text-gray-500">{{ item.code }} · {{ item.type }}</span>
                <span class="text-xs" :class="changeClass(item.changePct)">{{ fmtPct(item.changePct) }}</span>
              </div>
            </div>
            <button
              class="text-gray-500 text-sm hover:text-yellow-400"
              :class="{ 'text-yellow-400': store.isStarred(item.code) }"
              @click.stop="store.toggleStar(item)"
            >{{ store.isStarred(item.code) ? '★' : '☆' }}</button>
          </li>
        </ul>
      </div>
    </div>
  </aside>
</template>
