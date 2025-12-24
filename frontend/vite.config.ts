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
    // Increase chunk warning limit since we have intentional large chunks
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          // Node modules chunking
          if (id.includes('node_modules')) {
            // Vue ecosystem
            if (id.includes('vue') && !id.includes('vuetify') && !id.includes('vue-chartjs') && !id.includes('vue-i18n')) {
              return 'vue-core'
            }
            // Vuetify - large framework
            if (id.includes('vuetify')) {
              return 'vuetify'
            }
            // Charts - only used on specific pages
            if (id.includes('chart.js') || id.includes('vue-chartjs')) {
              return 'charts'
            }
            // Internationalization
            if (id.includes('vue-i18n')) {
              return 'i18n'
            }
            // Date utilities
            if (id.includes('date-fns')) {
              return 'date-utils'
            }
            // MapLibre - heavy map library, already lazy-loaded
            if (id.includes('maplibre')) {
              return 'maplibre-gl'
            }
            // Markdown rendering
            if (id.includes('marked') || id.includes('dompurify')) {
              return 'markdown'
            }
            // VueUse utilities
            if (id.includes('@vueuse')) {
              return 'vueuse'
            }
            // Other vendor libs
            return 'vendor'
          }
        }
      }
    }
  }
})
