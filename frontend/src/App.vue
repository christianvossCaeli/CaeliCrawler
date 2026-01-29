<template>
  <v-app>
    <!-- Navigation Drawer (only when authenticated) -->
    <v-navigation-drawer v-if="auth.isAuthenticated" v-model="drawer" app>
      <div class="pa-4">
        <CaeliWindLogo :primary-color="isDark ? '#deeec6' : '#113534'" />
      </div>

      <v-divider></v-divider>

      <v-list density="compact" nav>
        <template v-for="group in navGroups" :key="group.title">
          <!-- Group Header -->
          <v-list-subheader class="text-caption font-weight-bold text-uppercase nav-group-header">
            {{ group.title }}
          </v-list-subheader>

          <!-- Group Items -->
          <v-list-item
            v-for="item in group.items"
            :key="item.to"
            :to="item.to"
            class="nav-item-with-step"
          >
            <template #prepend>
              <span v-if="item.step" class="workflow-step">{{ item.step }}</span>
              <v-icon v-else class="nav-icon-spacer">{{ item.icon }}</v-icon>
              <v-icon v-if="item.step">{{ item.icon }}</v-icon>
            </template>
            <v-list-item-title>{{ item.title }}</v-list-item-title>
            <template #append>
              <v-chip
                v-if="item.badge === 'pending' && pendingDocsCount > 0"
                size="x-small"
                color="warning"
                variant="flat"
                class="nav-badge"
              >
                {{ pendingDocsCount > 99 ? '99+' : pendingDocsCount }}
              </v-chip>
              <v-chip
                v-if="item.badge === 'unverified' && unverifiedResultsCount > 0"
                size="x-small"
                color="info"
                variant="flat"
                class="nav-badge"
              >
                {{ unverifiedResultsCount > 99 ? '99+' : unverifiedResultsCount }}
              </v-chip>
            </template>
          </v-list-item>

          <!-- Divider after group -->
          <v-divider v-if="group.showDivider" class="my-2"></v-divider>
        </template>
      </v-list>

      <!-- Admin Section -->
      <template v-if="auth.isAdmin">
        <v-divider class="my-2"></v-divider>

        <v-list density="compact" nav>
          <v-list-subheader class="text-caption font-weight-bold text-uppercase nav-group-header">
            {{ $t('nav.admin.title') }}
          </v-list-subheader>
          <v-list-item
            v-for="item in adminNavItems"
            :key="item.to"
            :to="item.to"
            class="nav-item-with-step"
          >
            <template #prepend>
              <v-icon class="nav-icon-spacer">{{ item.icon }}</v-icon>
            </template>
            <v-list-item-title>{{ item.title }}</v-list-item-title>
          </v-list-item>
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

      <!-- Embedding Progress Indicator -->
      <EmbeddingProgressIndicator class="mr-2" />

      <!-- LLM Budget Status -->
      <LLMUsageStatusBar class="mr-2" />

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
            <v-list-item-title>{{ $t('auth.changePassword.title') }}</v-list-item-title>
          </v-list-item>
          <v-divider></v-divider>
          <v-list-item class="text-error" @click="logout">
            <template #prepend>
              <v-icon color="error">mdi-logout</v-icon>
            </template>
            <v-list-item-title>{{ $t('auth.logout.title') }}</v-list-item-title>
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
    <v-dialog v-model="passwordDialogOpen" :max-width="DIALOG_SIZES.XS" role="dialog" aria-modal="true">
      <v-card>
        <v-card-title>{{ $t('auth.changePassword.title') }}</v-card-title>
        <v-card-text class="pt-4">
          <v-form @submit.prevent="changePassword">
            <v-text-field
              v-model="currentPassword"
              :label="$t('auth.changePassword.currentPassword')"
              type="password"
              variant="outlined"
              class="mb-3"
            />
            <v-text-field
              v-model="newPassword"
              :label="$t('auth.changePassword.newPassword')"
              type="password"
              :rules="[v => v.length >= 8 || $t('auth.validation.passwordMinLength', { min: 8 })]"
              variant="outlined"
              class="mb-3"
            />
            <v-text-field
              v-model="confirmPassword"
              :label="$t('auth.changePassword.confirmPassword')"
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

    <!-- AI Chat Assistant - only render after auth is fully initialized -->
    <ChatAssistant v-if="auth.isAuthenticated && auth.initialized" />

    <!-- ARIA Live Regions for screen reader announcements -->
    <AriaLiveRegion />
  </v-app>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, defineAsyncComponent } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme, useLocale } from 'vuetify'
import { useI18n } from 'vue-i18n'
import CaeliWindLogo from './components/CaeliWindLogo.vue'
// Lazy load ChatAssistant to reduce initial bundle by ~50KB
const ChatAssistant = defineAsyncComponent(() =>
  import('./components/assistant/ChatAssistant.vue')
)
import LanguageSwitcher from './components/LanguageSwitcher.vue'
import AriaLiveRegion from './components/AriaLiveRegion.vue'
import { ErrorBoundary } from './components/common'
import LLMUsageStatusBar from './components/common/LLMUsageStatusBar.vue'
import EmbeddingProgressIndicator from './components/common/EmbeddingProgressIndicator.vue'
import { useSnackbar } from './composables/useSnackbar'
import { storeToRefs } from 'pinia'
import { useAuthStore } from './stores/auth'
import { useNotificationsStore } from './stores/notifications'
import { useFeatureFlags } from './composables/useFeatureFlags'
import { dataApi } from './services/api'
import { setLocale, type SupportedLocale } from './locales'
import { useLogger } from '@/composables/useLogger'
import { DIALOG_SIZES } from '@/config/ui'

const logger = useLogger('App')

const { snackbar, snackbarText, snackbarColor, snackbarTimeout, showMessage } = useSnackbar()
const { t, locale } = useI18n()
const vuetifyLocale = useLocale()

// Badge counts for navigation
const pendingDocsCount = ref(0)
const unverifiedResultsCount = ref(0)
const notificationsStore = useNotificationsStore()
const { unreadCount } = storeToRefs(notificationsStore)
const { initRealtime, cleanupRealtime } = notificationsStore
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

// Navigation item interface
interface NavItem {
  title: string
  icon: string
  to: string
  step?: number
  requiresEditor?: boolean
  badge?: 'pending' | 'unverified'
}

interface NavGroup {
  title: string
  items: NavItem[]
  showDivider?: boolean
}

// Navigation groups (computed for reactivity with locale changes)
const navGroups = computed<NavGroup[]>(() => {
  const groups: NavGroup[] = [
    {
      title: t('nav.groups.workflow'),
      items: [
        { step: 1, title: t('nav.chatHome'), icon: 'mdi-chat-processing-outline', to: '/' },
        { step: 2, title: t('nav.dashboard'), icon: 'mdi-view-dashboard', to: '/dashboard' },
        { step: 3, title: t('nav.entities'), icon: 'mdi-database', to: '/entities' },
        { step: 4, title: t('nav.entityTypes'), icon: 'mdi-shape', to: '/admin/entity-types' },
        { step: 5, title: t('nav.facetTypes'), icon: 'mdi-tag-multiple', to: '/admin/facet-types' },
      ],
    },
    {
      title: t('nav.groups.dataCapture'),
      items: [
        { step: 6, title: t('nav.categories'), icon: 'mdi-folder-multiple', to: '/categories', requiresEditor: true },
        { step: 7, title: t('nav.dataSources'), icon: 'mdi-web', to: '/sources', requiresEditor: true },
        { step: 8, title: t('nav.crawlerStatus'), icon: 'mdi-robot', to: '/crawler', requiresEditor: true },
        { step: 9, title: t('nav.documents'), icon: 'mdi-file-document-multiple', to: '/documents', badge: 'pending' },
      ],
    },
    {
      title: t('nav.groups.analysis'),
      items: [
        { step: 10, title: t('nav.results'), icon: 'mdi-chart-box', to: '/results', badge: 'unverified' },
        { step: 11, title: t('nav.smartQuery'), icon: 'mdi-head-question', to: '/smart-query' },
        { step: 12, title: t('nav.export'), icon: 'mdi-export', to: '/export' },
      ],
      showDivider: true,
    },
    {
      title: t('nav.groups.tools'),
      items: [
        { title: t('nav.favorites'), icon: 'mdi-star', to: '/favorites' },
        { title: t('nav.summaries'), icon: 'mdi-view-dashboard-variant', to: '/summaries' },
        { title: t('nav.notifications'), icon: 'mdi-bell-outline', to: '/notifications' },
        { title: t('nav.help'), icon: 'mdi-help-circle-outline', to: '/help' },
      ],
    },
  ]

  // Filter items based on permissions
  return groups.map((group) => ({
    ...group,
    items: group.items.filter((item) => !item.requiresEditor || auth.isEditor),
  })).filter((group) => group.items.length > 0)
})

const adminNavItems = computed(() => [
  { title: t('nav.admin.users'), icon: 'mdi-account-group', to: '/admin/users' },
  { title: t('nav.admin.auditLog'), icon: 'mdi-history', to: '/admin/audit-log' },
  { title: t('nav.admin.llmUsage'), icon: 'mdi-brain', to: '/admin/llm-usage' },
  { title: t('nav.admin.modelPricing'), icon: 'mdi-currency-usd', to: '/admin/model-pricing' },
  { title: t('nav.admin.llmConfig'), icon: 'mdi-cog-outline', to: '/admin/api-credentials' },
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
    showMessage(t('auth.changePassword.success'), 'success')
  } else {
    showMessage(result.error || t('auth.changePassword.error'), 'error')
  }
}

// Badge counts polling interval (notifications now use SSE)
let badgeInterval: ReturnType<typeof setInterval> | null = null

// Visibility API: pause polling when tab is hidden to save resources
function handleVisibilityChange() {
  if (document.hidden) {
    // Tab is hidden - stop polling
    if (badgeInterval) {
      clearInterval(badgeInterval)
      badgeInterval = null
    }
  } else {
    // Tab is visible again - resume polling if authenticated
    if (auth.isAuthenticated && auth.initialized && !badgeInterval) {
      loadBadgeCounts() // Immediate refresh
      badgeInterval = setInterval(loadBadgeCounts, 60000)
    }
  }
}

// Load badge counts for navigation
async function loadBadgeCounts() {
  try {
    const [docsRes, resultsRes] = await Promise.all([
      dataApi.getDocumentStats(),
      dataApi.getUnverifiedCount(),
    ])
    pendingDocsCount.value = docsRes.data.by_status?.PENDING || 0
    unverifiedResultsCount.value = resultsRes.data.unverified || 0
  } catch (error) {
    logger.error('Failed to load badge counts:', error)
  }
}

// Load notifications and feature flags when authenticated
// Wait for auth.initialized to avoid race conditions with token validation
watch(
  [() => auth.isAuthenticated, () => auth.initialized],
  async ([isAuth, isInitialized]) => {
    // Only proceed if auth initialization is complete
    if (!isInitialized) return

    if (isAuth) {
      await loadBadgeCounts()
      await loadFeatureFlags()
      // Initialize real-time notifications (SSE with polling fallback)
      await initRealtime()
      badgeInterval = setInterval(loadBadgeCounts, 60000)
    } else {
      // Cleanup SSE and polling
      cleanupRealtime()
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

  // Register visibility change handler to pause polling when tab is hidden
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

// Cleanup all resources on unmount to prevent memory leaks
onUnmounted(() => {
  // Remove visibility change listener
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  // Cleanup SSE and any polling fallback
  cleanupRealtime()
  if (badgeInterval) {
    clearInterval(badgeInterval)
    badgeInterval = null
  }
})
</script>

<style scoped>
/* Navigation Group Styling */
.nav-group-header {
  margin-top: 8px;
  padding-left: 16px;
}

/* Workflow Step Number */
.workflow-step {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: rgba(var(--v-theme-primary), 0.15);
  color: rgb(var(--v-theme-primary));
  font-size: 11px;
  font-weight: 600;
  margin-right: 4px;
  flex-shrink: 0;
}

/* Reduce spacing between prepend icon and text - override Vuetify defaults */
.nav-item-with-step :deep(.v-list-item__prepend) {
  margin-inline-end: 8px !important;
}

/* Hide the spacer that Vuetify adds automatically */
.nav-item-with-step :deep(.v-list-item__spacer) {
  display: none !important;
}

/* Spacer for items without step number to align icons */
.nav-icon-spacer {
  margin-right: 0 !important;
  margin-inline-end: 0 !important;
}

/* Active state styling for workflow steps - use contrast colors */
.v-list-item--active .workflow-step {
  background: rgba(var(--v-theme-on-surface), 0.9);
  color: rgb(var(--v-theme-surface));
}

/* Ensure title doesn't get cut off */
.nav-item-with-step :deep(.v-list-item-title) {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Compact chip badge styling */
.nav-badge {
  flex-shrink: 0;
  font-size: 10px !important;
  height: 16px !important;
  padding: 0 5px !important;
  margin-left: 4px;
}

.nav-badge :deep(.v-chip__content) {
  padding: 0;
}
</style>
