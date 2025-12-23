/**
 * Vitest Test Setup
 *
 * This file runs before all tests to set up the test environment.
 */

import { vi, afterEach } from 'vitest'

// Mock vue-i18n
vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string, fallback?: string) => fallback || key,
    locale: { value: 'de' },
  }),
  createI18n: vi.fn(),
}))

// Mock API service
vi.mock('@/services/api', () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

// Mock localStorage - return null or valid JSON to avoid JSON.parse errors
const localStorageMock = {
  getItem: vi.fn((key: string) => {
    // Return null for most keys to avoid JSON.parse errors
    if (key === 'auth_token') return 'mock-token'
    return null
  }),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

// Mock fetch for SSE streaming
global.fetch = vi.fn()

// Clean up after each test
afterEach(() => {
  vi.clearAllMocks()
})
