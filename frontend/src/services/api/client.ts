import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import type { Router } from 'vue-router'

// Default timeout for all requests (30 seconds)
const DEFAULT_TIMEOUT = 30000

export const api = axios.create({
  baseURL: '/api',
  timeout: DEFAULT_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Track if we're currently refreshing to prevent multiple refresh attempts
let isRefreshing = false
let failedQueue: Array<{
  resolve: (value?: unknown) => void
  reject: (reason?: unknown) => void
}> = []

const processQueue = (error: Error | null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve()
    }
  })
  failedQueue = []
}

/**
 * Clear authentication state and redirect to login.
 * Used when token refresh fails or auth endpoints return 401.
 */
async function clearAuthAndRedirect(router: Router) {
  const { useAuthStore } = await import('@/stores/auth')
  const auth = useAuthStore()

  // Clear auth state without API call (server already rejected us)
  auth.token = null
  auth.refreshToken = null
  auth.tokenExpiry = null
  auth.user = null
  localStorage.removeItem('caeli_auth_token')
  localStorage.removeItem('caeli_refresh_token')
  localStorage.removeItem('caeli_token_expiry')
  delete api.defaults.headers.common['Authorization']

  // Redirect to login if not already there
  if (router.currentRoute.value.name !== 'login') {
    router.push({
      name: 'login',
      query: { redirect: router.currentRoute.value.fullPath }
    })
  }
}

/**
 * Setup request and response interceptors for authentication handling.
 * Must be called after Pinia is initialized.
 *
 * Request interceptor: Automatically adds Authorization header from stored token
 * Response interceptor: Handles 401 errors with automatic token refresh
 */
export function setupApiInterceptors(router: Router) {
  // Request interceptor - add auth header
  api.interceptors.request.use(
    (config) => {
      // Get token from localStorage (more reliable than store during initialization)
      const token = localStorage.getItem('caeli_auth_token')
      if (token && !config.headers['Authorization']) {
        config.headers['Authorization'] = `Bearer ${token}`
      }
      return config
    },
    (error) => Promise.reject(error)
  )

  // Response interceptor - handle 401 and token refresh
  api.interceptors.response.use(
    response => response,
    async (error: AxiosError) => {
      const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

      // Only handle 401 errors
      if (error.response?.status !== 401) {
        return Promise.reject(error)
      }

      // Don't retry auth endpoints to prevent loops
      const isAuthEndpoint = originalRequest?.url?.includes('/auth/me') ||
                            originalRequest?.url?.includes('/auth/refresh') ||
                            originalRequest?.url?.includes('/auth/login')

      if (isAuthEndpoint || originalRequest?._retry) {
        // For auth endpoints, clear local auth and redirect to login
        await clearAuthAndRedirect(router)
        return Promise.reject(error)
      }

      // Try to refresh the token
      if (isRefreshing) {
        // If already refreshing, queue this request
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(() => {
          return api(originalRequest)
        }).catch(err => {
          return Promise.reject(err)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const { useAuthStore } = await import('@/stores/auth')
        const auth = useAuthStore()

        if (!auth.refreshToken) {
          throw new Error('No refresh token')
        }

        const success = await auth.refreshAccessToken()

        if (success) {
          processQueue(null)
          // Update the authorization header for the original request
          originalRequest.headers['Authorization'] = `Bearer ${auth.token}`
          return api(originalRequest)
        } else {
          throw new Error('Token refresh failed')
        }
      } catch (refreshError) {
        processQueue(refreshError as Error)

        // Refresh failed - logout and redirect
        await clearAuthAndRedirect(router)

        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }
  )
}

export default api
