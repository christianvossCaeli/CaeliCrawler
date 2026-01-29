/**
 * Assistant History Composable
 *
 * Manages conversation history and query history persistence.
 */

import { ref, type Ref } from 'vue'
import { useLogger } from '@/composables/useLogger'
import type {
  ConversationMessage,
  QueryHistoryItem,
  ResponseData,
} from './types'
import {
  STORAGE_KEY,
  QUERY_HISTORY_KEY,
  MAX_HISTORY_LENGTH,
  MAX_QUERY_HISTORY_LENGTH,
  generateMessageId,
} from './types'
import { validateStoredMessages, validateStoredQueryHistory } from './validation'

const logger = useLogger('useAssistantHistory')

export interface UseAssistantHistoryOptions {
  messages: Ref<ConversationMessage[]>
}

export function useAssistantHistory(options: UseAssistantHistoryOptions) {
  const { messages } = options

  // Query history state
  const queryHistory = ref<QueryHistoryItem[]>([])

  // Load conversation history from local storage with validation
  function loadHistory() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const parsed = JSON.parse(stored)
        const result = validateStoredMessages(parsed)

        if (result.success && result.data) {
          messages.value = result.data.map((msg) => ({
            // Generate new ID for restored messages, or use existing if available
            id: (msg as { id?: string }).id || generateMessageId(),
            role: msg.role,
            content: msg.content,
            timestamp: new Date(msg.timestamp),
            metadata: msg.metadata,
            response_type: msg.response_type,
            response_data: msg.response_data as ResponseData | undefined
          }))
        } else {
          // Invalid format - clear corrupted data
          logger.warn('Invalid conversation history format, clearing:', result.error?.issues)
          localStorage.removeItem(STORAGE_KEY)
        }
      }
    } catch (e) {
      logger.error('Failed to load assistant history:', e)
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  // Save conversation history to local storage
  function saveHistory() {
    try {
      const toSave = messages.value.slice(-MAX_HISTORY_LENGTH)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave))
    } catch (e) {
      logger.error('Failed to save assistant history:', e)
    }
  }

  // Load query history from local storage with validation
  function loadQueryHistory() {
    try {
      const stored = localStorage.getItem(QUERY_HISTORY_KEY)
      if (stored) {
        const parsed = JSON.parse(stored)
        const result = validateStoredQueryHistory(parsed)

        if (result.success && result.data) {
          queryHistory.value = result.data.map((item) => ({
            ...item,
            timestamp: new Date(item.timestamp)
          }))
        } else {
          // Invalid format - clear corrupted data
          logger.warn('Invalid query history format, clearing:', result.error?.issues)
          localStorage.removeItem(QUERY_HISTORY_KEY)
        }
      }
    } catch (e) {
      logger.error('Failed to load query history:', e)
      localStorage.removeItem(QUERY_HISTORY_KEY)
    }
  }

  // Save query history to local storage
  function saveQueryHistory() {
    try {
      const toSave = queryHistory.value.slice(-MAX_QUERY_HISTORY_LENGTH)
      localStorage.setItem(QUERY_HISTORY_KEY, JSON.stringify(toSave))
    } catch (e) {
      logger.error('Failed to save query history:', e)
    }
  }

  // Add a query to history
  function addQueryToHistory(
    query: string,
    resultCount: number,
    queryType: 'read' | 'write' | 'plan',
    metadata?: { entityType?: string; facetTypes?: string[] }
  ) {
    // Don't add duplicate consecutive queries
    const lastQuery = queryHistory.value[queryHistory.value.length - 1]
    if (lastQuery && lastQuery.query === query) {
      // Update the timestamp and result count instead
      lastQuery.timestamp = new Date()
      lastQuery.resultCount = resultCount
      saveQueryHistory()
      return
    }

    const historyItem: QueryHistoryItem = {
      id: `qh_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      query,
      timestamp: new Date(),
      resultCount,
      queryType,
      isFavorite: false,
      entityType: metadata?.entityType,
      facetTypes: metadata?.facetTypes
    }

    queryHistory.value.push(historyItem)

    // Trim to max length (but keep favorites)
    if (queryHistory.value.length > MAX_QUERY_HISTORY_LENGTH) {
      const favorites = queryHistory.value.filter(item => item.isFavorite)
      const nonFavorites = queryHistory.value.filter(item => !item.isFavorite)
      const trimmedNonFavorites = nonFavorites.slice(-MAX_QUERY_HISTORY_LENGTH + favorites.length)
      queryHistory.value = [...favorites, ...trimmedNonFavorites].sort(
        (a, b) => a.timestamp.getTime() - b.timestamp.getTime()
      )
    }

    saveQueryHistory()
  }

  // Toggle favorite status of a query history item
  function toggleQueryFavorite(itemId: string) {
    const item = queryHistory.value.find(q => q.id === itemId)
    if (item) {
      item.isFavorite = !item.isFavorite
      saveQueryHistory()
    }
  }

  // Remove a query from history
  function removeQueryFromHistory(itemId: string) {
    queryHistory.value = queryHistory.value.filter(q => q.id !== itemId)
    saveQueryHistory()
  }

  // Clear all query history (optionally keep favorites)
  function clearQueryHistory(keepFavorites: boolean = true) {
    if (keepFavorites) {
      queryHistory.value = queryHistory.value.filter(item => item.isFavorite)
    } else {
      queryHistory.value = []
    }
    saveQueryHistory()
  }

  // Get query history, optionally filtered
  function getQueryHistory(options?: {
    favoritesOnly?: boolean
    queryType?: 'read' | 'write' | 'plan'
    limit?: number
  }): QueryHistoryItem[] {
    let result = [...queryHistory.value]

    if (options?.favoritesOnly) {
      result = result.filter(item => item.isFavorite)
    }

    if (options?.queryType) {
      result = result.filter(item => item.queryType === options.queryType)
    }

    // Sort by timestamp descending (newest first)
    result.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())

    if (options?.limit) {
      result = result.slice(0, options.limit)
    }

    return result
  }

  // Clear conversation
  function clearConversation() {
    messages.value = []
    localStorage.removeItem(STORAGE_KEY)
  }

  return {
    // State
    queryHistory,

    // Conversation history methods
    loadHistory,
    saveHistory,
    clearConversation,

    // Query history methods
    loadQueryHistory,
    saveQueryHistory,
    addQueryToHistory,
    toggleQueryFavorite,
    removeQueryFromHistory,
    clearQueryHistory,
    getQueryHistory,
  }
}
