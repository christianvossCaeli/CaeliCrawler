<template>
  <div class="shared-summary-view">
    <!-- Password Gate -->
    <v-container v-if="requiresPassword && !isAuthenticated" class="fill-height">
      <v-row justify="center">
        <v-col cols="12" sm="8" md="6" lg="4">
          <v-card class="pa-4">
            <v-card-title class="text-center">
              <v-icon color="primary" size="48" class="mb-2">mdi-lock</v-icon>
              <div>{{ t('summaries.passwordProtected') }}</div>
            </v-card-title>

            <v-card-text>
              <p class="text-body-2 text-center text-medium-emphasis mb-4">
                {{ t('summaries.enterPasswordToView') }}
              </p>

              <v-form @submit.prevent="authenticate">
                <v-text-field
                  v-model="password"
                  :label="t('summaries.password')"
                  :error-messages="passwordError"
                  type="password"
                  autofocus
                  @update:model-value="passwordError = ''"
                />

                <v-btn
                  type="submit"
                  color="primary"
                  block
                  :loading="isAuthenticating"
                  class="mt-4"
                >
                  {{ t('summaries.unlock') }}
                </v-btn>
              </v-form>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-container>

    <!-- Loading -->
    <v-container v-else-if="isLoading" class="fill-height">
      <v-row justify="center" align="center">
        <v-col cols="auto" class="text-center">
          <v-progress-circular indeterminate color="primary" size="64" />
          <p class="mt-4 text-body-1">{{ t('summaries.loadingShared') }}</p>
        </v-col>
      </v-row>
    </v-container>

    <!-- Error State -->
    <v-container v-else-if="error" class="fill-height">
      <v-row justify="center">
        <v-col cols="12" sm="8" md="6" lg="4">
          <v-card class="pa-4 text-center">
            <v-icon color="error" size="64" class="mb-4">mdi-alert-circle</v-icon>
            <v-card-title>{{ t('summaries.shareError') }}</v-card-title>
            <v-card-text>
              <p class="text-body-2 text-medium-emphasis">{{ error }}</p>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-container>

    <!-- Summary Content -->
    <template v-else-if="summary">
      <!-- Header -->
      <v-app-bar flat color="surface" class="border-b">
        <v-app-bar-title>
          <div class="d-flex align-center">
            <v-icon color="primary" class="mr-2">mdi-view-dashboard</v-icon>
            <span>{{ summary.name }}</span>
          </div>
        </v-app-bar-title>

        <template #append>
          <!-- Export Button (if allowed) -->
          <v-btn
            v-if="allowExport"
            variant="outlined"
            size="small"
            :loading="isExporting"
            @click="exportPdf"
          >
            <v-icon start>mdi-file-pdf-box</v-icon>
            {{ t('summaries.exportPdf') }}
          </v-btn>

          <!-- Branding -->
          <div class="ml-4 text-caption text-medium-emphasis">
            {{ t('summaries.poweredBy') }}
          </div>
        </template>
      </v-app-bar>

      <!-- Description -->
      <v-container v-if="summary.description" class="py-2">
        <p class="text-body-2 text-medium-emphasis">{{ summary.description }}</p>
      </v-container>

      <!-- Widgets Grid -->
      <v-container fluid class="pa-4">
        <div class="widgets-grid">
          <div
            v-for="widget in widgets"
            :key="widget.id"
            class="widget-item"
            :style="getWidgetStyle(widget)"
          >
            <v-card height="100%">
              <v-card-title class="text-subtitle-1 py-2 px-3">
                {{ widget.title }}
                <span v-if="widget.subtitle" class="text-caption text-medium-emphasis ml-2">
                  {{ widget.subtitle }}
                </span>
              </v-card-title>
              <v-divider />
              <v-card-text class="pa-2 widget-content">
                <component
                  :is="getVisualizationComponent(widget.widget_type)"
                  v-if="getWidgetData(widget.id)"
                  :data="getWidgetData(widget.id)"
                  :config="widget.visualization_config || {}"
                />
                <div v-else class="d-flex align-center justify-center fill-height">
                  <span class="text-medium-emphasis">{{ t('summaries.noData') }}</span>
                </div>
              </v-card-text>
            </v-card>
          </div>
        </div>

        <!-- Last Updated -->
        <div v-if="lastUpdated" class="text-center mt-4 text-caption text-medium-emphasis">
          {{ t('summaries.lastUpdated') }}: {{ formatDateTime(lastUpdated) }}
        </div>
      </v-container>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, type Component } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '@/services/api'

// Import visualization components
import TableVisualization from '@/components/smartquery/visualizations/TableVisualization.vue'
import BarChartVisualization from '@/components/smartquery/visualizations/BarChartVisualization.vue'
import LineChartVisualization from '@/components/smartquery/visualizations/LineChartVisualization.vue'
import PieChartVisualization from '@/components/smartquery/visualizations/PieChartVisualization.vue'
import StatCardVisualization from '@/components/smartquery/visualizations/StatCardVisualization.vue'
import TextVisualization from '@/components/smartquery/visualizations/TextVisualization.vue'
import ComparisonVisualization from '@/components/smartquery/visualizations/ComparisonVisualization.vue'
import MapVisualization from '@/components/smartquery/visualizations/MapVisualization.vue'
import { useFileDownload } from '@/composables/useFileDownload'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('SharedSummaryView')

const { t } = useI18n()
const { downloadBlob } = useFileDownload()
const route = useRoute()

// State
const isLoading = ref(true)
const error = ref<string | null>(null)
const requiresPassword = ref(false)
const isAuthenticated = ref(false)
const password = ref('')
const passwordError = ref('')
const isAuthenticating = ref(false)
const isExporting = ref(false)
const allowExport = ref(false)

interface SharedSummaryData {
  summary: {
    id: string
    name: string
    description?: string
  }
  widgets: Array<{
    id: string
    widget_type: string
    title: string
    subtitle?: string
    position: { x: number; y: number; w: number; h: number }
    visualization_config?: Record<string, unknown>
  }>
  widget_data: Record<string, unknown>
  last_updated?: string
  allow_export: boolean
}

const summary = ref<SharedSummaryData['summary'] | null>(null)
const widgets = ref<SharedSummaryData['widgets']>([])
const widgetData = ref<Record<string, unknown>>({})
const lastUpdated = ref<string | null>(null)

const token = computed(() => route.params.token as string)

// Visualization component mapping
const visualizationComponents: Record<string, Component> = {
  table: TableVisualization,
  bar_chart: BarChartVisualization,
  line_chart: LineChartVisualization,
  pie_chart: PieChartVisualization,
  stat_card: StatCardVisualization,
  text: TextVisualization,
  comparison: ComparisonVisualization,
  map: MapVisualization,
}

function getVisualizationComponent(widgetType: string): Component {
  return visualizationComponents[widgetType] || TableVisualization
}

function getWidgetData(widgetId: string): unknown {
  return widgetData.value[widgetId]
}

function getWidgetStyle(widget: SharedSummaryData['widgets'][0]): Record<string, string> {
  return {
    gridColumn: `${widget.position.x + 1} / span ${widget.position.w}`,
    gridRow: `${widget.position.y + 1} / span ${widget.position.h}`,
  }
}

function formatDateTime(dateStr: string): string {
  // Use browser locale for consistent date formatting (no hardcoded locale)
  return new Date(dateStr).toLocaleString(undefined, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function loadSharedSummary(pwd?: string) {
  isLoading.value = true
  error.value = null

  try {
    const response = await api.post<SharedSummaryData>(`/api/v1/summaries/shared/${token.value}`, {
      password: pwd,
    })

    summary.value = response.data.summary
    widgets.value = response.data.widgets
    widgetData.value = response.data.widget_data
    lastUpdated.value = response.data.last_updated || null
    allowExport.value = response.data.allow_export
    isAuthenticated.value = true
    requiresPassword.value = false
  } catch (e: unknown) {
    const err = e as { response?: { status: number; data?: { detail?: string } } }
    if (err.response?.status === 401) {
      // Password required
      requiresPassword.value = true
      if (pwd) {
        passwordError.value = t('summaries.wrongPassword')
        password.value = '' // Clear password field on wrong password
      }
    } else if (err.response?.status === 404) {
      error.value = t('summaries.shareNotFound')
    } else if (err.response?.status === 410) {
      error.value = t('summaries.shareExpired')
    } else {
      error.value = err.response?.data?.detail || t('summaries.shareLoadError')
    }
  } finally {
    isLoading.value = false
  }
}

async function authenticate() {
  if (!password.value) {
    passwordError.value = t('validation.required')
    return
  }

  isAuthenticating.value = true
  await loadSharedSummary(password.value)
  isAuthenticating.value = false
}

async function exportPdf() {
  if (!allowExport.value) return

  isExporting.value = true
  try {
    const response = await api.get(`/api/v1/summaries/shared/${token.value}/export`, {
      responseType: 'blob',
      params: { password: password.value || undefined },
    })

    // Download using safe composable with proper cleanup
    const blob = new Blob([response.data], { type: 'application/pdf' })
    downloadBlob(blob, `${summary.value?.name || 'summary'}.pdf`)
  } catch (e) {
    logger.error('Export failed:', e)
  } finally {
    isExporting.value = false
  }
}

onMounted(() => {
  loadSharedSummary()
})
</script>

<style scoped>
.shared-summary-view {
  min-height: 100vh;
  background: rgb(var(--v-theme-surface));
}

.widgets-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  min-height: 200px;
}

.widget-item {
  min-height: 200px;
}

.widget-content {
  height: calc(100% - 48px);
  overflow: auto;
}

@media (max-width: 960px) {
  .widgets-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* Tablet Portrait Breakpoint */
@media (max-width: 768px) {
  .widgets-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  .widget-item {
    min-height: 180px;
  }
}

@media (max-width: 600px) {
  .widgets-grid {
    grid-template-columns: 1fr;
  }
}
</style>
