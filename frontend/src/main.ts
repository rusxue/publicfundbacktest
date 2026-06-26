import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { useMarketStore } from '@/stores/market'
import './style.css'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.mount('#app')

// 初始化主题（需在 pinia 注册后）
useMarketStore().initTheme()
