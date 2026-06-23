/**
 * 行情状态管理：当前标的、周期、搜索历史、星标列表。
 * 历史与星标持久化到 localStorage。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  fetchKline,
  extractError,
  type KlineResponse,
  type Period,
} from '@/api/kline'

const HISTORY_KEY = 'pfb_history'
const STARRED_KEY = 'pfb_starred'
const MAX_HISTORY = 5

export interface ListItem {
  code: string
  name: string
  type: 'ETF' | 'FUND'
  price: number | null
  changePct: number | null
}

export const useMarketStore = defineStore('market', () => {
  // ===== 当前展示 =====
  const current = ref<KlineResponse | null>(null)
  const period = ref<Period>('daily')
  const loading = ref(false)
  const errorMsg = ref('')

  // ===== 搜索历史 =====
  const history = ref<ListItem[]>(load(HISTORY_KEY))
  // ===== 星标列表 =====
  const starred = ref<ListItem[]>(load(STARRED_KEY))

  const currentInstrument = computed(() => current.value?.instrument ?? null)
  const isDegraded = computed(() => current.value?.is_degraded ?? false)

  function load(key: string): ListItem[] {
    try {
      const raw = localStorage.getItem(key)
      return raw ? JSON.parse(raw) : []
    } catch {
      return []
    }
  }
  function save(key: string, val: ListItem[]) {
    localStorage.setItem(key, JSON.stringify(val))
  }

  /** 查询行情并刷新当前展示 */
  async function query(code: string, type?: 'ETF' | 'FUND') {
    const c = code.trim()
    if (!c) return
    loading.value = true
    errorMsg.value = ''
    try {
      const resp = await fetchKline(c, period.value)
      current.value = resp
      const item = toListItem(resp)
      pushHistory(item)
      // 若已在星标列表，同步其名称/价格
      syncStarred(item)
    } catch (err) {
      errorMsg.value = extractError(err)
      current.value = null
    } finally {
      loading.value = false
    }
  }

  function toListItem(resp: KlineResponse): ListItem {
    const klines = resp.klines
    const last = klines[klines.length - 1]
    const prev = klines.length > 1 ? klines[klines.length - 2] : null
    const price = last ? (last.close ?? last.nav) ?? null : null
    let changePct: number | null = null
    if (last && prev) {
      const cur = last.close ?? last.nav
      const p = prev.close ?? prev.nav
      if (cur != null && p) changePct = ((cur - p) / p) * 100
    }
    return {
      code: resp.instrument.code,
      name: resp.instrument.name,
      type: resp.instrument.type,
      price,
      changePct,
    }
  }

  function pushHistory(item: ListItem) {
    const idx = history.value.findIndex((h) => h.code === item.code)
    if (idx >= 0) history.value.splice(idx, 1)
    history.value.unshift(item)
    if (history.value.length > MAX_HISTORY) history.value.length = MAX_HISTORY
    save(HISTORY_KEY, history.value)
  }

  function clearHistory() {
    history.value = []
    save(HISTORY_KEY, [])
  }

  function isStarred(code: string) {
    return starred.value.some((s) => s.code === code)
  }

  function toggleStar(item: ListItem) {
    const idx = starred.value.findIndex((s) => s.code === item.code)
    if (idx >= 0) starred.value.splice(idx, 1)
    else starred.value.push(item)
    save(STARRED_KEY, starred.value)
  }

  function syncStarred(item: ListItem) {
    const idx = starred.value.findIndex((s) => s.code === item.code)
    if (idx >= 0) {
      starred.value[idx] = { ...item }
      save(STARRED_KEY, starred.value)
    }
  }

  /** 移动星标项顺序 */
  function moveStarred(from: number, to: number) {
    if (to < 0 || to >= starred.value.length) return
    const [item] = starred.value.splice(from, 1)
    starred.value.splice(to, 0, item)
    save(STARRED_KEY, starred.value)
  }

  function switchPeriod(p: Period) {
    period.value = p
    if (current.value) {
      // 重新拉取以切换周期
      query(current.value.instrument.code)
    }
  }

  return {
    current,
    period,
    loading,
    errorMsg,
    history,
    starred,
    currentInstrument,
    isDegraded,
    query,
    clearHistory,
    isStarred,
    toggleStar,
    moveStarred,
    switchPeriod,
  }
})
