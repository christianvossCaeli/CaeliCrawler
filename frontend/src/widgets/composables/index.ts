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

export {
  useFormatTime,
  type FormatTimeOptions,
} from './useFormatTime'
