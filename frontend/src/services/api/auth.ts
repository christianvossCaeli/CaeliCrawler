import { api } from './client'

// Auth API
export const login = (data: { email: string; password: string }) => api.post('/auth/login', data)
export const logout = () => api.post('/auth/logout')
export const getMe = () => api.get('/auth/me')
export const changePassword = (data: { current_password: string; new_password: string }) =>
  api.post('/auth/change-password', data)
export const checkPasswordStrength = (password: string) =>
  api.post<{
    is_valid: boolean
    score: number
    errors: string[]
    suggestions: string[]
    requirements: string
  }>('/auth/check-password-strength', { password })

// Language preference
export const updateLanguage = (language: 'de' | 'en') =>
  api.put('/auth/language', { language })

// Token refresh
export const refresh = (refreshToken: string) =>
  api.post<{
    access_token: string
    refresh_token: string
    token_type: string
    expires_in: number
    refresh_expires_in: number
    user: {
      id: string
      email: string
      name: string
      role: string
      language: string
    }
  }>('/auth/refresh', { refresh_token: refreshToken })

// Session management
export const listSessions = () =>
  api.get<{
    sessions: Array<{
      id: string
      device_type: string
      device_name: string | null
      ip_address: string | null
      location: string | null
      created_at: string
      last_used_at: string
      is_current: boolean
    }>
    total: number
    max_sessions: number
  }>('/auth/sessions')

export const revokeSession = (sessionId: string) =>
  api.delete(`/auth/sessions/${sessionId}`)

export const revokeAllSessions = () =>
  api.delete('/auth/sessions')
