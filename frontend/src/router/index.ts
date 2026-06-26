/**
 * 路由表(hash 模式:无后端配合即可刷新保持,URL 可分享)。
 * 三视图:行情(默认)、量化配置、回测结果。
 * 主区域整体切换,Sidebar 常驻。
 */
import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/market' },
  {
    path: '/market',
    name: 'market',
    component: () => import('@/views/MarketView.vue'),
  },
  {
    path: '/backtest',
    name: 'config',
    component: () => import('@/views/ConfigView.vue'),
  },
  {
    path: '/backtest/result',
    name: 'result',
    component: () => import('@/views/ResultView.vue'),
  },
]

export const router = createRouter({
  history: createWebHashHistory(),
  routes,
})
