<template>
  <div class="quick-actions">
    <div
      class="quick-actions__header"
      role="button"
      tabindex="0"
      :aria-expanded="expanded"
      :aria-label="t('assistant.toggleQuickActions')"
      @click="expanded = !expanded"
      @keydown.enter.prevent="expanded = !expanded"
      @keydown.space.prevent="expanded = !expanded"
    >
      <span>
        <v-icon size="x-small" class="mr-1">mdi-lightning-bolt</v-icon>
        {{ t('assistant.quickActions') }}
      </span>
      <v-icon size="x-small">{{ expanded ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
    </div>
    <div v-if="expanded" class="quick-actions__content">
      <button
        v-for="action in quickActions"
        :key="action.id"
        class="quick-action-btn"
        :aria-label="action.label"
        @click="$emit('action', action)"
      >
        <v-icon size="14">{{ action.icon }}</v-icon>
        {{ action.label }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { AssistantContext } from '@/composables/assistant/types'

const props = defineProps<{
  currentContext: AssistantContext
}>()

defineEmits<{
  action: [action: { id: string; label: string; icon: string; query: string }]
}>()

const { t } = useI18n()
const expanded = ref(true)

interface QuickAction {
  id: string
  label: string
  icon: string
  query: string
}

const quickActions = computed<QuickAction[]>(() => {
  const actions: QuickAction[] = []
  const viewMode = props.currentContext.view_mode

  if (viewMode === 'detail' && props.currentContext.current_entity_id) {
    actions.push(
      { id: 'summary', label: t('assistant.summary'), icon: 'mdi-text-box-outline', query: '/summary' },
      { id: 'painpoints', label: 'Pain Points', icon: 'mdi-alert-circle-outline', query: 'Zeige Pain Points' },
    )
  } else if (viewMode === 'dashboard') {
    actions.push(
      { id: 'overview', label: t('assistant.overview'), icon: 'mdi-view-dashboard-outline', query: 'Gib mir einen Überblick' },
      { id: 'help', label: t('assistant.help'), icon: 'mdi-help-circle-outline', query: '/help' },
    )
  } else {
    actions.push(
      { id: 'search', label: t('assistant.search'), icon: 'mdi-magnify', query: '/search ' },
      { id: 'help', label: t('assistant.help'), icon: 'mdi-help-circle-outline', query: '/help' },
    )
  }

  return actions
})
</script>

<style scoped>
@import './styles/chat-assistant.css';
</style>
