<template>
  <v-app>
    <!-- Navigation Drawer (only when authenticated) -->
    <v-navigation-drawer v-if="auth.isAuthenticated" v-model="drawer" app>
      <div class="pa-4">
        <CaeliWindLogo :primary-color="isDark ? '#deeec6' : '#113534'" />
      </div>

      <v-divider></v-divider>

      <v-list density="compact" nav>
        <v-list-item
          v-for="item in mainNavItems"
          :key="item.to"
          :to="item.to"
          :prepend-icon="item.icon"
          :title="item.title"
        >
          <template #append>
            <v-badge
              v-if="item.to === '/documents' && pendingDocsCount > 0"
              :content="pendingDocsCount > 99 ? '99+' : pendingDocsCount"
              color="warning"
              inline
            ></v-badge>
            <v-badge
              v-if="item.to === '/results' && unverifiedResultsCount > 0"
              :content="unverifiedResultsCount > 99 ? '99+' : unverifiedResultsCount"
              color="info"
              inline
            ></v-badge>
          </template>
        </v-list-item>
      </v-list>

      <v-divider class="my-2"></v-divider>

      <v-list density="compact" nav>
        <v-list-item
          v-for="item in secondaryNavItems"
          :key="item.to"
          :to="item.to"
          :prepend-icon="item.icon"
          :title="item.title"
        ></v-list-item>
      </v-list>

      <!-- Admin Section -->
      <template v-if="auth.isAdmin">
        <v-divider class="my-2"></v-divider>

        <v-list density="compact" nav>
          <v-list-subheader class="text-caption font-weight-bold">
            {{ $t('nav.admin.title') }}
          </v-list-subheader>
          <v-list-item
            v-for="item in adminNavItems"
            :key="item.to"
            :to="item.to"
            :prepend-icon="item.icon"
            :title="item.title"
          ></v-list-item>
        </v-list>
      </template>

      <!-- User Info at Bottom -->
      <template #append>
        <v-divider></v-divider>
        <div class="pa-3">
          <div class="d-flex align-center mb-2">
            <v-avatar color="primary" size="32" class="mr-2">
              <span class="text-body-2">{{ userInitials }}</span>
            </v-avatar>
            <div class="flex-grow-1 overflow-hidden">
              <div class="text-body-2 font-weight-medium text-truncate">
                {{ auth.user?.full_name }}
              </div>
              <div class="text-caption text-medium-emphasis text-truncate">
                {{ auth.user?.email }}
              </div>
            </div>
          </div>
          <v-chip size="small" :color="getRoleColor(auth.user?.role)" class="mb-2">
            {{ getRoleLabel(auth.user?.role) }}
          </v-chip>
        </div>
      </template>
    </v-navigation-drawer>

    <!-- App Bar -->
    <v-app-bar v-if="auth.isAuthenticated" app color="primary">
      <v-app-bar-nav-icon :aria-label="$t('common.toggleMenu')" @click="drawer = !drawer"></v-app-bar-nav-icon>
      <v-toolbar-title>CaeliCrawler</v-toolbar-title>
      <v-spacer></v-spacer>

      <!-- Notifications Button -->
      <v-btn icon variant="tonal" :title="$t('nav.notifications')" :aria-label="$t('nav.notifications')" @click="router.push('/notifications')">
        <v-badge
          v-if="unreadCount > 0"
          :content="unreadCount > 99 ? '99+' : unreadCount"
          color="error"
          overlap
        >
          <v-icon aria-hidden="true">mdi-bell-outline</v-icon>
        </v-badge>
        <v-icon v-else aria-hidden="true">mdi-bell-outline</v-icon>
      </v-btn>

      <!-- Language Switcher -->
      <LanguageSwitcher />

      <!-- Theme Toggle -->
      <v-btn
        :icon="isDark ? 'mdi-weather-sunny' : 'mdi-weather-night'"
        variant="tonal"
        :title="$t('user.themeToggle')"
        :aria-label="$t('user.themeToggle')"
        @click="toggleTheme"
      ></v-btn>

      <!-- Refresh -->
      <v-btn icon="mdi-refresh" variant="tonal" :title="$t('user.reloadPage')" :aria-label="$t('user.reloadPage')" @click="refresh"></v-btn>

      <!-- User Menu -->
      <v-menu>
        <template #activator="{ props }">
          <v-btn icon v-bind="props" :title="$t('user.userMenu')" :aria-label="$t('user.userMenu')">
            <v-avatar color="secondary" size="32">
              <span class="text-body-2">{{ userInitials }}</span>
            </v-avatar>
          </v-btn>
        </template>
        <v-list density="compact" min-width="200">
          <v-list-item>
            <v-list-item-title class="font-weight-medium">
              {{ auth.user?.full_name }}
            </v-list-item-title>
            <v-list-item-subtitle>{{ auth.user?.email }}</v-list-item-subtitle>
          </v-list-item>
          <v-divider></v-divider>
          <v-list-item @click="openPasswordDialog">
            <template #prepend>
              <v-icon>mdi-lock-reset</v-icon>
            </template>
            <v-list-item-title>{{ $t('auth.changePassword') }}</v-list-item-title>
          </v-list-item>
          <v-divider></v-divider>
          <v-list-item class="text-error" @click="logout">
            <template #prepend>
              <v-icon color="error">mdi-logout</v-icon>
            </template>
            <v-list-item-title>{{ $t('auth.logout') }}</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </v-app-bar>

    <v-main>
      <v-container fluid>
        <ErrorBoundary>
          <router-view></router-view>
        </ErrorBoundary>
      </v-container>
    </v-main>

    <!-- Password Change Dialog -->
    <v-dialog v-model="passwordDialogOpen" max-width="400" role="dialog" aria-modal="true">
      <v-card>
        <v-card-title>{{ $t('auth.changePassword') }}</v-card-title>
        <v-card-text class="pt-4">
          <v-form @submit.prevent="changePassword">
            <v-text-field
              v-model="currentPassword"
              :label="$t('auth.currentPassword')"
              type="password"
              variant="outlined"
              class="mb-3"
            />
            <v-text-field
              v-model="newPassword"
              :label="$t('auth.newPassword')"
              type="password"
              :rules="[v => v.length >= 8 || $t('auth.validation.passwordMinLength', { min: 8 })]"
              variant="outlined"
              class="mb-3"
            />
            <v-text-field
              v-model="confirmPassword"
              :label="$t('auth.confirmPassword')"
              type="password"
              :rules="[v => v === newPassword || $t('auth.validation.passwordsDoNotMatch')]"
              variant="outlined"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="tonal" @click="passwordDialogOpen = false">
            {{ $t('common.cancel') }}
          </v-btn>
          <v-btn
            color="primary"
            :loading="passwordLoading"
            :disabled="!isPasswordValid"
            @click="changePassword"
          >
            {{ $t('common.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Global Snackbar -->
    <v-snackbar
      v-model="snackbar"
      :color="snackbarColor"
      :timeout="snackbarTimeout"
      location="bottom right"
      role="alert"
      aria-live="polite"
    >
      {{ snackbarText }}
      <template #actions>
        <v-btn variant="tonal" :aria-label="$t('common.close')" @click="snackbar = false">
          <v-icon aria-hidden="true">mdi-close</v-icon>
        </v-btn>
      </template>
    </v-snackbar>

    <!-- AI Chat Assistant -->
    <ChatAssistant v-if="auth.isAuthenticated" />

    <!-- ARIA Live Regions for screen reader announcements -->
    <AriaLiveRegion />
  </v-app>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme, useLocale } from 'vuetify'
import { useI18n } from 'vue-i18n'
import CaeliWindLogo from './components/CaeliWindLogo.vue'
import ChatAssistant from './components/assistant/ChatAssistant.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'
import AriaLiveRegion from './components/AriaLiveRegion.vue'
import { ErrorBoundary } from './components/common'
import { useSnackbar } from './composables/useSnackbar'
import { useAuthStore } from './stores/auth'
import { useNotifications } from './composables/useNotifications'
import { useFeatureFlags } from './composables/useFeatureFlags'
import { dataApi } from './services/api'
import { setLocale, type SupportedLocale } from './locales'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('App')

const { snackbar, snackbarText, snackbarColor, snackbarTimeout, showMessage } = useSnackbar()
const { t, locale } = useI18n()
const vuetifyLocale = useLocale()

// Badge counts for navigation
const pendingDocsCount = ref(0)
const unverifiedResultsCount = ref(0)
const { unreadCount, loadUnreadCount } = useNotifications()
const { loadFeatureFlags } = useFeatureFlags()

const drawer = ref(true)
const router = useRouter()
const theme = useTheme()
const auth = useAuthStore()

// Password change dialog
const passwordDialogOpen = ref(false)
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const passwordLoading = ref(false)

const isPasswordValid = computed(() =>
  currentPassword.value.length > 0 &&
  newPassword.value.length >= 8 &&
  newPassword.value === confirmPassword.value
)

// Navigation items (computed for reactivity with locale changes)
const mainNavItems = computed(() => {
  const items = [
    { title: t('nav.dashboard'), icon: 'mdi-view-dashboard', to: '/' },
    { title: t('nav.entities'), icon: 'mdi-database', to: '/entities' },
    { title: t('nav.entityTypes'), icon: 'mdi-shape', to: '/admin/entity-types' },
    { title: t('nav.facetTypes'), icon: 'mdi-tag-multiple', to: '/admin/facet-types' },
    { title: t('nav.categories'), icon: 'mdi-folder-multiple', to: '/categories', requiresEditor: true },
    { title: t('nav.dataSources'), icon: 'mdi-web', to: '/sources', requiresEditor: true },
    { title: t('nav.crawlerStatus'), icon: 'mdi-robot', to: '/crawler', requiresEditor: true },
    { title: t('nav.documents'), icon: 'mdi-file-document-multiple', to: '/documents' },
    { title: t('nav.results'), icon: 'mdi-chart-box', to: '/results' },
    { title: t('nav.smartQuery'), icon: 'mdi-head-question', to: '/smart-query' },
    { title: t('nav.export'), icon: 'mdi-export', to: '/export' },
  ]

  return items.filter((item) => !item.requiresEditor || auth.isEditor)
})

const secondaryNavItems = computed(() => [
  { title: t('nav.favorites'), icon: 'mdi-star', to: '/favorites' },
  { title: t('nav.summaries'), icon: 'mdi-view-dashboard-variant', to: '/summaries' },
  { title: t('nav.notifications'), icon: 'mdi-bell-outline', to: '/notifications' },
  { title: t('nav.help'), icon: 'mdi-help-circle-outline', to: '/help' },
])

const adminNavItems = computed(() => [
  { title: t('nav.admin.users'), icon: 'mdi-account-group', to: '/admin/users' },
  { title: t('nav.admin.auditLog'), icon: 'mdi-history', to: '/admin/audit-log' },
])

// User helpers
const userInitials = computed(() => {
  const name = auth.user?.full_name || auth.user?.email || '?'
  const parts = name.split(' ')
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return name.substring(0, 2).toUpperCase()
})

function getRoleColor(role?: string): string {
  const colors: Record<string, string> = {
    ADMIN: 'error',
    EDITOR: 'primary',
    VIEWER: 'grey',
  }
  return colors[role || ''] || 'grey'
}

function getRoleLabel(role?: string): string {
  if (!role) return ''
  return t(`roles.${role}`)
}

// Theme
const isDark = computed(() => theme.global.current.value.dark)

const toggleTheme = () => {
  const newTheme = isDark.value ? 'caeliLight' : 'caeliDark'
  theme.change(newTheme)
  localStorage.setItem('caeli-theme', newTheme)
}

const refresh = () => {
  router.go(0)
}

// Auth actions
async function logout() {
  await auth.logout()
  router.push('/login')
}

function openPasswordDialog() {
  currentPassword.value = ''
  newPassword.value = ''
  confirmPassword.value = ''
  passwordDialogOpen.value = true
}

async function changePassword() {
  if (!isPasswordValid.value) return

  passwordLoading.value = true
  const result = await auth.changePassword(currentPassword.value, newPassword.value)
  passwordLoading.value = false

  if (result.success) {
    passwordDialogOpen.value = false
    showMessage(t('auth.passwordChanged'), 'success')
  } else {
    showMessage(result.error || t('auth.passwordChangeError'), 'error')
  }
}

// Notification polling interval
let notificationInterval: ReturnType<typeof setInterval> | null = null
let badgeInterval: ReturnType<typeof setInterval> | null = null

// Load badge counts for navigation
async function loadBadgeCounts() {
  try {
    const [docsRes, resultsRes] = await Promise.all([
      dataApi.getDocuments({ processing_status: 'PENDING', per_page: 1 }),
      dataApi.getExtractionStats({}),
    ])
    pendingDocsCount.value = docsRes.data.total
    unverifiedResultsCount.value = resultsRes.data.unverified || 0
  } catch (error) {
    logger.error('Failed to load badge counts:', error)
  }
}

// Load notifications and feature flags when authenticated
watch(
  () => auth.isAuthenticated,
  async (isAuth) => {
    if (isAuth) {
      await loadUnreadCount()
      await loadBadgeCounts()
      await loadFeatureFlags()
      // Poll every 60 seconds
      notificationInterval = setInterval(loadUnreadCount, 60000)
      badgeInterval = setInterval(loadBadgeCounts, 60000)
    } else {
      if (notificationInterval) {
        clearInterval(notificationInterval)
        notificationInterval = null
      }
      if (badgeInterval) {
        clearInterval(badgeInterval)
        badgeInterval = null
      }
    }
  },
  { immediate: true }
)

// Initialize user language when logged in
watch(
  () => auth.user?.language,
  (userLanguage) => {
    if (userLanguage) {
      locale.value = userLanguage
      vuetifyLocale.current.value = userLanguage
      setLocale(userLanguage as SupportedLocale)
    }
  },
  { immediate: true }
)

onMounted(() => {
  // Restore theme
  const savedTheme = localStorage.getItem('caeli-theme')
  if (savedTheme && (savedTheme === 'caeliLight' || savedTheme === 'caeliDark')) {
    theme.change(savedTheme)
  }

  // Restore language from localStorage if user not loaded yet
  const savedLanguage = localStorage.getItem('caeli-language')
  if (savedLanguage && !auth.user?.language) {
    locale.value = savedLanguage
    vuetifyLocale.current.value = savedLanguage
  }
})

// Cleanup all intervals on unmount to prevent memory leaks
onUnmounted(() => {
  if (notificationInterval) {
    clearInterval(notificationInterval)
    notificationInterval = null
  }
  if (badgeInterval) {
    clearInterval(badgeInterval)
    badgeInterval = null
  }
})
</script>
