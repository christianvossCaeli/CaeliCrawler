<template>
  <div v-if="isVisible" class="embedding-progress-indicator">
    <v-menu
      v-model="menuOpen"
      :close-on-content-click="false"
      location="bottom end"
      offset="8"
    >
      <template #activator="{ props }">
        <v-btn
          v-bind="props"
          icon
          variant="tonal"
          size="small"
          class="embedding-btn"
          :title="isRunning ? 'Embedding-Generierung läuft...' : `Embedding-Status: ${Math.round(overallProgress)}%`"
        >
          <v-badge
            v-if="isRunning"
            dot
            color="warning"
            location="top end"
          >
            <v-progress-circular
              indeterminate
              size="20"
              width="2"
            />
          </v-badge>
          <v-icon v-else size="20">mdi-vector-polyline</v-icon>
        </v-btn>
      </template>

      <v-card min-width="320" max-width="400">
        <v-card-title class="d-flex align-center py-2 px-3">
          <v-icon start size="small" :color="isRunning ? 'info' : 'success'">
            {{ isRunning ? 'mdi-cog-sync' : 'mdi-vector-polyline' }}
          </v-icon>
          <span class="text-body-1">Embedding-Status</span>
          <v-spacer />
          <v-btn
            icon
            variant="text"
            size="x-small"
            :loading="loading"
            title="Aktualisieren"
            @click="loadStats"
          >
            <v-icon size="16">mdi-refresh</v-icon>
          </v-btn>
        </v-card-title>

        <v-divider />

        <v-card-text class="pa-3">
          <!-- Running Status -->
          <v-alert
            v-if="isRunning"
            type="info"
            variant="tonal"
            density="compact"
            class="mb-3"
          >
            <template #prepend>
              <v-progress-circular
                indeterminate
                size="18"
                width="2"
                color="info"
              />
            </template>
            <div>
              <span class="font-weight-medium">Generierung läuft...</span>
              <div v-if="stats?.task_id" class="text-caption text-medium-emphasis">
                Task: {{ stats.task_id.substring(0, 8) }}...
              </div>
            </div>
          </v-alert>

          <!-- Progress Details -->
          <div class="progress-items">
            <!-- Entities -->
            <div class="progress-item mb-2">
              <div class="d-flex justify-space-between align-center mb-1">
                <span class="text-body-2">
                  <v-icon size="14" class="mr-1">mdi-database</v-icon>
                  Entities
                </span>
                <span class="text-caption text-medium-emphasis">
                  {{ stats?.entities_with_embedding || 0 }} / {{ stats?.entities_total || 0 }}
                </span>
              </div>
              <v-progress-linear
                :model-value="entitiesProgress"
                :color="entitiesProgress === 100 ? 'success' : 'primary'"
                height="6"
                rounded
              />
            </div>

            <!-- Types (combined) -->
            <div class="progress-item mb-2">
              <div class="d-flex justify-space-between align-center mb-1">
                <span class="text-body-2">
                  <v-icon size="14" class="mr-1">mdi-shape</v-icon>
                  Typen
                </span>
                <span class="text-caption text-medium-emphasis">
                  {{ typesWithEmbedding }} / {{ typesTotal }}
                </span>
              </div>
              <v-progress-linear
                :model-value="typesProgress"
                :color="typesProgress === 100 ? 'success' : 'secondary'"
                height="6"
                rounded
              />
            </div>

            <!-- Facet Values -->
            <div class="progress-item">
              <div class="d-flex justify-space-between align-center mb-1">
                <span class="text-body-2">
                  <v-icon size="14" class="mr-1">mdi-tag-multiple</v-icon>
                  Facetten-Werte
                </span>
                <span class="text-caption text-medium-emphasis">
                  {{ stats?.facet_values_with_embedding || 0 }} / {{ stats?.facet_values_total || 0 }}
                </span>
              </div>
              <v-progress-linear
                :model-value="facetValuesProgress"
                :color="facetValuesProgress === 100 ? 'success' : 'warning'"
                height="6"
                rounded
              />
            </div>
          </div>

          <!-- Overall Progress -->
          <v-divider class="my-3" />
          <div class="d-flex justify-space-between align-center">
            <span class="text-body-2 font-weight-medium">Gesamt</span>
            <v-chip
              size="small"
              :color="overallProgress === 100 ? 'success' : 'primary'"
              variant="tonal"
            >
              {{ Math.round(overallProgress) }}%
            </v-chip>
          </div>
        </v-card-text>

        <v-divider />

        <v-card-actions class="pa-2">
          <v-btn
            size="small"
            variant="text"
            color="primary"
            to="/admin/api-credentials"
            @click="menuOpen = false"
          >
            <v-icon start size="16">mdi-cog</v-icon>
            Einstellungen
          </v-btn>
          <v-spacer />
          <v-btn
            size="small"
            variant="text"
            @click="menuOpen = false"
          >
            Schließen
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-menu>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { getEmbeddingStats } from '@/services/api/admin'
import type { EmbeddingStats } from '@/services/api/admin'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const stats = ref<EmbeddingStats | null>(null)
const loading = ref(false)
const menuOpen = ref(false)
let pollingInterval: ReturnType<typeof setInterval> | null = null
let slowPollingInterval: ReturnType<typeof setInterval> | null = null

// Polling intervals
const FAST_POLL_MS = 3000 // 3 seconds when running
const SLOW_POLL_MS = 30000 // 30 seconds when idle (to detect new tasks)

// Computed properties
const isRunning = computed(() => stats.value?.task_running ?? false)
const isConfigured = computed(() => stats.value?.is_configured ?? false)

// Show indicator if user is editor, configured, and either running or has incomplete embeddings
const isVisible = computed(() => {
  if (!auth.isEditor) return false
  if (!isConfigured.value) return false
  if (isRunning.value) return true
  // Also show if there are missing embeddings
  return overallProgress.value < 100
})

const entitiesProgress = computed(() => {
  if (!stats.value || stats.value.entities_total === 0) return 0
  return (stats.value.entities_with_embedding / stats.value.entities_total) * 100
})

const typesTotal = computed(() => {
  if (!stats.value) return 0
  return (
    stats.value.entity_types_total +
    stats.value.facet_types_total +
    stats.value.categories_total +
    stats.value.relation_types_total
  )
})

const typesWithEmbedding = computed(() => {
  if (!stats.value) return 0
  return (
    stats.value.entity_types_with_embedding +
    stats.value.facet_types_with_embedding +
    stats.value.categories_with_embedding +
    stats.value.relation_types_with_embedding
  )
})

const typesProgress = computed(() => {
  if (typesTotal.value === 0) return 0
  return (typesWithEmbedding.value / typesTotal.value) * 100
})

const facetValuesProgress = computed(() => {
  if (!stats.value || stats.value.facet_values_total === 0) return 0
  return (stats.value.facet_values_with_embedding / stats.value.facet_values_total) * 100
})

const overallProgress = computed(() => {
  if (!stats.value) return 0
  const total =
    stats.value.entities_total +
    typesTotal.value +
    stats.value.facet_values_total
  if (total === 0) return 100
  const done =
    stats.value.entities_with_embedding +
    typesWithEmbedding.value +
    stats.value.facet_values_with_embedding
  return (done / total) * 100
})

async function loadStats() {
  loading.value = true
  try {
    const response = await getEmbeddingStats()
    stats.value = response.data
  } catch {
    // Silently fail - user might not have permissions
  } finally {
    loading.value = false
  }
}

function startFastPolling() {
  stopFastPolling() // Clear any existing fast polling
  pollingInterval = setInterval(() => {
    loadStats()
  }, FAST_POLL_MS)
}

function stopFastPolling() {
  if (pollingInterval) {
    clearInterval(pollingInterval)
    pollingInterval = null
  }
}

function startSlowPolling() {
  if (slowPollingInterval) return // Already running
  slowPollingInterval = setInterval(() => {
    loadStats()
  }, SLOW_POLL_MS)
}

function stopSlowPolling() {
  if (slowPollingInterval) {
    clearInterval(slowPollingInterval)
    slowPollingInterval = null
  }
}

// Watch for running state changes to switch polling speed
watch(isRunning, (running) => {
  if (running) {
    // Task is running: use fast polling, stop slow polling
    stopSlowPolling()
    startFastPolling()
  } else {
    // Task stopped: stop fast polling, resume slow polling
    stopFastPolling()
    startSlowPolling()
  }
})

// Initial load and start appropriate polling
onMounted(async () => {
  await loadStats()
  if (isRunning.value) {
    // Task already running: use fast polling
    startFastPolling()
  } else {
    // No task running: use slow polling to detect new tasks
    startSlowPolling()
  }
})

onUnmounted(() => {
  stopFastPolling()
  stopSlowPolling()
})
</script>

<style scoped>
.embedding-progress-indicator {
  display: flex;
  align-items: center;
}

.embedding-btn {
  --v-btn-color: #6366f1 !important;
  color: #6366f1 !important;
}

.embedding-btn :deep(.v-progress-circular) {
  color: #6366f1 !important;
}

.progress-items {
  display: flex;
  flex-direction: column;
}

.progress-item {
  min-width: 0;
}
</style>
