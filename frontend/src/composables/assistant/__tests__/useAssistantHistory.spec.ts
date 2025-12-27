/**
 * Tests for useAssistantHistory composable
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { useAssistantHistory } from '../useAssistantHistory'
import type { ConversationMessage } from '../types'
import { STORAGE_KEY } from '../types'

describe('useAssistantHistory', () => {
  const localStorageMock = {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
    Object.defineProperty(window, 'localStorage', {
      value: localStorageMock,
      writable: true
    })
  })

  describe('loadHistory', () => {
    it('should load conversation history from localStorage', () => {
      const messages = ref<ConversationMessage[]>([])
      const storedMessages = [
        {
          role: 'user' as const,
          content: 'Hello',
          timestamp: '2024-01-01T10:00:00.000Z',
        },
        {
          role: 'assistant' as const,
          content: 'Hi there!',
          timestamp: '2024-01-01T10:00:01.000Z',
        },
      ]
      localStorageMock.getItem.mockReturnValue(JSON.stringify(storedMessages))

      const { loadHistory } = useAssistantHistory({ messages })
      loadHistory()

      expect(localStorageMock.getItem).toHaveBeenCalledWith(STORAGE_KEY)
      expect(messages.value).toHaveLength(2)
      expect(messages.value[0].content).toBe('Hello')
      expect(messages.value[0].timestamp).toBeInstanceOf(Date)
    })

    it('should handle empty localStorage', () => {
      const messages = ref<ConversationMessage[]>([])
      localStorageMock.getItem.mockReturnValue(null)

      const { loadHistory } = useAssistantHistory({ messages })
      loadHistory()

      expect(messages.value).toHaveLength(0)
    })

    it('should handle invalid JSON gracefully', () => {
      const messages = ref<ConversationMessage[]>([])
      localStorageMock.getItem.mockReturnValue('invalid-json')

      const { loadHistory } = useAssistantHistory({ messages })
      loadHistory()

      expect(messages.value).toHaveLength(0)
    })
  })

  describe('saveHistory', () => {
    it('should save messages to localStorage', () => {
      const messages = ref<ConversationMessage[]>([
        {
          role: 'user',
          content: 'Test message',
          timestamp: new Date('2024-01-01T10:00:00.000Z'),
        },
      ])

      const { saveHistory } = useAssistantHistory({ messages })
      saveHistory()

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        STORAGE_KEY,
        expect.any(String)
      )
    })

    it('should limit saved messages to MAX_HISTORY_LENGTH', () => {
      const messages = ref<ConversationMessage[]>([])
      // Create 60 messages (more than MAX_HISTORY_LENGTH of 50)
      for (let i = 0; i < 60; i++) {
        messages.value.push({
          role: 'user',
          content: `Message ${i}`,
          timestamp: new Date(),
        })
      }

      const { saveHistory } = useAssistantHistory({ messages })
      saveHistory()

      const savedData = JSON.parse(localStorageMock.setItem.mock.calls[0][1])
      expect(savedData).toHaveLength(50)
    })
  })

  describe('clearConversation', () => {
    it('should clear all messages', () => {
      const messages = ref<ConversationMessage[]>([
        { role: 'user', content: 'Test', timestamp: new Date() },
      ])

      const { clearConversation } = useAssistantHistory({ messages })
      clearConversation()

      expect(messages.value).toHaveLength(0)
      expect(localStorageMock.removeItem).toHaveBeenCalledWith(STORAGE_KEY)
    })
  })

  describe('query history', () => {
    it('should add query to history', () => {
      const messages = ref<ConversationMessage[]>([])
      localStorageMock.getItem.mockReturnValue(null)

      const { queryHistory, addQueryToHistory, loadQueryHistory } = useAssistantHistory({ messages })
      loadQueryHistory()
      addQueryToHistory('test query', 5, 'read')

      expect(queryHistory.value).toHaveLength(1)
      expect(queryHistory.value[0].query).toBe('test query')
      expect(queryHistory.value[0].resultCount).toBe(5)
      expect(queryHistory.value[0].queryType).toBe('read')
      expect(queryHistory.value[0].isFavorite).toBe(false)
    })

    it('should not add duplicate consecutive queries', () => {
      const messages = ref<ConversationMessage[]>([])
      localStorageMock.getItem.mockReturnValue(null)

      const { queryHistory, addQueryToHistory, loadQueryHistory } = useAssistantHistory({ messages })
      loadQueryHistory()
      addQueryToHistory('same query', 5, 'read')
      addQueryToHistory('same query', 10, 'read')

      expect(queryHistory.value).toHaveLength(1)
      expect(queryHistory.value[0].resultCount).toBe(10) // Updated count
    })

    it('should toggle favorite status', () => {
      const messages = ref<ConversationMessage[]>([])
      localStorageMock.getItem.mockReturnValue(null)

      const { queryHistory, addQueryToHistory, toggleQueryFavorite, loadQueryHistory } = useAssistantHistory({ messages })
      loadQueryHistory()
      addQueryToHistory('test query', 5, 'read')

      const itemId = queryHistory.value[0].id
      expect(queryHistory.value[0].isFavorite).toBe(false)

      toggleQueryFavorite(itemId)
      expect(queryHistory.value[0].isFavorite).toBe(true)

      toggleQueryFavorite(itemId)
      expect(queryHistory.value[0].isFavorite).toBe(false)
    })

    it('should remove query from history', () => {
      const messages = ref<ConversationMessage[]>([])
      localStorageMock.getItem.mockReturnValue(null)

      const { queryHistory, addQueryToHistory, removeQueryFromHistory, loadQueryHistory } = useAssistantHistory({ messages })
      loadQueryHistory()
      addQueryToHistory('query 1', 5, 'read')
      addQueryToHistory('query 2', 10, 'write')

      expect(queryHistory.value).toHaveLength(2)

      const itemId = queryHistory.value[0].id
      removeQueryFromHistory(itemId)

      expect(queryHistory.value).toHaveLength(1)
      expect(queryHistory.value[0].query).toBe('query 2')
    })

    it('should clear query history while keeping favorites', () => {
      const messages = ref<ConversationMessage[]>([])
      localStorageMock.getItem.mockReturnValue(null)

      const { queryHistory, addQueryToHistory, toggleQueryFavorite, clearQueryHistory, loadQueryHistory } = useAssistantHistory({ messages })
      loadQueryHistory()
      addQueryToHistory('query 1', 5, 'read')
      addQueryToHistory('query 2', 10, 'write')

      // Make first query a favorite
      toggleQueryFavorite(queryHistory.value[0].id)

      clearQueryHistory(true) // Keep favorites

      expect(queryHistory.value).toHaveLength(1)
      expect(queryHistory.value[0].query).toBe('query 1')
    })

    it('should get filtered query history', () => {
      const messages = ref<ConversationMessage[]>([])
      localStorageMock.getItem.mockReturnValue(null)

      const { queryHistory, addQueryToHistory, toggleQueryFavorite, getQueryHistory, loadQueryHistory } = useAssistantHistory({ messages })
      loadQueryHistory()
      addQueryToHistory('read query', 5, 'read')
      addQueryToHistory('write query', 10, 'write')
      toggleQueryFavorite(queryHistory.value[0].id)

      // Filter by favorites
      const favorites = getQueryHistory({ favoritesOnly: true })
      expect(favorites).toHaveLength(1)
      expect(favorites[0].query).toBe('read query')

      // Filter by query type
      const writeQueries = getQueryHistory({ queryType: 'write' })
      expect(writeQueries).toHaveLength(1)
      expect(writeQueries[0].query).toBe('write query')

      // Limit results
      const limited = getQueryHistory({ limit: 1 })
      expect(limited).toHaveLength(1)
    })
  })
})
