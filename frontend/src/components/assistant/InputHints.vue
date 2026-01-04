<template>
  <transition name="hints-fade">
    <div v-if="visibleHints.length > 0" class="input-hints">
      <div class="input-hints__header">
        <v-icon size="small" class="mr-1">mdi-lightbulb-on-outline</v-icon>
        <span>{{ t('assistant.hintsTitle') }}</span>
      </div>
      <div class="input-hints__list">
        <div
          v-for="hint in visibleHints"
          :key="hint.id"
          class="input-hints__item"
          @click="$emit('hint-click', hint.example)"
        >
          <v-chip
            size="x-small"
            :color="hint.color"
            variant="tonal"
            class="mr-2"
          >
            {{ hint.category }}
          </v-chip>
          <span class="input-hints__text">
            <!-- eslint-disable-next-line vue/no-v-html -- highlightTrigger returns safe <strong> tags only -->
            <span v-html="highlightTrigger(hint.text, hint.trigger)"></span>
          </span>
          <code v-if="hint.example" class="input-hints__example">
            {{ hint.example }}
          </code>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { escapeHtml } from '@/utils/messageFormatting'

const props = defineProps<{
  inputText: string
  isWriteMode: boolean
}>()

defineEmits<{
  'hint-click': [example: string]
}>()

const { t, locale } = useI18n()

interface InputHint {
  id: string
  trigger: string | RegExp
  text: string
  example: string
  category: string
  color: string
  priority: number
}

// Define all available hints
const allHints = computed<InputHint[]>(() => {
  const isDE = locale.value === 'de'

  return [
    // Count queries
    {
      id: 'count',
      trigger: isDE ? /^(wie\s*viel|wieviel|anzahl)/i : /^(how\s*many|count)/i,
      text: isDE ? 'Zählabfragen mit "Wie viele..."' : 'Count queries with "How many..."',
      example: isDE ? 'Wie viele Bürgermeister gibt es in NRW?' : 'How many mayors are there in NRW?',
      category: isDE ? 'Zählen' : 'Count',
      color: 'primary',
      priority: 10
    },
    // List queries
    {
      id: 'list',
      trigger: isDE ? /^(zeig|liste|finde|such)/i : /^(show|list|find|search)/i,
      text: isDE ? 'Auflistungen mit "Zeige alle..."' : 'List queries with "Show all..."',
      example: isDE ? 'Zeige alle Gemeinden mit Pain Points' : 'Show all municipalities with pain points',
      category: isDE ? 'Liste' : 'List',
      color: 'info',
      priority: 10
    },
    // Geographic filter
    {
      id: 'geo',
      trigger: isDE ? /\b(in|aus|von)\s*$/i : /\b(in|from)\s*$/i,
      text: isDE ? 'Geografischer Filter: "in NRW", "in Bayern"' : 'Geographic filter: "in NRW", "in Bavaria"',
      example: isDE ? 'Gemeinden in Nordrhein-Westfalen' : 'Municipalities in North Rhine-Westphalia',
      category: isDE ? 'Ort' : 'Location',
      color: 'success',
      priority: 8
    },
    // Date range
    {
      id: 'date',
      trigger: isDE ? /\b(zwischen|von.*bis|ab|seit|bis)\b/i : /\b(between|from.*to|since|until)\b/i,
      text: isDE ? 'Datumsbereich: "zwischen 1.1. und 31.3."' : 'Date range: "between Jan 1 and Mar 31"',
      example: isDE ? 'Events zwischen 1. Januar und 31. März 2025' : 'Events between January 1 and March 31, 2025',
      category: isDE ? 'Datum' : 'Date',
      color: 'warning',
      priority: 7
    },
    // Boolean OR
    {
      id: 'or',
      trigger: /\b(oder|or)\b/i,
      text: isDE ? 'ODER-Verknüpfung für mehrere Optionen' : 'OR operator for multiple options',
      example: isDE ? 'Bürgermeister in NRW oder Bayern' : 'Mayors in NRW or Bavaria',
      category: 'OR',
      color: 'purple',
      priority: 6
    },
    // Negation
    {
      id: 'not',
      trigger: isDE ? /\b(ohne|nicht|keine)\b/i : /\b(without|not|no)\b/i,
      text: isDE ? 'Negation: "OHNE Pain Points"' : 'Negation: "WITHOUT pain points"',
      example: isDE ? 'Gemeinden ohne Pain Points' : 'Municipalities without pain points',
      category: isDE ? 'OHNE' : 'NOT',
      color: 'error',
      priority: 6
    },
    // Aggregation
    {
      id: 'aggregate',
      trigger: isDE ? /\b(durchschnitt|summe|minimum|maximum|mittel)/i : /\b(average|sum|minimum|maximum|mean)/i,
      text: isDE ? 'Aggregationen: Durchschnitt, Summe, Min/Max' : 'Aggregations: Average, Sum, Min/Max',
      example: isDE ? 'Durchschnittliche Anzahl Pain Points pro Gemeinde' : 'Average number of pain points per municipality',
      category: isDE ? 'Statistik' : 'Stats',
      color: 'teal',
      priority: 5
    },
    // Relations
    {
      id: 'relation',
      trigger: isDE ? /\b(deren|dessen|die\s+mit|verbunden|relation)/i : /\b(whose|which\s+have|connected|related)/i,
      text: isDE ? 'Relationen: "Personen, deren Gemeinden..."' : 'Relations: "People whose municipalities..."',
      example: isDE ? 'Personen, deren Gemeinden Pain Points haben' : 'People whose municipalities have pain points',
      category: isDE ? 'Relation' : 'Relation',
      color: 'indigo',
      priority: 4
    },
    // Write mode hints
    {
      id: 'edit',
      trigger: isDE ? /^(ändere|setze|aktualisiere)/i : /^(change|set|update)/i,
      text: isDE ? 'Bearbeiten: "Ändere den Namen von..."' : 'Edit: "Change the name of..."',
      example: isDE ? 'Ändere den Namen von Gemeinde X zu Y' : 'Change the name of municipality X to Y',
      category: isDE ? 'Bearbeiten' : 'Edit',
      color: 'orange',
      priority: 9
    },
    // Delete hint (write mode)
    {
      id: 'delete',
      trigger: isDE ? /^(lösche|entferne|delete)/i : /^(delete|remove)/i,
      text: isDE ? 'Löschen: "Lösche Entity..." (mit Bestätigung)' : 'Delete: "Delete entity..." (with confirmation)',
      example: isDE ? 'Lösche alle Pain Points von Gemeinde X' : 'Delete all pain points from municipality X',
      category: isDE ? 'Löschen' : 'Delete',
      color: 'red',
      priority: 8
    },
    // Export hint
    {
      id: 'export',
      trigger: isDE ? /\b(export|csv|excel|json)\b/i : /\b(export|csv|excel|json)\b/i,
      text: isDE ? 'Export: "Exportiere als CSV/Excel/JSON"' : 'Export: "Export as CSV/Excel/JSON"',
      example: isDE ? 'Exportiere alle Bürgermeister als Excel' : 'Export all mayors as Excel',
      category: 'Export',
      color: 'cyan',
      priority: 5
    },
    // Undo hint
    {
      id: 'undo',
      trigger: isDE ? /\b(rückgängig|undo|zurück)/i : /\b(undo|revert|back)/i,
      text: isDE ? 'Rückgängig: "Mache letzte Änderung rückgängig"' : 'Undo: "Undo last change"',
      example: isDE ? 'Mache die letzte Änderung rückgängig' : 'Undo the last change',
      category: 'Undo',
      color: 'grey',
      priority: 3
    },
    // Help
    {
      id: 'help',
      trigger: isDE ? /^(hilfe|\?|help)/i : /^(help|\?)/i,
      text: isDE ? 'Hilfe anzeigen' : 'Show help',
      example: isDE ? 'Hilfe' : 'Help',
      category: isDE ? 'Hilfe' : 'Help',
      color: 'blue-grey',
      priority: 2
    }
  ]
})

// Filter hints based on current input and mode
const visibleHints = computed(() => {
  const input = props.inputText.trim().toLowerCase()

  // Don't show hints for empty input or very short input
  if (input.length < 2) {
    return []
  }

  // Filter hints that match the current input
  const matchingHints = allHints.value.filter(hint => {
    // In read mode, hide write-specific hints
    if (!props.isWriteMode && ['edit', 'delete'].includes(hint.id)) {
      return false
    }

    // In write mode, prioritize write hints
    if (props.isWriteMode && ['count', 'list', 'aggregate'].includes(hint.id)) {
      return false
    }

    // Check if trigger matches
    if (hint.trigger instanceof RegExp) {
      return hint.trigger.test(input)
    }
    return input.includes(hint.trigger.toLowerCase())
  })

  // Sort by priority and limit to 3 hints
  return matchingHints
    .sort((a, b) => b.priority - a.priority)
    .slice(0, 3)
})

// Highlight the trigger word in the hint text (with XSS protection)
function highlightTrigger(text: string, trigger: string | RegExp): string {
  // First escape the text to prevent XSS
  const escapedText = escapeHtml(text)

  if (trigger instanceof RegExp) {
    // For regex triggers, we highlight based on common keywords
    // Match quoted text in the escaped string (quotes are now &quot;)
    const keywords = escapedText.match(/&quot;([^&]+)&quot;/g)
    if (keywords) {
      let result = escapedText
      keywords.forEach(kw => {
        result = result.replace(kw, `<strong>${kw}</strong>`)
      })
      return result
    }
    return escapedText
  }

  const escapedTrigger = escapeHtml(trigger).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return escapedText.replace(new RegExp(`(${escapedTrigger})`, 'gi'), '<strong>$1</strong>')
}
</script>

<style scoped>
.input-hints {
  background: rgb(var(--v-theme-surface-variant));
  border-radius: 8px;
  padding: 8px 12px;
  margin-bottom: 8px;
  font-size: 0.8rem;
}

.input-hints__header {
  display: flex;
  align-items: center;
  color: rgb(var(--v-theme-on-surface-variant));
  font-weight: 500;
  margin-bottom: 6px;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.input-hints__list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.input-hints__item {
  display: flex;
  align-items: center;
  padding: 4px 6px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.input-hints__item:hover {
  background: rgba(var(--v-theme-primary), 0.1);
}

.input-hints__text {
  flex: 1;
  color: rgb(var(--v-theme-on-surface-variant));
}

.input-hints__text :deep(strong) {
  color: rgb(var(--v-theme-primary));
  font-weight: 600;
}

.input-hints__example {
  font-size: 0.7rem;
  background: rgba(var(--v-theme-on-surface), 0.08);
  padding: 2px 6px;
  border-radius: 4px;
  color: rgb(var(--v-theme-on-surface-variant));
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Transition */
.hints-fade-enter-active,
.hints-fade-leave-active {
  transition: all 0.2s ease;
}

.hints-fade-enter-from,
.hints-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
