/**
 * Assistant Composables - Barrel Export
 *
 * This module re-exports all assistant composables and types.
 * The main useAssistant composable is in _core.ts.
 */

// Export types
export * from './types'

// Export sub-composables for individual use
export { useAssistantHistory } from './useAssistantHistory'
export { useAssistantAttachments } from './useAssistantAttachments'
export { useAssistantBatch } from './useAssistantBatch'
export { useAssistantWizard } from './useAssistantWizard'
export { useAssistantReminders } from './useAssistantReminders'
export { useAssistantInsights } from './useAssistantInsights'

// Export main composable from core module
export { useAssistant } from './_core'
