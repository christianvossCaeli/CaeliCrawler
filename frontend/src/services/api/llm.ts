/**
 * User LLM Usage API Service
 *
 * Provides API methods for user budget status and limit requests.
 */

import { api } from './client'
import type {
  LimitIncreaseRequest,
  LimitIncreaseRequestCreate,
  LimitRequestListResponse,
  LimitRequestStatus,
  UserBudgetStatus,
} from '@/types/llm-usage'

// === User Endpoints ===

/**
 * Get current user's LLM budget status.
 * Returns null if no budget is configured for the user.
 */
export async function getMyLLMUsage(): Promise<UserBudgetStatus | null> {
  const { data } = await api.get<UserBudgetStatus | null>('/v1/me/llm/usage')
  return data
}

/**
 * Request an increase to the user's LLM budget limit.
 */
export async function requestLimitIncrease(
  request: LimitIncreaseRequestCreate
): Promise<LimitIncreaseRequest> {
  const { data } = await api.post<LimitIncreaseRequest>('/v1/me/llm/limit-request', request)
  return data
}

/**
 * Get all limit requests submitted by the current user.
 */
export async function getMyLimitRequests(): Promise<LimitIncreaseRequest[]> {
  const { data } = await api.get<LimitIncreaseRequest[]>('/v1/me/llm/limit-requests')
  return data
}

// === Admin Endpoints ===

/**
 * List all limit increase requests (admin only).
 */
export async function getLimitRequests(params?: {
  status?: LimitRequestStatus
  limit?: number
}): Promise<LimitRequestListResponse> {
  const { data } = await api.get<LimitRequestListResponse>('/admin/llm-budget/limit-requests', {
    params,
  })
  return data
}

/**
 * Get a specific limit request (admin only).
 */
export async function getLimitRequest(requestId: string): Promise<LimitIncreaseRequest> {
  const { data } = await api.get<LimitIncreaseRequest>(
    `/admin/llm-budget/limit-requests/${requestId}`
  )
  return data
}

/**
 * Approve a limit increase request (admin only).
 */
export async function approveLimitRequest(
  requestId: string,
  notes?: string
): Promise<LimitIncreaseRequest> {
  const { data } = await api.post<LimitIncreaseRequest>(
    `/admin/llm-budget/limit-requests/${requestId}/approve`,
    notes ? { notes } : undefined
  )
  return data
}

/**
 * Deny a limit increase request (admin only).
 */
export async function denyLimitRequest(
  requestId: string,
  notes?: string
): Promise<LimitIncreaseRequest> {
  const { data } = await api.post<LimitIncreaseRequest>(
    `/admin/llm-budget/limit-requests/${requestId}/deny`,
    notes ? { notes } : undefined
  )
  return data
}
