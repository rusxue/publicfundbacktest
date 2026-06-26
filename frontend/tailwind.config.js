/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'PingFang SC',
          'Microsoft YaHei',
          'sans-serif',
        ],
        mono: ['JetBrains Mono', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      colors: {
        // 语义化主题 token
        // 默认对应 light 主题；dark 下通过 CSS 变量覆盖
        bg: {
          base: 'rgb(var(--c-bg-base) / <alpha-value>)',
          surface: 'rgb(var(--c-bg-surface) / <alpha-value>)',
          elevated: 'rgb(var(--c-bg-elevated) / <alpha-value>)',
          hover: 'rgb(var(--c-bg-hover) / <alpha-value>)',
        },
        border: {
          DEFAULT: 'rgb(var(--c-border) / <alpha-value>)',
        },
        fg: {
          DEFAULT: 'rgb(var(--c-text) / <alpha-value>)',
          muted: 'rgb(var(--c-text-muted) / <alpha-value>)',
          faint: 'rgb(var(--c-text-faint) / <alpha-value>)',
        },
        // 红涨绿跌（中国习惯，两主题一致）
        up: '#ef4444',
        down: '#22c55e',
        accent: 'rgb(var(--c-accent) / <alpha-value>)',
        // MA 均线色
        ma: {
          5: '#ef4444',
          10: '#f59e0b',
          20: '#eab308',
          30: '#a855f7',
          60: '#3b82f6',
        },
      },
      boxShadow: {
        card: '0 1px 2px 0 rgb(0 0 0 / 0.04), 0 1px 3px 0 rgb(0 0 0 / 0.06)',
      },
    },
  },
  plugins: [],
}