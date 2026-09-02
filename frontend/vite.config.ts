import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    // dev 模式把 /api 代理到后端;SSE 流由 http-proxy 直接透传
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:9081',
        changeOrigin: true,
      },
    },
  },
})
