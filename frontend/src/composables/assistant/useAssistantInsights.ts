/**
 * Assistant Insights Composable
 *
 * Manages proactive insights and context-aware suggestions.
 */

import { ref, type Ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { assistantApi } from '@/services/api'
import { useLogger } from '@/composables/useLogger'
import type {
  Insight,
  SlashCommand,
  SuggestedAction,
  AssistantContext,
  ApiSuggestion,
  ConversationMessage,
} from './types'

const logger = useLogger('useAssistantInsights')

export interface UseAssistantInsightsOptions {
  currentContext: Ref<AssistantContext>
  messages: Ref<ConversationMessage[]>
  suggestedActions: Ref<SuggestedAction[]>
  send: (text: string) => Promise<void>
  closeChat: () => void
}

export function useAssistantInsights(options: UseAssistantInsightsOptions) {
  const { currentContext, messages, suggestedActions, send, closeChat } = options
  const router = useRouter()
  const { locale } = useI18n()

  // Insights state
  const insights = ref<Insight[]>([])
  const slashCommands = ref<SlashCommand[]>([])

  // Load slash commands
  async function loadSlashCommands() {
    try {
      const response = await assistantApi.getCommands()
      slashCommands.value = response.data
    } catch (e) {
      logger.error('Failed to load slash commands:', e)
    }
  }

  // Load context-specific suggestions from API
  async function loadSuggestions() {
    try {
      const response = await assistantApi.getSuggestions({
        route: currentContext.value.current_route,
        entity_type: currentContext.value.current_entity_type || undefined,
        entity_id: currentContext.value.current_entity_id || undefined
      })

      // Only update if we don't have user-triggered suggestions
      if (messages.value.length === 0 || !suggestedActions.value.length) {
        const suggestions = response.data.suggestions as ApiSuggestion[] | undefined
        suggestedActions.value = suggestions?.map((s) => ({
          label: s.label,
          action: 'query',
          value: s.query
        })) || []
      }
    } catch (e) {
      logger.error('Failed to load suggestions:', e)
    }
  }

  // Load proactive insights from API
  async function loadInsights() {
    try {
      const lang = (locale.value === 'de' || locale.value === 'en') ? locale.value : 'de'
      const response = await assistantApi.getInsights({
        route: currentContext.value.current_route,
        view_mode: currentContext.value.view_mode,
        entity_type: currentContext.value.current_entity_type || undefined,
        entity_id: currentContext.value.current_entity_id || undefined,
        language: lang
      })
      insights.value = response.data.insights || []
    } catch (e) {
      logger.error('Failed to load insights:', e)
      insights.value = []
    }
  }

  // Handle insight action click
  async function handleInsightAction(action: { type: string; value: string }) {
    if (action.type === 'navigate') {
      router.push(action.value)
      closeChat()
    } else if (action.type === 'query') {
      await send(action.value)
    }
  }

  return {
    // State
    insights,
    slashCommands,

    // Methods
    loadSlashCommands,
    loadSuggestions,
    loadInsights,
    handleInsightAction,
  }
}
