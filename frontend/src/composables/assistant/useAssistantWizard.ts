/**
 * Assistant Wizard Composable
 *
 * Manages multi-step wizard interactions for entity creation and configuration.
 */

import { ref, type Ref } from 'vue'
import { useRouter } from 'vue-router'
import { assistantApi } from '@/services/api'
import { extractErrorMessage } from '@/utils/errorMessage'
import { useLogger } from '@/composables/useLogger'
import type {
  ActiveWizard,
  WizardInfo,
  WizardResponseData,
  ConversationMessage,
  AssistantContext,
} from './types'

const logger = useLogger('useAssistantWizard')

export interface UseAssistantWizardOptions {
  messages: Ref<ConversationMessage[]>
  error: Ref<string | null>
  currentContext: Ref<AssistantContext>
  saveHistory: () => void
}

export function useAssistantWizard(options: UseAssistantWizardOptions) {
  const { messages, error, currentContext, saveHistory } = options
  const router = useRouter()

  // Wizard state
  const activeWizard = ref<ActiveWizard | null>(null)
  const availableWizards = ref<WizardInfo[]>([])
  const isWizardLoading = ref(false)

  // Load available wizards
  async function loadWizards() {
    try {
      const response = await assistantApi.getWizards()
      availableWizards.value = response.data.wizards || []
    } catch (e) {
      logger.error('Failed to load wizards:', e)
      availableWizards.value = []
    }
  }

  // Start a new wizard
  async function startWizard(wizardType: string): Promise<boolean> {
    isWizardLoading.value = true
    error.value = null

    try {
      const response = await assistantApi.startWizard(wizardType, {
        current_entity_id: currentContext.value.current_entity_id,
        current_entity_type: currentContext.value.current_entity_type,
      })

      const data = response.data

      // Find wizard info for name/icon
      const wizardInfo = availableWizards.value.find(w => w.type === wizardType)

      activeWizard.value = {
        state: data.wizard_state,
        currentStep: data.current_step,
        canGoBack: data.can_go_back,
        progress: data.progress,
        message: data.message,
        name: wizardInfo?.name || wizardType,
        icon: wizardInfo?.icon || 'mdi-wizard-hat',
      }

      // Add wizard start message to chat
      const wizardMessage: ConversationMessage = {
        role: 'assistant',
        content: data.message,
        timestamp: new Date(),
        response_type: 'wizard',
        metadata: { wizard_id: data.wizard_state.wizard_id },
      }
      messages.value.push(wizardMessage)
      saveHistory()

      return true
    } catch (e: unknown) {
      error.value = extractErrorMessage(e)
      return false
    } finally {
      isWizardLoading.value = false
    }
  }

  // Submit wizard response
  async function submitWizardResponse(value: unknown): Promise<boolean> {
    if (!activeWizard.value) return false

    isWizardLoading.value = true
    error.value = null

    try {
      const response = await assistantApi.wizardRespond(
        activeWizard.value.state.wizard_id,
        value
      )

      const data = response.data as WizardResponseData
      const wizardResponse = data.wizard_response
      const result = data.result

      // Update wizard state
      if (wizardResponse.wizard_state.completed || wizardResponse.wizard_state.cancelled) {
        // Wizard finished
        const completionMessage: ConversationMessage = {
          role: 'assistant',
          content: wizardResponse.message,
          timestamp: new Date(),
          response_type: result?.success ? 'success' : (wizardResponse.wizard_state.cancelled ? 'info' : 'error'),
        }
        messages.value.push(completionMessage)
        saveHistory()

        // Handle result actions (e.g., navigation)
        if (result?.navigate_to) {
          router.push(result.navigate_to)
        }

        activeWizard.value = null
      } else {
        // Update to next step
        activeWizard.value = {
          ...activeWizard.value,
          state: wizardResponse.wizard_state,
          currentStep: wizardResponse.current_step,
          canGoBack: wizardResponse.can_go_back,
          progress: wizardResponse.progress,
          message: wizardResponse.message,
        }

        // Add step message to chat
        const stepMessage: ConversationMessage = {
          role: 'assistant',
          content: wizardResponse.message,
          timestamp: new Date(),
          response_type: 'wizard',
        }
        messages.value.push(stepMessage)
        saveHistory()
      }

      return true
    } catch (e: unknown) {
      error.value = extractErrorMessage(e)
      return false
    } finally {
      isWizardLoading.value = false
    }
  }

  // Go back to previous wizard step
  async function wizardGoBack(): Promise<boolean> {
    if (!activeWizard.value || !activeWizard.value.canGoBack) return false

    isWizardLoading.value = true
    error.value = null

    try {
      const response = await assistantApi.wizardBack(activeWizard.value.state.wizard_id)
      const data = response.data

      activeWizard.value = {
        ...activeWizard.value,
        state: data.wizard_state,
        currentStep: data.current_step,
        canGoBack: data.can_go_back,
        progress: data.progress,
        message: data.message,
      }

      return true
    } catch (e: unknown) {
      error.value = extractErrorMessage(e)
      return false
    } finally {
      isWizardLoading.value = false
    }
  }

  // Cancel active wizard
  async function cancelWizard(): Promise<void> {
    if (!activeWizard.value) return

    try {
      await assistantApi.wizardCancel(activeWizard.value.state.wizard_id)
    } catch (e) {
      logger.error('Failed to cancel wizard:', e)
    }

    // Add cancellation message
    const cancelMessage: ConversationMessage = {
      role: 'assistant',
      content: 'Wizard abgebrochen.',
      timestamp: new Date(),
      response_type: 'info',
    }
    messages.value.push(cancelMessage)
    saveHistory()

    activeWizard.value = null
  }

  return {
    // State
    activeWizard,
    availableWizards,
    isWizardLoading,

    // Methods
    loadWizards,
    startWizard,
    submitWizardResponse,
    wizardGoBack,
    cancelWizard,
  }
}
