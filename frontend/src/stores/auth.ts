/**
 * Authentication Store
 *
 * Manages user authentication state, JWT tokens, and role-based access control.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('AuthStore')

// Types
export type UserRole = 'VIEWER' | 'EDITOR' | 'ADMIN'

export interface User {
  id: string
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
  is_superuser: boolean
  last_login: string | null
  created_at: string
  language: string
}

interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  refresh_expires_in: number
  user: User
}

// Token storage keys
const TOKEN_KEY = 'caeli_auth_token'
const REFRESH_TOKEN_KEY = 'caeli_refresh_token'
const TOKEN_EXPIRY_KEY = 'caeli_token_expiry'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const refreshToken = ref<string | null>(localStorage.getItem(REFRESH_TOKEN_KEY))
  const tokenExpiry = ref<number | null>(
    localStorage.getItem(TOKEN_EXPIRY_KEY) ? parseInt(localStorage.getItem(TOKEN_EXPIRY_KEY)!) : null
  )
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const initialized = ref(false)
  const isRefreshing = ref(false)

  // Computed
  const isAuthenticated = computed(() => !!token.value && !!user.value)

  const isAdmin = computed(() => user.value?.role === 'ADMIN' || user.value?.is_superuser)

  const isEditor = computed(() =>
    ['ADMIN', 'EDITOR'].includes(user.value?.role || '') || user.value?.is_superuser
  )

  const isViewer = computed(() =>
    ['ADMIN', 'EDITOR', 'VIEWER'].includes(user.value?.role || '') || user.value?.is_superuser
  )

  const canEdit = computed(() => isEditor.value)
  const canView = computed(() => isAuthenticated.value)

  const userDisplayName = computed(() => user.value?.full_name || user.value?.email || 'Unknown')

  // Actions
  function setAuthHeader(tokenValue: string | null) {
    if (tokenValue) {
      api.defaults.headers.common['Authorization'] = `Bearer ${tokenValue}`
    } else {
      delete api.defaults.headers.common['Authorization']
    }
  }

  async function login(email: string, password: string): Promise<boolean> {
    isLoading.value = true
    error.value = null

    try {
      const response = await api.post<LoginResponse>('/auth/login', {
        email,
        password,
      })

      token.value = response.data.access_token
      refreshToken.value = response.data.refresh_token
      user.value = response.data.user

      // Calculate token expiry timestamp
      const expiryTime = Date.now() + (response.data.expires_in * 1000)
      tokenExpiry.value = expiryTime

      // Persist tokens
      localStorage.setItem(TOKEN_KEY, response.data.access_token)
      localStorage.setItem(REFRESH_TOKEN_KEY, response.data.refresh_token)
      localStorage.setItem(TOKEN_EXPIRY_KEY, expiryTime.toString())

      // Set auth header for future requests
      setAuthHeader(response.data.access_token)

      return true
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Login fehlgeschlagen'
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function refreshAccessToken(): Promise<boolean> {
    if (!refreshToken.value || isRefreshing.value) {
      return false
    }

    isRefreshing.value = true

    try {
      const response = await api.post<LoginResponse>('/auth/refresh', {
        refresh_token: refreshToken.value,
      })

      token.value = response.data.access_token
      user.value = response.data.user

      // Calculate new token expiry timestamp
      const expiryTime = Date.now() + (response.data.expires_in * 1000)
      tokenExpiry.value = expiryTime

      // Persist new access token
      localStorage.setItem(TOKEN_KEY, response.data.access_token)
      localStorage.setItem(TOKEN_EXPIRY_KEY, expiryTime.toString())

      // Set auth header for future requests
      setAuthHeader(response.data.access_token)

      return true
    } catch (err: any) {
      // Refresh token is invalid, log out
      await logout()
      return false
    } finally {
      isRefreshing.value = false
    }
  }

  function isTokenExpired(): boolean {
    if (!tokenExpiry.value) return true
    // Consider token expired 30 seconds before actual expiry
    return Date.now() > (tokenExpiry.value - 30000)
  }

  async function logout(): Promise<void> {
    try {
      // Optionally notify server
      if (token.value) {
        await api.post('/auth/logout').catch(() => {
          // Ignore logout errors
        })
      }
    } finally {
      // Clear state
      token.value = null
      refreshToken.value = null
      tokenExpiry.value = null
      user.value = null
      error.value = null

      // Clear storage
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(REFRESH_TOKEN_KEY)
      localStorage.removeItem(TOKEN_EXPIRY_KEY)

      // Clear auth header
      setAuthHeader(null)
    }
  }

  async function fetchCurrentUser(): Promise<boolean> {
    if (!token.value) {
      initialized.value = true
      return false
    }

    isLoading.value = true

    try {
      // Set auth header first
      setAuthHeader(token.value)

      const response = await api.get<User>('/auth/me')
      user.value = response.data
      initialized.value = true
      return true
    } catch (err) {
      // Token is invalid or expired
      await logout()
      initialized.value = true
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function changePassword(
    currentPassword: string,
    newPassword: string
  ): Promise<{ success: boolean; error?: string }> {
    try {
      await api.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      })
      return { success: true }
    } catch (err: any) {
      return {
        success: false,
        error: err.response?.data?.detail || 'Passwortänderung fehlgeschlagen',
      }
    }
  }

  function hasRole(role: UserRole): boolean {
    if (!user.value) return false
    if (user.value.is_superuser) return true

    const roleHierarchy: Record<UserRole, number> = {
      VIEWER: 1,
      EDITOR: 2,
      ADMIN: 3,
    }

    return roleHierarchy[user.value.role] >= roleHierarchy[role]
  }

  async function updateLanguage(language: string): Promise<boolean> {
    try {
      await api.put('/auth/language', { language })
      if (user.value) {
        user.value.language = language
      }
      return true
    } catch (err) {
      logger.error('Failed to update language preference:', err)
      return false
    }
  }

  // Initialize on store creation
  if (token.value && !initialized.value) {
    fetchCurrentUser()
  } else {
    initialized.value = true
  }

  return {
    // State
    user,
    token,
    refreshToken,
    tokenExpiry,
    isLoading,
    error,
    initialized,
    isRefreshing,

    // Computed
    isAuthenticated,
    isAdmin,
    isEditor,
    isViewer,
    canEdit,
    canView,
    userDisplayName,

    // Actions
    login,
    logout,
    fetchCurrentUser,
    changePassword,
    hasRole,
    updateLanguage,
    refreshAccessToken,
    isTokenExpired,
  }
})
