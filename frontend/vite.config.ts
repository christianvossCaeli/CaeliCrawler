/// <reference types="vitest" />
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  test: {
    globals: true,
    environment: 'happy-dom',
    include: ['src/**/*.{test,spec}.{js,ts}'],
    setupFiles: ['./src/test/setup.ts'],
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_BASE_URL || 'http://backend:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Vue core - rarely changes
          'vue-core': ['vue', 'vue-router', 'pinia'],
          // Vuetify - large framework, cache separately
          'vuetify': ['vuetify'],
          // Charts - only used on specific pages
          'charts': ['chart.js', 'vue-chartjs'],
          // Internationalization
          'i18n': ['vue-i18n'],
          // Date utilities with timezone support
          'date-utils': ['date-fns', '@date-fns/tz'],
        }
      }
    }
  }
})
