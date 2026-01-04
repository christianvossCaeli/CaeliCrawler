/**
 * Widget Composables
 * Re-exports all composable functions for widget development
 */

export {
  useClickableAttrs,
  handleKeyboardClick,
  createKeydownHandler,
  useWidgetInteraction,
  type ClickableOptions,
} from './useClickableWidget'

export {
  useStatsWidget,
  useWidgetNavigation,
  type UseStatsWidgetOptions,
} from './useStatsWidget'

// useFormatTime is deprecated - use useDateFormatter from '@/composables/useDateFormatter' directly
export { useDateFormatter } from '@/composables/useDateFormatter'
