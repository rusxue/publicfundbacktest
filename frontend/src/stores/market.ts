/**
 * 行情状态管理：当前标的、周期、搜索历史、星标列表。
 * 历史与星标持久化到 localStorage。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { isCancel } from 'axios'
import {
  fetchKline,
  extractError,
  type KlineResponse,
  type Period,
} from '@/api/kline'

export type Theme = 'light' | 'dark'

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
  // ===== 主题（明/暗）=====
  const theme = ref<'light' | 'dark'>('light')

  function initTheme() {
    const saved = (localStorage.getItem('pfb_theme') ?? 'light') as 'light' | 'dark'
    theme.value = saved
    applyTheme(saved)
  }

  function toggleTheme() {
    const next = theme.value === 'light' ? 'dark' : 'light'
    theme.value = next
    localStorage.setItem('pfb_theme', next)
    applyTheme(next)
  }

  function applyTheme(t: 'light' | 'dark') {
    document.documentElement.classList.toggle('dark', t === 'dark')
  }

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
  // 请求竞态控制：切标的/切周期时取消上一个在飞请求；相同请求在飞时去重复用，
  // 避免快速连点叠发；被取消的请求静默处理，不写错误、不清空展示。
  const inflight = new Map<string, Promise<KlineResponse>>()
  let currentController: AbortController | null = null

  function applyResult(resp: KlineResponse) {
    current.value = resp
    const item = toListItem(resp)
    pushHistory(item)
    // 若已在星标列表，同步其名称/价格
    syncStarred(item)
  }

  async function query(code: string, type: 'ETF' | 'FUND') {
    const c = code.trim()
    if (!c) return
    const key = `${c}|${type}|${period.value}`

    // 去重：相同请求在飞则复用，避免叠发
    const existing = inflight.get(key)
    if (existing) {
      loading.value = true
      try {
        applyResult(await existing)
      } catch (err) {
        if (!isCancel(err)) {
          errorMsg.value = extractError(err)
          current.value = null
        }
      } finally {
        loading.value = inflight.size > 0
      }
      return
    }

    // 取消上一个在飞请求（切标的/切周期时旧请求不再需要）
    currentController?.abort()
    const controller = new AbortController()
    currentController = controller

    loading.value = true
    errorMsg.value = ''
    const p = fetchKline(c, period.value, type, controller.signal)
    inflight.set(key, p)
    try {
      applyResult(await p)
    } catch (err) {
      // 被新请求取消：静默，不报错、不清空
      if (isCancel(err)) return
      errorMsg.value = extractError(err)
      current.value = null
    } finally {
      inflight.delete(key)
      if (currentController === controller) currentController = null
      loading.value = inflight.size > 0
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
      // 重新拉取以切换周期（沿用当前标的类型，类型不随周期切换而变）
      query(current.value.instrument.code, current.value.instrument.type)
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
    // 主题
    theme,
    initTheme,
    toggleTheme,
  }
})
