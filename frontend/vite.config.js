import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'node:path';
// 后端端口（与 backend/.env BACKEND_PORT 保持一致）
var BACKEND_PORT = process.env.BACKEND_PORT || '8000';
export default defineConfig({
    plugins: [vue()],
    resolve: {
        alias: {
            '@': path.resolve(__dirname, 'src'),
        },
    },
    server: {
        port: 5173,
        proxy: {
            // /api 转发至后端，消除跨域
            '/api': {
                target: "http://localhost:".concat(BACKEND_PORT),
                changeOrigin: true,
            },
        },
    },
    build: {
        outDir: 'dist',
        emptyOutDir: true,
    },
});
