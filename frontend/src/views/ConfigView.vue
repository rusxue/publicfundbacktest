<script setup lang="ts">
/**
 * 量化配置页：覆盖 docs/MA均线策略量化回测界面配置.md 全部配置项。
 * 分三大区：①策略参数 ②份额费率切换(A/C 联动) ③公共回测参数。
 * 提交校验 → 写入 store → 跳转回测结果页。
 */
import { reactive, computed, ref, toRaw } from 'vue'
import { useRouter } from 'vue-router'
import ViewTabs from '@/components/ViewTabs.vue'
import { useBacktestStore, type ShareClass } from '@/stores/backtest'
import { useMarketStore } from '@/stores/market'
import { runBacktest, extractBacktestError } from '@/api/backtest'

const btStore = useBacktestStore()
const market = useMarketStore()
const router = useRouter()

const inst = computed(() => market.currentInstrument)

// 以 store 配置初始化本地表单（深拷贝 raw 对象，避免 structuredClone 克隆 Proxy 报错）
function cloneConfig() {
  return JSON.parse(JSON.stringify(toRaw(btStore.config)))
}
const form = reactive(cloneConfig()) as typeof btStore.config
const MA_OPTIONS = [5, 10, 20, 30, 60] as const

const submitting = ref(false)
const errMsg = ref('')

function syncToStore() {
  btStore.config = JSON.parse(JSON.stringify(toRaw(form)))
}

function resetDefaults() {
  btStore.resetConfig()
  // resetConfig 改的是 store.config，复制回本地表单
  Object.assign(form, cloneConfig())
}

function switchShareClass(c: ShareClass) {
  form.shareClass = c
}

/** 提交回测：校验 → 写入 store → 请求 → 跳转结果页 */
async function onSubmit() {
  errMsg.value = ''
  if (!inst.value) {
    errMsg.value = '请先在左侧侧边栏选择一个标的'
    return
  }
  if (!form.startDate || !form.endDate) {
    errMsg.value = '请选择回测起止日期'
    return
  }
  if (form.startDate >= form.endDate) {
    errMsg.value = '起始日期需早于结束日期'
    return
  }
  if (form.initialCapital <= 0) {
    errMsg.value = '初始本金必须大于 0'
    return
  }

  syncToStore()
  submitting.value = true
  try {
    const result = await runBacktest(inst.value, btStore.config)
    btStore.result = result
    router.push('/backtest/result')
  } catch (err) {
    // 后端未就绪时给出明确提示，但仍允许跳转到结果页查看空态/占位
    errMsg.value = extractBacktestError(err)
  } finally {
    submitting.value = false
  }
}

/** 折叠「兜底规则」提示展示 */
const showRules = ref(false)
</script>

<template>
  <div class="flex flex-col h-full overflow-y-auto">
    <ViewTabs />

    <!-- 当前标的提示 -->
    <div class="px-4 py-2 border-b bg-bg-surface border-border text-sm">
      <span v-if="inst" class="text-fg">
        回测标的：<span class="font-medium">{{ inst.name }}</span>
        <span class="font-mono text-fg-muted ml-1">{{ inst.code }}</span>
        <span class="text-xs ml-1 px-1.5 py-0.5 rounded bg-bg-elevated text-fg-muted border border-border">{{ inst.type }}</span>
      </span>
      <span v-else class="text-yellow-500">请先在左侧侧边栏选择一个标的后再配置回测</span>
    </div>

    <div class="flex-1 px-4 py-4 space-y-5 max-w-5xl">
      <!-- ① 策略参数配置区 -->
      <section class="rounded border border-border bg-bg-surface">
        <header class="px-4 py-2 border-b border-border text-sm font-semibold text-fg">① 策略参数配置</header>
        <div class="p-4 space-y-3">
          <div class="flex flex-wrap items-center gap-4">
            <label class="flex items-center gap-2 text-sm text-fg-muted">
              K 线周期
              <select v-model="form.period" class="px-2 py-1 bg-bg-elevated rounded border border-border text-fg text-sm">
                <option value="weekly">周线</option>
                <option value="daily">日线</option>
              </select>
            </label>
            <label class="flex items-center gap-2 text-sm text-fg-muted">
              MA 均线周期
              <select v-model.number="form.maPeriod" class="px-2 py-1 bg-bg-elevated rounded border border-border text-fg text-sm">
                <option v-for="m in MA_OPTIONS" :key="m" :value="m">MA{{ m }}</option>
              </select>
            </label>
            <div class="text-sm text-fg-faint">信号判定日：每周五收盘（固定）</div>
          </div>
          <div class="text-xs text-fg-faint leading-relaxed">
            买入条件：收盘价 &gt; MA 均线（固定逻辑，仅周期跟随上方配置）；
            成交价：信号产生后下周一收盘价买入/卖出。
          </div>
          <button
            class="text-xs text-accent hover:underline cursor-pointer"
            @click="showRules = !showRules"
          >{{ showRules ? '收起' : '查看' }}非交易日兜底 / 持仓天数口径</button>
          <div v-if="showRules" class="text-xs text-fg-faint leading-relaxed bg-bg-elevated rounded p-3 border border-border space-y-1">
            <p>· 信号判定日兜底：基准周五为非交易日时，自动向前匹配本周最后一个交易日为信号判定日。</p>
            <p>· 成交日兜底：基准下周一为非交易日时，自动向后顺延至首个开盘交易日。</p>
            <p>· 持仓天数口径：统一按自然日历天数计算（含周末/节假日），用于阶梯赎回费率与锁仓冷却期判定。</p>
          </div>
        </div>
      </section>

      <!-- ② 份额费率切换 -->
      <section class="rounded border border-border bg-bg-surface">
        <header class="px-4 py-2 border-b border-border text-sm font-semibold text-fg">② 份额费率切换（互斥单选）</header>
        <div class="p-4 space-y-3">
          <div class="flex items-center gap-4 text-sm">
            <label class="flex items-center gap-1.5 cursor-pointer">
              <input type="radio" :checked="form.shareClass === 'A'" @change="switchShareClass('A')" class="accent-accent" />
              <span class="text-fg">A 类份额</span>
            </label>
            <label class="flex items-center gap-1.5 cursor-pointer">
              <input type="radio" :checked="form.shareClass === 'C'" @change="switchShareClass('C')" class="accent-accent" />
              <span class="text-fg">C 类份额</span>
            </label>
          </div>

          <!-- A 类 -->
          <div v-if="form.shareClass === 'A'" class="grid grid-cols-2 md:grid-cols-3 gap-3">
            <label class="flex flex-col gap-1 text-xs text-fg-muted">
              申购费率 (%)
              <input v-model.number="form.aPurchaseFee" type="number" step="0.01" min="0"
                class="px-2 py-1 bg-bg-elevated rounded border border-border text-fg text-sm" />
            </label>
            <label class="flex flex-col gap-1 text-xs text-fg-muted">
              年化管理费 (%)
              <input v-model.number="form.aManagementFee" type="number" step="0.01" min="0"
                class="px-2 py-1 bg-bg-elevated rounded border border-border text-fg text-sm" />
            </label>
            <div class="col-span-2 md:col-span-3 text-xs text-fg-faint mt-1">赎回费率档位（按自然日历持仓天数）：</div>
            <label class="flex flex-col gap-1 text-xs text-fg-muted">
              持仓 &lt; 7 天 (%)
              <input v-model.number="form.redemption.lt7" type="number" step="0.01" min="0"
                class="px-2 py-1 bg-bg-elevated rounded border border-border text-fg text-sm" />
            </label>
            <label class="flex flex-col gap-1 text-xs text-fg-muted">
              7 ≤ 持仓 &lt; 30 天 (%)
              <input v-model.number="form.redemption.lt30" type="number" step="0.01" min="0"
                class="px-2 py-1 bg-bg-elevated rounded border border-border text-fg text-sm" />
            </label>
            <label class="flex flex-col gap-1 text-xs text-fg-muted">
              30 ≤ 持仓 &lt; 365 天 (%)
              <input v-model.number="form.redemption.lt365" type="number" step="0.01" min="0"
                class="px-2 py-1 bg-bg-elevated rounded border border-border text-fg text-sm" />
            </label>
            <label class="flex flex-col gap-1 text-xs text-fg-muted">
              365 ≤ 持仓 &lt; 730 天 (%)
              <input v-model.number="form.redemption.lt730" type="number" step="0.01" min="0"
                class="px-2 py-1 bg-bg-elevated rounded border border-border text-fg text-sm" />
            </label>
            <label class="flex flex-col gap-1 text-xs text-fg-muted">
              持仓 ≥ 730 天 (%)
              <input v-model.number="form.redemption.gte730" type="number" step="0.01" min="0"
                class="px-2 py-1 bg-bg-elevated rounded border border-border text-fg text-sm" />
            </label>
          </div>

          <!-- C 类 -->
          <div v-else class="grid grid-cols-2 md:grid-cols-3 gap-3">
            <label class="flex flex-col gap-1 text-xs text-fg-muted">
              申购费率 (%)
              <input :value="0" disabled
                class="px-2 py-1 bg-bg-base rounded border border-border text-fg-faint text-sm" />
            </label>
            <label class="flex flex-col gap-1 text-xs text-fg-muted">
              年化销售服务费 (%)
              <input v-model.number="form.cServiceFee" type="number" step="0.01" min="0"
                class="px-2 py-1 bg-bg-elevated rounded border border-border text-fg text-sm" />
            </label>
            <div class="col-span-2 md:col-span-3 text-xs text-fg-faint mt-1">赎回费率档位（C 类：≥30 天自动 0）：</div>
            <label class="flex flex-col gap-1 text-xs text-fg-muted">
              持仓 &lt; 7 天 (%)
              <input v-model.number="form.redemption.lt7" type="number" step="0.01" min="0"
                class="px-2 py-1 bg-bg-elevated rounded border border-border text-fg text-sm" />
            </label>
            <label class="flex flex-col gap-1 text-xs text-fg-muted">
              7 ≤ 持仓 &lt; 30 天 (%)
              <input v-model.number="form.redemption.lt30" type="number" step="0.01" min="0"
                class="px-2 py-1 bg-bg-elevated rounded border border-border text-fg text-sm" />
            </label>
            <label class="flex flex-col gap-1 text-xs text-fg-muted">
              持仓 ≥ 30 天 (%)
              <input :value="0" disabled
                class="px-2 py-1 bg-bg-base rounded border border-border text-fg-faint text-sm" />
            </label>
          </div>
        </div>
      </section>

      <!-- ③ 公共回测参数 -->
      <section class="rounded border border-border bg-bg-surface">
        <header class="px-4 py-2 border-b border-border text-sm font-semibold text-fg">③ 公共回测参数</header>
        <div class="p-4 space-y-3">
          <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
            <label class="flex flex-col gap-1 text-xs text-fg-muted">
              初始本金
              <input v-model.number="form.initialCapital" type="number" min="1"
                class="px-2 py-1 bg-bg-elevated rounded border border-border text-fg text-sm" />
            </label>
            <label class="flex flex-col gap-1 text-xs text-fg-muted">
              锁仓冷却期 (天)
              <input v-model.number="form.lockupDays" type="number" min="0"
                class="px-2 py-1 bg-bg-elevated rounded border border-border text-fg text-sm" />
            </label>
            <label class="flex flex-col gap-1 text-xs text-fg-muted">
              买入价格偏离率 (%)
              <input v-model.number="form.buyDeviation" type="number" step="0.01"
                class="px-2 py-1 bg-bg-elevated rounded border border-border text-fg text-sm" />
            </label>
            <label class="flex flex-col gap-1 text-xs text-fg-muted">
              卖出价格偏离率 (%)
              <input v-model.number="form.sellDeviation" type="number" step="0.01"
                class="px-2 py-1 bg-bg-elevated rounded border border-border text-fg text-sm" />
            </label>
            <label class="flex flex-col gap-1 text-xs text-fg-muted">
              平仓比例 (%)
              <input v-model.number="form.closeRatio" type="number" min="0" max="100"
                class="px-2 py-1 bg-bg-elevated rounded border border-border text-fg text-sm" />
            </label>
          </div>
          <div class="flex flex-wrap items-center gap-4">
            <label class="flex items-center gap-2 text-sm text-fg-muted">
              回测起始
              <input v-model="form.startDate" type="date"
                class="px-2 py-1 bg-bg-elevated rounded border border-border text-fg text-sm" />
            </label>
            <label class="flex items-center gap-2 text-sm text-fg-muted">
              回测结束
              <input v-model="form.endDate" type="date"
                class="px-2 py-1 bg-bg-elevated rounded border border-border text-fg text-sm" />
            </label>
            <span class="text-xs text-fg-faint">默认近 3 年</span>
          </div>
        </div>
      </section>

      <!-- 错误提示 -->
      <div v-if="errMsg" class="text-sm text-yellow-500">{{ errMsg }}</div>

      <!-- 操作栏 -->
      <div class="flex items-center justify-end gap-3 pb-4">
        <button
          class="px-4 py-1.5 text-sm text-fg-muted bg-bg-elevated rounded border border-border hover:bg-bg-hover transition-colors duration-150 cursor-pointer"
          @click="resetDefaults"
        >重置默认</button>
        <button
          class="flex items-center gap-2 px-5 py-1.5 text-sm bg-accent text-white rounded hover:brightness-110 transition-all duration-150 cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
          :disabled="submitting || !inst"
          @click="onSubmit"
        >
          <svg v-if="submitting" class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 1 1-6.219-8.56" stroke-linecap="round" />
          </svg>
          {{ submitting ? '回测中…' : '▶ 开始回测' }}
        </button>
      </div>
    </div>
  </div>
</template>
