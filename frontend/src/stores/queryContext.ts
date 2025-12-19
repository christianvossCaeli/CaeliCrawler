/**
 * Query Context Store
 *
 * Provides shared state between the Chat Assistant and Smart Query views
 * for bi-directional data passing and context sharing.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface QueryContextData {
  /** The query string to execute */
  query: string
  /** Mode: 'read' for queries, 'write' for mutations */
  mode: 'read' | 'write'
  /** Source of the query context */
  source: 'assistant' | 'smart_query' | 'direct'
  /** Conversation ID from assistant */
  conversationId?: string
  /** Entity context from assistant */
  entityContext?: {
    entityId?: string | null
    entityType?: string | null
    entityName?: string | null
  }
  /** Timestamp when context was set */
  timestamp: Date
}

export interface QueryResultData {
  /** Summary of the result */
  summary: string
  /** Total number of results */
  total: number
  /** Result items (first few for preview) */
  items: any[]
  /** Query interpretation */
  interpretation?: any
  /** Whether the operation was successful */
  success: boolean
  /** Mode of the query */
  mode: 'read' | 'write'
}

export const useQueryContextStore = defineStore('queryContext', () => {
  // State
  const pendingContext = ref<QueryContextData | null>(null)
  const lastResults = ref<QueryResultData | null>(null)
  const returnToAssistant = ref(false)

  // Computed
  const hasContext = computed(() => pendingContext.value !== null)
  const hasResults = computed(() => lastResults.value !== null)

  // Actions

  /**
   * Set context from the assistant to be used by Smart Query
   */
  function setFromAssistant(
    query: string,
    mode: 'read' | 'write',
    entityContext?: {
      entityId?: string | null
      entityType?: string | null
      entityName?: string | null
    },
    conversationId?: string
  ) {
    pendingContext.value = {
      query,
      mode,
      source: 'assistant',
      conversationId,
      entityContext,
      timestamp: new Date(),
    }
    returnToAssistant.value = true
  }

  /**
   * Get and consume the pending context (used by Smart Query)
   */
  function consumeContext(): QueryContextData | null {
    const context = pendingContext.value
    pendingContext.value = null
    return context
  }

  /**
   * Set results from Smart Query to be returned to assistant
   */
  function setResults(results: QueryResultData) {
    lastResults.value = results
  }

  /**
   * Get and consume the last results (used by assistant)
   */
  function consumeResults(): QueryResultData | null {
    const results = lastResults.value
    lastResults.value = null
    returnToAssistant.value = false
    return results
  }

  /**
   * Clear all context and results
   */
  function clearAll() {
    pendingContext.value = null
    lastResults.value = null
    returnToAssistant.value = false
  }

  /**
   * Check if we should return to assistant after Smart Query
   */
  function shouldReturnToAssistant(): boolean {
    return returnToAssistant.value
  }

  /**
   * Mark that we've handled the return to assistant
   */
  function clearReturnFlag() {
    returnToAssistant.value = false
  }

  return {
    // State
    pendingContext,
    lastResults,
    returnToAssistant,

    // Computed
    hasContext,
    hasResults,

    // Actions
    setFromAssistant,
    consumeContext,
    setResults,
    consumeResults,
    clearAll,
    shouldReturnToAssistant,
    clearReturnFlag,
  }
})
