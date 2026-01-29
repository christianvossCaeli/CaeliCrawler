/// <reference types="vitest" />
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import Icons from 'unplugin-icons/vite'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  // Load env files based on mode (.env, .env.local, .env.[mode], .env.[mode].local)
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [
      vue(),
      // Vuetify tree-shaking: only include components actually used
      vuetify({ autoImport: true }),
      // Icon tree-shaking: only bundle icons actually used (replaces ~200KB @mdi/font)
      Icons({
        compiler: 'vue3',
        autoInstall: true,
      }),
    ],
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
          target: env.VITE_API_BASE_URL || 'http://backend:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, '')
        }
      }
    },
    build: {
      // Increase chunk warning limit since we have intentional large chunks
      chunkSizeWarningLimit: 600,
      // esbuild minification with production optimizations
      minify: 'esbuild',
      // Drop console.log in production for smaller bundles
      esbuild: mode === 'production' ? {
        drop: ['console', 'debugger'],
        legalComments: 'none',
      } : undefined,
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
  }
})
