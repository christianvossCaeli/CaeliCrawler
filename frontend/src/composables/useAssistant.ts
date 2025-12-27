/**
 * Assistant Composable - Re-export for Backward Compatibility
 *
 * This file maintains backward compatibility by re-exporting from the
 * new modular assistant composables structure.
 *
 * The assistant functionality has been refactored into smaller,
 * focused composables located in ./assistant/:
 *
 * - useAssistantHistory: Conversation and query history management
 * - useAssistantAttachments: File upload handling
 * - useAssistantBatch: Batch operations for bulk updates
 * - useAssistantWizard: Multi-step wizard interactions
 * - useAssistantReminders: Reminder management
 * - useAssistantInsights: Proactive insights and suggestions
 *
 * @see ./assistant/index.ts for the main composable
 * @see ./assistant/types.ts for all type definitions
 */

// Re-export everything from the new modular structure
export * from './assistant'

// Default export for convenience
export { useAssistant as default } from './assistant'
