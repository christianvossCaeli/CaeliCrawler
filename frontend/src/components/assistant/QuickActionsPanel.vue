<template>
  <div class="quick-actions-panel">
    <div class="quick-actions-header" role="button" tabindex="0" :aria-expanded="isExpanded" @click="isExpanded = !isExpanded" @keydown.enter.prevent="isExpanded = !isExpanded" @keydown.space.prevent="isExpanded = !isExpanded">
      <div class="d-flex align-center">
        <v-icon size="small" class="mr-2">mdi-lightning-bolt</v-icon>
        <span class="text-caption font-weight-medium">{{ t('assistant.quickActions') }}</span>
      </div>
      <v-icon size="small">{{ isExpanded ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
    </div>

    <v-expand-transition>
      <div v-if="isExpanded" class="quick-actions-content">
        <div class="quick-actions-grid">
          <v-btn
            v-for="action in contextActions"
            :key="action.id"
            variant="tonal"
            size="small"
            class="quick-action-btn"
            @click="handleActionClick(action)"
          >
            <v-icon start size="small">{{ action.icon }}</v-icon>
            {{ action.label }}
          </v-btn>
        </div>
      </div>
    </v-expand-transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { AssistantContext } from '@/composables/useAssistant'

const props = defineProps<{
  context: AssistantContext
  mode: 'read' | 'write'
}>()

const emit = defineEmits<{
  action: [action: QuickAction]
  'start-wizard': [wizardType: string]
}>()

const { t } = useI18n()

export interface QuickAction {
  id: string
  label: string
  icon: string
  query: string
  action?: string  // 'edit', 'create', 'wizard'
  wizardType?: string  // For wizard actions
}

const isExpanded = ref(true)

// Handle action click - emit wizard event or regular action
function handleActionClick(action: QuickAction) {
  if (action.action === 'wizard' && action.wizardType) {
    emit('start-wizard', action.wizardType)
  } else {
    emit('action', action)
  }
}

// Generate context-aware actions based on current view mode
const contextActions = computed<QuickAction[]>(() => {
  const actions: QuickAction[] = []
  const viewMode = props.context.view_mode

  if (viewMode === 'detail' && props.context.current_entity_id) {
    // On entity detail page
    actions.push(
      {
        id: 'summary',
        label: t('assistant.summary'),
        icon: 'mdi-text-box-outline',
        query: '/summary'
      },
      {
        id: 'painpoints',
        label: t('assistant.painPoints'),
        icon: 'mdi-alert-circle-outline',
        query: t('assistant.queryPainPoints')
      },
      {
        id: 'relations',
        label: t('assistant.relations'),
        icon: 'mdi-link-variant',
        query: t('assistant.queryRelations')
      }
    )

    // Add edit action in write mode
    if (props.mode === 'write') {
      actions.push({
        id: 'edit',
        label: t('assistant.edit'),
        icon: 'mdi-pencil-outline',
        query: t('assistant.queryEdit'),
        action: 'edit'
      })
    }
  } else if (viewMode === 'list' && props.context.current_entity_type) {
    // On entity list page
    const entityType = props.context.current_entity_type
    actions.push(
      {
        id: 'filter',
        label: t('assistant.filter'),
        icon: 'mdi-filter-outline',
        query: '/search '
      },
      {
        id: 'all',
        label: t('assistant.showAll'),
        icon: 'mdi-view-list',
        query: t('assistant.queryShowAll', { type: entityType })
      },
      {
        id: 'withPainPoints',
        label: t('assistant.withPainPoints'),
        icon: 'mdi-alert',
        query: t('assistant.queryWithPainPoints', { type: entityType })
      }
    )

    // Add create wizard in write mode
    if (props.mode === 'write') {
      actions.push({
        id: 'create_wizard',
        label: t('assistant.createNew'),
        icon: 'mdi-plus-circle',
        query: '',
        action: 'wizard',
        wizardType: 'create_entity'
      })
    }
  } else if (viewMode === 'dashboard') {
    // On dashboard
    actions.push(
      {
        id: 'overview',
        label: t('assistant.overview'),
        icon: 'mdi-view-dashboard-outline',
        query: t('assistant.queryOverview')
      },
      {
        id: 'recentPainPoints',
        label: t('assistant.recentPainPoints'),
        icon: 'mdi-alert-circle',
        query: t('assistant.queryRecentPainPoints')
      },
      {
        id: 'municipalities',
        label: t('assistant.municipalities'),
        icon: 'mdi-domain',
        query: t('assistant.queryMunicipalities')
      },
      {
        id: 'help',
        label: t('assistant.help'),
        icon: 'mdi-help-circle-outline',
        query: '/help'
      }
    )
  } else {
    // Default actions
    actions.push(
      {
        id: 'search',
        label: t('assistant.search'),
        icon: 'mdi-magnify',
        query: '/search '
      },
      {
        id: 'help',
        label: t('assistant.help'),
        icon: 'mdi-help-circle-outline',
        query: '/help'
      }
    )
  }

  return actions
})
</script>

<style scoped>
.quick-actions-panel {
  border-bottom: 1px solid rgb(var(--v-theme-outline-variant));
  background: rgb(var(--v-theme-surface-variant));
  color: rgb(var(--v-theme-on-surface-variant));
}

.quick-actions-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  cursor: pointer;
  user-select: none;
}

.quick-actions-header:hover {
  background: rgba(var(--v-theme-on-surface-variant), 0.08);
}

.quick-actions-header:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: -2px;
}

.quick-actions-content {
  padding: 0 16px 12px;
}

.quick-actions-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.quick-action-btn {
  text-transform: none;
  font-weight: 400;
}
</style>
