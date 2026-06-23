/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // 深色主题
        bg: {
          900: '#0a0a0b',
          800: '#111114',
          700: '#1a1a1f',
          600: '#26262d',
        },
        // 红涨绿跌（中国习惯）
        up: '#ef4444',
        down: '#22c55e',
        accent: '#3b82f6',
      },
    },
  },
  plugins: [],
}
