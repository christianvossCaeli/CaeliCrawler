/**
 * Unit tests for the authentication store
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from './auth'

// Mock the API module
vi.mock('@/services/api', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
    put: vi.fn(),
    defaults: {
      headers: {
        common: {},
      },
    },
  },
}))

// Mock vue-i18n
vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string) => key,
  }),
}))

// Mock useLogger
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}))

// Import the mocked api after vi.mock
import api from '@/services/api'

describe('Auth Store', () => {
  let store: ReturnType<typeof useAuthStore>

  beforeEach(() => {
    // Clear localStorage
    localStorage.clear()

    // Reset all mocks
    vi.clearAllMocks()

    // Create fresh Pinia instance
    setActivePinia(createPinia())
    store = useAuthStore()
  })

  afterEach(() => {
    localStorage.clear()
  })

  // ==========================================================================
  // Initial State
  // ==========================================================================

  describe('Initial State', () => {
    it('has correct default state', () => {
      expect(store.user).toBeNull()
      expect(store.isLoading).toBe(false)
      expect(store.error).toBeNull()
      expect(store.isRefreshing).toBe(false)
    })

    it('is not authenticated by default', () => {
      expect(store.isAuthenticated).toBe(false)
    })

    it('has no admin/editor privileges by default', () => {
      // When user is null, these should be falsy (false or undefined)
      expect(store.isAdmin).toBeFalsy()
      expect(store.isEditor).toBeFalsy()
    })
  })

  // ==========================================================================
  // Login
  // ==========================================================================

  describe('login', () => {
    const mockLoginResponse = {
      data: {
        access_token: 'test-access-token',
        refresh_token: 'test-refresh-token',
        expires_in: 3600,
        refresh_expires_in: 604800,
        user: {
          id: '123',
          email: 'test@example.com',
          full_name: 'Test User',
          role: 'EDITOR' as const,
          is_active: true,
          is_superuser: false,
          last_login: null,
          created_at: '2024-01-01T00:00:00Z',
          language: 'de',
        },
      },
    }

    it('successfully logs in with valid credentials', async () => {
      vi.mocked(api.post).mockResolvedValueOnce(mockLoginResponse)

      const result = await store.login('test@example.com', 'password123')

      expect(result).toBe(true)
      expect(store.user).toEqual(mockLoginResponse.data.user)
      expect(store.token).toBe('test-access-token')
      expect(store.refreshToken).toBe('test-refresh-token')
      expect(store.isAuthenticated).toBe(true)
      expect(store.error).toBeNull()
    })

    it('stores tokens in store state on successful login', async () => {
      vi.mocked(api.post).mockResolvedValueOnce(mockLoginResponse)

      await store.login('test@example.com', 'password123')

      // Verify tokens are stored in store state
      expect(store.token).toBe('test-access-token')
      expect(store.refreshToken).toBe('test-refresh-token')
      expect(store.tokenExpiry).toBeTruthy()
      // Token expiry should be approximately expires_in seconds from now
      expect(store.tokenExpiry).toBeGreaterThan(Date.now())
    })

    it('sets Authorization header on successful login', async () => {
      vi.mocked(api.post).mockResolvedValueOnce(mockLoginResponse)

      await store.login('test@example.com', 'password123')

      expect(api.defaults.headers.common['Authorization']).toBe('Bearer test-access-token')
    })

    it('handles login failure', async () => {
      const mockError = {
        response: {
          data: {
            detail: 'Invalid email or password',
          },
        },
      }
      vi.mocked(api.post).mockRejectedValueOnce(mockError)

      const result = await store.login('wrong@example.com', 'wrongpassword')

      expect(result).toBe(false)
      expect(store.user).toBeNull()
      expect(store.token).toBeNull()
      expect(store.isAuthenticated).toBe(false)
      expect(store.error).toBe('Invalid email or password')
    })

    it('uses error message on login failure', async () => {
      vi.mocked(api.post).mockRejectedValueOnce(new Error('Network error'))

      const result = await store.login('test@example.com', 'password123')

      expect(result).toBe(false)
      // Uses actual error message when available
      expect(store.error).toBe('Network error')
    })

    it('sets isLoading during login', async () => {
      let resolvePromise: (value: unknown) => void
      const pendingPromise = new Promise((resolve) => {
        resolvePromise = resolve
      })
      vi.mocked(api.post).mockReturnValueOnce(pendingPromise as never)

      const loginPromise = store.login('test@example.com', 'password123')

      expect(store.isLoading).toBe(true)

      resolvePromise!(mockLoginResponse)
      await loginPromise

      expect(store.isLoading).toBe(false)
    })
  })

  // ==========================================================================
  // Logout
  // ==========================================================================

  describe('logout', () => {
    beforeEach(async () => {
      // Setup logged in state
      vi.mocked(api.post).mockResolvedValueOnce({
        data: {
          access_token: 'test-token',
          refresh_token: 'test-refresh',
          expires_in: 3600,
          refresh_expires_in: 604800,
          user: {
            id: '123',
            email: 'test@example.com',
            full_name: 'Test User',
            role: 'VIEWER' as const,
            is_active: true,
            is_superuser: false,
            last_login: null,
            created_at: '2024-01-01T00:00:00Z',
            language: 'de',
          },
        },
      })
      await store.login('test@example.com', 'password')
    })

    it('clears user state on logout', async () => {
      vi.mocked(api.post).mockResolvedValueOnce({})

      await store.logout()

      expect(store.user).toBeNull()
      expect(store.token).toBeNull()
      expect(store.refreshToken).toBeNull()
      expect(store.tokenExpiry).toBeNull()
      expect(store.isAuthenticated).toBe(false)
    })

    it('clears localStorage on logout', async () => {
      vi.mocked(api.post).mockResolvedValueOnce({})

      await store.logout()

      expect(localStorage.getItem('caeli_auth_token')).toBeNull()
      expect(localStorage.getItem('caeli_refresh_token')).toBeNull()
      expect(localStorage.getItem('caeli_token_expiry')).toBeNull()
    })

    it('clears Authorization header on logout', async () => {
      vi.mocked(api.post).mockResolvedValueOnce({})

      await store.logout()

      expect(api.defaults.headers.common['Authorization']).toBeUndefined()
    })

    it('completes logout even if server call fails', async () => {
      vi.mocked(api.post).mockRejectedValueOnce(new Error('Network error'))

      await store.logout()

      expect(store.user).toBeNull()
      expect(store.token).toBeNull()
    })
  })

  // ==========================================================================
  // Role Checking
  // ==========================================================================

  describe('hasRole', () => {
    it('returns false when user is not logged in', () => {
      expect(store.hasRole('VIEWER')).toBe(false)
      expect(store.hasRole('EDITOR')).toBe(false)
      expect(store.hasRole('ADMIN')).toBe(false)
    })

    it('correctly checks VIEWER role', async () => {
      vi.mocked(api.post).mockResolvedValueOnce({
        data: {
          access_token: 'test',
          refresh_token: 'test',
          expires_in: 3600,
          refresh_expires_in: 604800,
          user: {
            id: '123',
            email: 'viewer@example.com',
            full_name: 'Viewer',
            role: 'VIEWER' as const,
            is_active: true,
            is_superuser: false,
            last_login: null,
            created_at: '2024-01-01T00:00:00Z',
            language: 'de',
          },
        },
      })
      await store.login('viewer@example.com', 'password')

      expect(store.hasRole('VIEWER')).toBe(true)
      expect(store.hasRole('EDITOR')).toBe(false)
      expect(store.hasRole('ADMIN')).toBe(false)
    })

    it('correctly checks EDITOR role (includes VIEWER)', async () => {
      vi.mocked(api.post).mockResolvedValueOnce({
        data: {
          access_token: 'test',
          refresh_token: 'test',
          expires_in: 3600,
          refresh_expires_in: 604800,
          user: {
            id: '123',
            email: 'editor@example.com',
            full_name: 'Editor',
            role: 'EDITOR' as const,
            is_active: true,
            is_superuser: false,
            last_login: null,
            created_at: '2024-01-01T00:00:00Z',
            language: 'de',
          },
        },
      })
      await store.login('editor@example.com', 'password')

      expect(store.hasRole('VIEWER')).toBe(true)
      expect(store.hasRole('EDITOR')).toBe(true)
      expect(store.hasRole('ADMIN')).toBe(false)
    })

    it('correctly checks ADMIN role (includes all)', async () => {
      vi.mocked(api.post).mockResolvedValueOnce({
        data: {
          access_token: 'test',
          refresh_token: 'test',
          expires_in: 3600,
          refresh_expires_in: 604800,
          user: {
            id: '123',
            email: 'admin@example.com',
            full_name: 'Admin',
            role: 'ADMIN' as const,
            is_active: true,
            is_superuser: false,
            last_login: null,
            created_at: '2024-01-01T00:00:00Z',
            language: 'de',
          },
        },
      })
      await store.login('admin@example.com', 'password')

      expect(store.hasRole('VIEWER')).toBe(true)
      expect(store.hasRole('EDITOR')).toBe(true)
      expect(store.hasRole('ADMIN')).toBe(true)
    })

    it('superuser has all roles', async () => {
      vi.mocked(api.post).mockResolvedValueOnce({
        data: {
          access_token: 'test',
          refresh_token: 'test',
          expires_in: 3600,
          refresh_expires_in: 604800,
          user: {
            id: '123',
            email: 'super@example.com',
            full_name: 'Super',
            role: 'VIEWER' as const,
            is_active: true,
            is_superuser: true,
            last_login: null,
            created_at: '2024-01-01T00:00:00Z',
            language: 'de',
          },
        },
      })
      await store.login('super@example.com', 'password')

      expect(store.hasRole('VIEWER')).toBe(true)
      expect(store.hasRole('EDITOR')).toBe(true)
      expect(store.hasRole('ADMIN')).toBe(true)
    })
  })

  // ==========================================================================
  // Computed Properties
  // ==========================================================================

  describe('computed properties', () => {
    it('isAdmin returns true for ADMIN role', async () => {
      vi.mocked(api.post).mockResolvedValueOnce({
        data: {
          access_token: 'test',
          refresh_token: 'test',
          expires_in: 3600,
          refresh_expires_in: 604800,
          user: {
            id: '123',
            email: 'admin@example.com',
            full_name: 'Admin',
            role: 'ADMIN' as const,
            is_active: true,
            is_superuser: false,
            last_login: null,
            created_at: '2024-01-01T00:00:00Z',
            language: 'de',
          },
        },
      })
      await store.login('admin@example.com', 'password')

      expect(store.isAdmin).toBe(true)
    })

    it('isAdmin returns true for superuser', async () => {
      vi.mocked(api.post).mockResolvedValueOnce({
        data: {
          access_token: 'test',
          refresh_token: 'test',
          expires_in: 3600,
          refresh_expires_in: 604800,
          user: {
            id: '123',
            email: 'super@example.com',
            full_name: 'Super',
            role: 'VIEWER' as const,
            is_active: true,
            is_superuser: true,
            last_login: null,
            created_at: '2024-01-01T00:00:00Z',
            language: 'de',
          },
        },
      })
      await store.login('super@example.com', 'password')

      expect(store.isAdmin).toBe(true)
    })

    it('isEditor returns true for EDITOR and ADMIN', async () => {
      vi.mocked(api.post).mockResolvedValueOnce({
        data: {
          access_token: 'test',
          refresh_token: 'test',
          expires_in: 3600,
          refresh_expires_in: 604800,
          user: {
            id: '123',
            email: 'editor@example.com',
            full_name: 'Editor',
            role: 'EDITOR' as const,
            is_active: true,
            is_superuser: false,
            last_login: null,
            created_at: '2024-01-01T00:00:00Z',
            language: 'de',
          },
        },
      })
      await store.login('editor@example.com', 'password')

      expect(store.isEditor).toBe(true)
    })

    it('userDisplayName returns full_name or email', async () => {
      vi.mocked(api.post).mockResolvedValueOnce({
        data: {
          access_token: 'test',
          refresh_token: 'test',
          expires_in: 3600,
          refresh_expires_in: 604800,
          user: {
            id: '123',
            email: 'test@example.com',
            full_name: 'Test User',
            role: 'VIEWER' as const,
            is_active: true,
            is_superuser: false,
            last_login: null,
            created_at: '2024-01-01T00:00:00Z',
            language: 'de',
          },
        },
      })
      await store.login('test@example.com', 'password')

      expect(store.userDisplayName).toBe('Test User')
    })
  })

  // ==========================================================================
  // Token Expiry
  // ==========================================================================

  describe('isTokenExpired', () => {
    it('returns true when no token expiry is set', () => {
      expect(store.isTokenExpired()).toBe(true)
    })

    it('returns true when token is expired', async () => {
      vi.mocked(api.post).mockResolvedValueOnce({
        data: {
          access_token: 'test',
          refresh_token: 'test',
          expires_in: -1, // Already expired
          refresh_expires_in: 604800,
          user: {
            id: '123',
            email: 'test@example.com',
            full_name: 'Test',
            role: 'VIEWER' as const,
            is_active: true,
            is_superuser: false,
            last_login: null,
            created_at: '2024-01-01T00:00:00Z',
            language: 'de',
          },
        },
      })
      await store.login('test@example.com', 'password')

      expect(store.isTokenExpired()).toBe(true)
    })

    it('returns false when token is valid', async () => {
      vi.mocked(api.post).mockResolvedValueOnce({
        data: {
          access_token: 'test',
          refresh_token: 'test',
          expires_in: 3600, // 1 hour
          refresh_expires_in: 604800,
          user: {
            id: '123',
            email: 'test@example.com',
            full_name: 'Test',
            role: 'VIEWER' as const,
            is_active: true,
            is_superuser: false,
            last_login: null,
            created_at: '2024-01-01T00:00:00Z',
            language: 'de',
          },
        },
      })
      await store.login('test@example.com', 'password')

      expect(store.isTokenExpired()).toBe(false)
    })
  })

  // ==========================================================================
  // Password Change
  // ==========================================================================

  describe('changePassword', () => {
    beforeEach(async () => {
      vi.mocked(api.post).mockResolvedValueOnce({
        data: {
          access_token: 'test',
          refresh_token: 'test',
          expires_in: 3600,
          refresh_expires_in: 604800,
          user: {
            id: '123',
            email: 'test@example.com',
            full_name: 'Test',
            role: 'VIEWER' as const,
            is_active: true,
            is_superuser: false,
            last_login: null,
            created_at: '2024-01-01T00:00:00Z',
            language: 'de',
          },
        },
      })
      await store.login('test@example.com', 'password')
    })

    it('successfully changes password', async () => {
      vi.mocked(api.post).mockResolvedValueOnce({})

      const result = await store.changePassword('oldPassword', 'newPassword')

      expect(result.success).toBe(true)
      expect(result.error).toBeUndefined()
    })

    it('handles password change failure', async () => {
      vi.mocked(api.post).mockRejectedValueOnce({
        response: {
          data: {
            detail: 'Current password is incorrect',
          },
        },
      })

      const result = await store.changePassword('wrongPassword', 'newPassword')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Current password is incorrect')
    })

    it('uses error message on password change failure', async () => {
      vi.mocked(api.post).mockRejectedValueOnce(new Error('Network error'))

      const result = await store.changePassword('oldPassword', 'newPassword')

      expect(result.success).toBe(false)
      // Uses actual error message when available
      expect(result.error).toBe('Network error')
    })
  })
})
