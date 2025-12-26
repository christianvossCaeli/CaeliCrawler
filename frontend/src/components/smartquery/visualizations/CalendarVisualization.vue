<template>
  <div class="calendar-visualization">
    <VueCal
      ref="vuecal"
      :active-view="activeView"
      :events="calendarEvents"
      :locale="locale"
      :disable-views="disabledViews"
      :time="showTime"
      :time-from="timeFrom"
      :time-to="timeTo"
      :hide-view-selector="hideViewSelector"
      :twelve-hour="false"
      :class="{ 'vuecal--dark': isDarkMode }"
      events-on-month-view
      @event-click="onEventClick"
      @view-change="onViewChange"
    >
      <!-- Custom event rendering -->
      <template #event="{ event }">
        <div class="vuecal__event-content" :style="{ backgroundColor: event.color || defaultEventColor }">
          <div class="vuecal__event-title">{{ event.title }}</div>
          <div v-if="event.subtitle" class="vuecal__event-subtitle">{{ event.subtitle }}</div>
        </div>
      </template>

      <!-- No events message -->
      <template #no-event>
        <div class="text-center text-medium-emphasis py-2">
          {{ t('smartQuery.visualization.calendar.noEvents') }}
        </div>
      </template>
    </VueCal>

    <!-- Event detail popup -->
    <v-dialog v-model="showEventDialog" max-width="400">
      <v-card v-if="selectedEvent">
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2" color="primary">mdi-calendar</v-icon>
          {{ selectedEvent.title }}
        </v-card-title>
        <v-card-text>
          <div v-if="selectedEvent.subtitle" class="text-body-2 mb-2">
            {{ selectedEvent.subtitle }}
          </div>
          <div class="text-caption text-medium-emphasis">
            <v-icon size="small" class="mr-1">mdi-clock-outline</v-icon>
            {{ formatEventDate(selectedEvent) }}
          </div>
          <div v-if="selectedEvent.entity_id" class="mt-3">
            <v-btn
              variant="tonal"
              color="primary"
              size="small"
              :to="`/entity/${selectedEvent.entity_id}`"
            >
              <v-icon start>mdi-open-in-new</v-icon>
              {{ t('smartQuery.visualization.calendar.viewDetails') }}
            </v-btn>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showEventDialog = false">
            {{ t('common.close') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTheme } from 'vuetify'
// @ts-expect-error - vue-cal types not properly exported
import { VueCal } from 'vue-cal'
import 'vue-cal/style.css'
import type { VisualizationConfig } from './types'
import { getNestedValue } from './types'

const props = defineProps<{
  data: Record<string, unknown>[]
  config?: VisualizationConfig & {
    active_view?: 'month' | 'week' | 'day' | 'year'
    date_field?: string
    end_date_field?: string
    title_field?: string
    subtitle_field?: string
    color_field?: string
    show_time?: boolean
    disabled_views?: string[]
  }
}>()
const { t, locale: i18nLocale } = useI18n()
const theme = useTheme()

// Refs
const showEventDialog = ref(false)
const selectedEvent = ref<{ title?: string; start?: Date; end?: Date; content?: string; originalItem?: unknown } | null>(null)

// Computed: Dark mode
const isDarkMode = computed(() => theme.global.current.value.dark)

// Computed: Default event color (from theme)
const defaultEventColor = computed(() =>
  isDarkMode.value ? '#4a7c7a' : '#113534'
)

// Computed: Locale (Vue Cal uses 2-letter codes)
const locale = computed(() => {
  const lang = i18nLocale.value
  // Map i18n locale to Vue Cal locale
  if (lang.startsWith('de')) return 'de'
  if (lang.startsWith('en')) return 'en'
  if (lang.startsWith('fr')) return 'fr'
  if (lang.startsWith('es')) return 'es'
  return 'en'
})

// Computed: Active view
const activeView = computed(() => props.config?.active_view || 'month')

// Computed: Show time
const showTime = computed(() => props.config?.show_time !== false)

// Computed: Time range
const timeFrom = computed(() => 6 * 60) // 6:00
const timeTo = computed(() => 22 * 60) // 22:00

// Computed: Disabled views
const disabledViews = computed(() =>
  props.config?.disabled_views || []
)

// Computed: Hide view selector if only one view
const hideViewSelector = computed(() => {
  const enabledViews = ['month', 'week', 'day', 'year'].filter(
    v => !disabledViews.value.includes(v)
  )
  return enabledViews.length <= 1
})

// Computed: Calendar events from data
const calendarEvents = computed(() => {
  if (!props.data || props.data.length === 0) return []

  const dateField = props.config?.date_field || 'date'
  const endDateField = props.config?.end_date_field
  const titleField = props.config?.title_field || 'entity_name'
  const subtitleField = props.config?.subtitle_field
  const colorField = props.config?.color_field

  return props.data
    .map((item, index) => {
      // Get start date
      const startDate = getNestedValue(item, dateField) ||
                      getNestedValue(item, `facets.${dateField}.value`) ||
                      item.date ||
                      item.start_date

      if (!startDate) return null

      // Parse date
      const start = parseDate(startDate)
      if (!start) return null

      // Get end date (optional)
      let end = start
      if (endDateField) {
        const endDateValue = getNestedValue(item, endDateField) ||
                             getNestedValue(item, `facets.${endDateField}.value`)
        if (endDateValue) {
          const parsedEnd = parseDate(endDateValue)
          if (parsedEnd) end = parsedEnd
        }
      }

      // Get title
      const title = getNestedValue(item, titleField) ||
                    item.entity_name ||
                    item.name ||
                    `Event ${index + 1}`

      // Get subtitle (optional)
      const subtitle = subtitleField
        ? getNestedValue(item, subtitleField) ||
          getNestedValue(item, `facets.${subtitleField}.value`)
        : undefined

      // Get color (optional)
      let color = defaultEventColor.value
      if (colorField) {
        const colorValue = getNestedValue(item, colorField) ||
                          getNestedValue(item, `facets.${colorField}.value`)
        if (colorValue) {
          // Map category to color or use directly if it's a hex color
          color = mapCategoryToColor(colorValue)
        }
      }

      return {
        start,
        end,
        title,
        subtitle,
        color,
        class: 'custom-event',
        // Store original data for click handler
        entity_id: item.entity_id,
        entity_type: item.entity_type,
        originalData: item,
      }
    })
    .filter(Boolean)
})

// Helper: Parse date string to Date
function parseDate(value: unknown): Date | null {
  if (!value) return null
  if (value instanceof Date) return value

  // Try parsing ISO string
  const date = new Date(value)
  if (!isNaN(date.getTime())) return date

  // Try German date format (DD.MM.YYYY)
  const germanMatch = String(value).match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})/)
  if (germanMatch) {
    const [, day, month, year] = germanMatch
    return new Date(parseInt(year), parseInt(month) - 1, parseInt(day))
  }

  return null
}

// Helper: Map category values to colors
function mapCategoryToColor(category: string): string {
  // Predefined color palette
  const colorMap: Record<string, string> = {
    // German
    'wichtig': '#e53935',
    'dringend': '#d32f2f',
    'normal': '#1976d2',
    'niedrig': '#757575',
    // English
    'important': '#e53935',
    'urgent': '#d32f2f',
    'low': '#757575',
    // Status colors
    'aktiv': '#4caf50',
    'active': '#4caf50',
    'geplant': '#ff9800',
    'planned': '#ff9800',
    'abgesagt': '#9e9e9e',
    'cancelled': '#9e9e9e',
  }

  const lowerCategory = String(category).toLowerCase()
  if (colorMap[lowerCategory]) {
    return colorMap[lowerCategory]
  }

  // If it's already a hex color, use it
  if (/^#[0-9a-fA-F]{6}$/.test(category)) {
    return category
  }

  // Generate color from string hash
  return stringToColor(category)
}

// Helper: Generate consistent color from string
function stringToColor(str: string): string {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash)
  }
  const hue = hash % 360
  return `hsl(${hue}, 60%, 45%)`
}

// Event handlers
function onEventClick(event: { title?: string; start?: Date; end?: Date; content?: string; originalData?: unknown }, e: Event) {
  e.stopPropagation()
  selectedEvent.value = event
  showEventDialog.value = true
}

function onViewChange(_view: string) {
  // Could emit to parent if needed
}

// Helper: Format event date for display
function formatEventDate(event: { start?: Date | string; end?: Date | string | null } | null): string {
  if (!event?.start) return ''

  const start = new Date(event.start)
  const end = event.end ? new Date(event.end) : null

  const dateOptions: Intl.DateTimeFormatOptions = {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }

  const timeOptions: Intl.DateTimeFormatOptions = {
    hour: '2-digit',
    minute: '2-digit',
  }

  const locale = i18nLocale.value.startsWith('de') ? 'de-DE' : 'en-US'

  let result = start.toLocaleDateString(locale, dateOptions)

  // Add time if not all-day event
  if (showTime.value) {
    result += `, ${start.toLocaleTimeString(locale, timeOptions)}`

    if (end && end.getTime() !== start.getTime()) {
      result += ` - ${end.toLocaleTimeString(locale, timeOptions)}`
    }
  }

  return result
}
</script>

<style scoped>
.calendar-visualization {
  min-height: 400px;
  height: 100%;
}

.calendar-visualization :deep(.vuecal) {
  height: 100%;
  min-height: 400px;
  border-radius: 8px;
  overflow: hidden;
}

/* Light mode styles */
.calendar-visualization :deep(.vuecal__header) {
  background-color: rgb(var(--v-theme-surface));
}

.calendar-visualization :deep(.vuecal__cell) {
  border-color: rgba(var(--v-border-color), var(--v-border-opacity));
}

.calendar-visualization :deep(.vuecal__cell--today) {
  background-color: rgba(var(--v-theme-primary), 0.1);
}

.calendar-visualization :deep(.vuecal__cell--selected) {
  background-color: rgba(var(--v-theme-primary), 0.15);
}

/* Dark mode styles */
.calendar-visualization :deep(.vuecal--dark) {
  background-color: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface));
}

.calendar-visualization :deep(.vuecal--dark .vuecal__header) {
  background-color: rgb(var(--v-theme-surface-variant));
}

.calendar-visualization :deep(.vuecal--dark .vuecal__cell) {
  border-color: rgba(255, 255, 255, 0.12);
}

.calendar-visualization :deep(.vuecal--dark .vuecal__cell--today) {
  background-color: rgba(var(--v-theme-primary), 0.2);
}

/* Event styles */
.calendar-visualization :deep(.vuecal__event) {
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
  transition: transform 0.1s ease;
}

.calendar-visualization :deep(.vuecal__event:hover) {
  transform: scale(1.02);
  z-index: 10;
}

.calendar-visualization :deep(.vuecal__event-content) {
  padding: 2px 4px;
  border-radius: 4px;
  color: white;
  height: 100%;
}

.calendar-visualization :deep(.vuecal__event-title) {
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.calendar-visualization :deep(.vuecal__event-subtitle) {
  font-size: 0.65rem;
  opacity: 0.85;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* View selector styles */
.calendar-visualization :deep(.vuecal__view-btn) {
  color: rgb(var(--v-theme-on-surface));
}

.calendar-visualization :deep(.vuecal__view-btn--active) {
  background-color: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
}

/* Navigation arrows */
.calendar-visualization :deep(.vuecal__arrow) {
  color: rgb(var(--v-theme-on-surface));
}

/* Time column in week/day views */
.calendar-visualization :deep(.vuecal__time-column) {
  font-size: 0.7rem;
  color: rgb(var(--v-theme-on-surface-variant));
}
</style>
