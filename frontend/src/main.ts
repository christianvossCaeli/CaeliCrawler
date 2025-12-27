import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { setupApiInterceptors } from './services/api/client'

// Vuetify
import 'vuetify/styles'
import './styles/global.css'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import * as labsComponents from 'vuetify/labs/components'
import '@mdi/font/css/materialdesignicons.css'
import { de, en } from 'vuetify/locale'

// i18n
import i18n, { getLocale } from './locales'

const vuetify = createVuetify({
  components: {
    ...components,
    ...labsComponents,
  },
  directives,
  locale: {
    locale: getLocale(),
    fallback: 'de',
    messages: { de, en },
  },
  theme: {
    defaultTheme: 'caeliLight',
    themes: {
      caeliLight: {
        dark: false,
        colors: {
          primary: '#113634',
          secondary: '#deeec6',
          tertiary: '#5c6bc0',
          error: '#dc3545',
          info: '#0288d1',
          success: '#2e7d32',
          warning: '#5c6bc0',
          background: '#f3f3f3',
          surface: '#ffffff',
          'on-primary': '#ffffff',
          'on-secondary': '#113634',
          'on-success': '#ffffff',
          'on-warning': '#ffffff',
          'on-error': '#ffffff',
          'on-info': '#ffffff',
          'on-surface': '#212529',
          'on-background': '#212529',
          red: '#871623',
          blue: '#00274a',
          purple: '#6610f2',
          danger: '#dc3545',
          light: '#f3f3f3',
          dark: '#212529',
          'success-light': '#dbe8e2',
          'warning-light': '#92a0ff',
          'info-light': '#d1ecf1',
        },
      },
      caeliDark: {
        dark: true,
        colors: {
          // Basierend auf Caeli Wind Farbpalette
          primary: '#deeec6',           // Secondary wird zu Primary im Dark Mode (gutes Grün)
          secondary: '#113634',         // Original Primary als Secondary
          tertiary: '#92a0ff',          // Bleibt gleich (Lila/Blau)
          error: '#ff6b6b',             // Aufgehelltes Rot
          info: '#7ec8e3',              // Aufgehelltes Blau
          success: '#a8d5a2',           // Aufgehelltes Grün
          warning: '#b8c0ff',           // Aufgehelltes Tertiary
          background: '#0d1f1e',        // Sehr dunkles Grün (basierend auf Primary)
          surface: '#142928',           // Etwas helleres dunkles Grün
          'on-primary': '#113634',      // Dunkler Text auf hellem Primary
          'on-secondary': '#deeec6',    // Heller Text auf dunklem Secondary
          'on-success': '#0d1f1e',
          'on-warning': '#0d1f1e',
          'on-error': '#0d1f1e',
          'on-info': '#0d1f1e',
          'on-surface': '#e8f5e2',      // Leicht grünlicher heller Text
          'on-background': '#e8f5e2',
          red: '#ff6b6b',               // Aufgehelltes Rot
          blue: '#5c9ece',              // Aufgehelltes Blau
          purple: '#a78bfa',            // Aufgehelltes Lila
          danger: '#ff6b6b',
          light: '#2a3d3c',             // Dunkles Grün als "Light"
          dark: '#e8f5e2',              // Helles Grün als "Dark"
          'success-light': '#1e3a2f',
          'warning-light': '#2a3055',
          'info-light': '#1a3a4a',
        },
      },
    },
  },
  defaults: {
    global: {
      font: {
        family: 'Figtree, sans-serif',
      },
    },
  },
})

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(vuetify)
app.use(i18n)

// Setup API interceptors for automatic 401 handling (after Pinia is initialized)
setupApiInterceptors(router)

// Set HTML lang attribute
document.documentElement.lang = getLocale()

app.mount('#app')
