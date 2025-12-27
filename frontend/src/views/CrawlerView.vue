<template>
  <div>
    <!-- Loading Overlay (only on initial load) -->
    <v-overlay :model-value="loading && initialLoad" class="align-center justify-center" persistent >
      <v-card class="pa-8 text-center" min-width="320" elevation="24">
        <v-progress-circular indeterminate size="80" width="6" color="primary" class="mb-4"></v-progress-circular>
        <div class="text-h6 mb-2">{{ $t('crawler.dataLoading') }}</div>
        <div class="text-body-2 text-medium-emphasis">{{ $t('crawler.loadingStatus') }}</div>
      </v-card>
    </v-overlay>

    <PageHeader
      :title="$t('crawler.title')"
      :subtitle="$t('crawler.subtitle')"
      icon="mdi-spider-web"
    >
      <template #actions>
        <v-btn
          color="primary"
          variant="tonal"
          prepend-icon="mdi-content-save-cog"
          @click="presetsDrawer = true"
        >
          {{ $t('crawlPresets.title') }}
          <v-badge
            v-if="presetsStore.favoriteCount > 0"
            :content="presetsStore.favoriteCount"
            color="warning"
            offset-x="-8"
            offset-y="-8"
          />
        </v-btn>
        <v-btn
          v-if="status.running_jobs > 0 || status.pending_jobs > 0"
          color="error"
          variant="outlined"
          prepend-icon="mdi-stop"
          :loading="stoppingAll"
          @click="stopAllCrawlers"
        >
          {{ $t('crawler.stopAll') }}
        </v-btn>
      </template>
    </PageHeader>

    <!-- Presets Drawer -->
    <v-navigation-drawer
      v-model="presetsDrawer"
      location="right"
      temporary
      width="600"
    >
      <div class="pa-4">
        <div class="d-flex align-center mb-4">
          <h2 class="text-h5">{{ $t('crawlPresets.title') }}</h2>
          <v-spacer />
          <v-btn
            icon
            variant="text"
            :aria-label="$t('common.closePanel')"
            @click="presetsDrawer = false"
          >
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </div>
        <CrawlPresetsTab />
      </div>
    </v-navigation-drawer>

    <!-- Live Status -->
    <v-row class="mb-4">
      <v-col cols="12" md="3">
        <v-card color="success" dark>
          <v-card-text class="text-center">
            <div class="text-h3">{{ status.worker_count }}</div>
            <div>{{ $t('crawler.activeWorkers') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card color="info" dark>
          <v-card-text class="text-center">
            <div class="text-h3">{{ status.running_jobs }}</div>
            <div>{{ $t('crawler.runningJobs') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card color="warning" dark>
          <v-card-text class="text-center">
            <div class="text-h3">{{ status.pending_jobs }}</div>
            <div>{{ $t('crawler.pendingJobs') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card color="primary" dark>
          <v-card-text class="text-center">
            <div class="text-h3">{{ stats.total_documents }}</div>
            <div>{{ $t('crawler.totalDocuments') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Running AI Tasks -->
    <v-card v-if="runningAiTasks.length > 0" class="mb-4" color="info-lighten-5">
      <v-card-title class="d-flex align-center">
        <v-icon color="info" class="mr-2 mdi-spin">mdi-loading</v-icon>
        {{ $t('crawler.aiTasks') }} ({{ runningAiTasks.length }})
        <v-spacer></v-spacer>
        <v-chip size="small" color="info">{{ $t('crawler.liveUpdates') }}</v-chip>
      </v-card-title>
      <v-card-text>
        <v-list dense>
          <v-list-item
            v-for="task in runningAiTasks"
            :key="task.id"
          >
            <template #prepend>
              <v-icon color="info" class="mdi-spin" size="small">mdi-brain</v-icon>
            </template>
            <v-list-item-title>{{ task.name }}</v-list-item-title>
            <v-list-item-subtitle>
              <span v-if="task.current_item">{{ $t('crawler.current') }}: {{ task.current_item }}</span>
              <span v-else>{{ $t('crawler.processing') }}</span>
              <span class="ml-2">{{ task.progress_current }}/{{ task.progress_total }}</span>
            </v-list-item-subtitle>
            <template #append>
              <div class="d-flex align-center">
                <v-progress-linear
                  :model-value="task.progress_percent ?? 0"
                  height="8"
                  rounded
                  color="info"
                  style="width: 100px"
                  class="mr-2"
                ></v-progress-linear>
                <span class="text-caption mr-2">{{ Math.round(task.progress_percent ?? 0) }}%</span>
                <v-btn
                  icon="mdi-stop"
                  size="small"
                  color="error"
                  variant="tonal"
                  :title="$t('crawler.cancel')"
                  :aria-label="$t('common.stopTask')"
                  @click.stop="cancelAiTask(task)"
                ></v-btn>
              </div>
            </template>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>

    <!-- Active Crawlers with Live Log -->
    <v-card v-if="runningJobs.length > 0" class="mb-4 card-running">
      <v-card-title class="d-flex align-center">
        <v-icon color="info" class="mr-2 mdi-spin">mdi-loading</v-icon>
        {{ $t('crawler.activeCrawlers') }} ({{ runningJobs.length }})
        <v-spacer></v-spacer>
        <v-chip size="small" color="info">{{ $t('crawler.liveUpdatesInterval') }}</v-chip>
      </v-card-title>
      <v-card-text>
        <v-expansion-panels variant="accordion">
          <v-expansion-panel
            v-for="rj in runningJobs"
            :key="rj.id"
            @group:selected="loadJobLog(rj.id)"
          >
            <v-expansion-panel-title>
              <div class="d-flex align-center w-100">
                <v-icon color="info" class="mr-2 mdi-spin" size="small">mdi-web-sync</v-icon>
                <div class="flex-grow-1">
                  <div class="font-weight-bold">{{ rj.source_name }}</div>
                  <div class="text-caption text-primary">
                    <v-icon size="x-small" class="mr-1">mdi-tag</v-icon>
                    {{ rj.category_name || $t('crawler.noCategory') }}
                  </div>
                  <div class="text-caption text-truncate" style="max-width: 400px;">
                    {{ rj.current_url || rj.base_url }}
                  </div>
                </div>
                <div class="d-flex align-center mr-4">
                  <v-chip size="x-small" color="primary" class="mr-1">
                    {{ rj.pages_crawled }} {{ $t('crawler.pages') }}
                  </v-chip>
                  <v-chip size="x-small" color="success" class="mr-1">
                    {{ rj.documents_found }} {{ $t('crawler.docs') }}
                  </v-chip>
                  <v-chip v-if="(rj.error_count ?? 0) > 0" size="x-small" color="warning">
                    {{ rj.error_count }} {{ $t('crawler.errors') }}
                  </v-chip>
                </div>
                <v-btn
                  icon="mdi-stop"
                  size="small"
                  color="error"
                  variant="tonal"
                  :title="$t('crawler.cancel')"
                  :aria-label="$t('common.stopTask')"
                  @click.stop="cancelJob(rj)"
                ></v-btn>
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <div v-if="jobLogs[rj.id]" class="pa-2">
                <div class="text-subtitle-2 mb-2">
                  {{ $t('crawler.currentUrl') }}:
                  <code class="text-caption">{{ jobLogs[rj.id].current_url || '-' }}</code>
                </div>
                <v-divider class="mb-2"></v-divider>
                <div class="text-subtitle-2 mb-1">{{ $t('crawler.recentActivities') }}:</div>
                <v-virtual-scroll
                  :items="jobLogs[rj.id].log_entries || []"
                  height="200"
                  item-height="32"
                >
                  <template #default="{ item }">
                    <div class="d-flex align-center py-1" style="font-family: monospace; font-size: 11px;">
                      <v-icon
                        :color="item.status === 'document' ? 'success' : (item.status === 'error' ? 'error' : 'grey')"
                        size="x-small"
                        class="mr-2"
                      >
                        {{ item.status === 'document' ? 'mdi-file-document' : (item.status === 'error' ? 'mdi-alert' : 'mdi-web') }}
                      </v-icon>
                      <span class="text-truncate flex-grow-1">{{ item.url }}</span>
                      <span class="text-caption text-medium-emphasis ml-2">{{ formatLogTime(item.timestamp) }}</span>
                    </div>
                  </template>
                </v-virtual-scroll>
              </div>
              <div v-else class="text-center pa-4">
                <v-progress-circular indeterminate size="24"></v-progress-circular>
                <div class="text-caption mt-2">{{ $t('crawler.loadingLog') }}</div>
              </div>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>
    </v-card>

    <!-- Jobs Table -->
    <v-card>
      <v-card-title>
        <v-row align="center">
          <v-col>{{ $t('crawler.crawlJobs') }}</v-col>
          <v-col cols="auto">
            <v-btn-toggle v-model="statusFilter" color="primary" mandatory>
              <v-btn value="">{{ $t('crawler.all') }}</v-btn>
              <v-btn value="RUNNING">{{ $t('crawler.running') }}</v-btn>
              <v-btn value="COMPLETED">{{ $t('crawler.completed') }}</v-btn>
              <v-btn value="FAILED">{{ $t('crawler.failed') }}</v-btn>
            </v-btn-toggle>
          </v-col>
        </v-row>
      </v-card-title>

      <v-data-table
        :headers="headers"
        :items="filteredJobs"
        :loading="loading"
        :items-per-page="20"
      >
        <template #item.status="{ item }">
          <v-chip :color="getStatusColor(item.status)" size="small">
            <v-icon v-if="item.status === 'RUNNING'" class="mr-1" size="small">mdi-loading mdi-spin</v-icon>
            {{ item.status }}
          </v-chip>
        </template>

        <template #item.scheduled_at="{ item }">
          {{ item.scheduled_at ? formatDate(item.scheduled_at) : '-' }}
        </template>

        <template #item.duration="{ item }">
          {{ item.duration_seconds ? formatDuration(item.duration_seconds) : '-' }}
        </template>

        <template #item.progress="{ item }">
          <div class="d-flex align-center">
            <template v-if="item.status === 'COMPLETED' || item.status === 'FAILED' || item.status === 'CANCELLED'">
              <v-chip v-if="(item.documents_new ?? 0) > 0" size="x-small" color="success" class="mr-1">
                {{ item.documents_new }} {{ $t('crawler.newDocuments') }}
              </v-chip>
              <v-chip size="x-small" color="info" class="mr-1">
                {{ item.documents_found ?? 0 }} {{ $t('crawler.documentsFound') }}
              </v-chip>
              <v-icon v-if="item.status === 'COMPLETED'" color="success" size="small">mdi-check-circle</v-icon>
              <v-icon v-else-if="item.status === 'FAILED'" color="error" size="small">mdi-alert-circle</v-icon>
              <v-icon v-else color="grey" size="small">mdi-cancel</v-icon>
            </template>
            <template v-else>
              <span class="mr-2">{{ item.pages_crawled ?? 0 }} {{ $t('crawler.pages') }}</span>
              <v-progress-circular
                indeterminate
                size="16"
                width="2"
                color="primary"
              ></v-progress-circular>
            </template>
          </div>
        </template>

        <template #item.actions="{ item }">
          <div class="table-actions">
            <v-btn
              v-if="item.status === 'RUNNING'"
              icon="mdi-stop"
              size="small"
              variant="tonal"
              color="error"
              :title="$t('common.cancel')"
              :aria-label="$t('common.stopTask')"
              @click="cancelJob(item)"
            ></v-btn>
            <v-btn
              v-if="item.status === 'FAILED' || item.status === 'CANCELLED'"
              icon="mdi-refresh"
              size="small"
              variant="tonal"
              color="warning"
              :title="$t('crawler.retry')"
              :aria-label="$t('crawler.retryJob')"
              @click="retryJob(item)"
            ></v-btn>
            <v-btn
              icon="mdi-information"
              size="small"
              variant="tonal"
              :title="$t('common.details')"
              :aria-label="$t('common.showDetails')"
              @click="showJobDetails(item)"
            ></v-btn>
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- Confirmation Dialog -->
    <v-dialog v-model="confirmDialog" max-width="450">
      <v-card>
        <v-card-title class="text-h6">
          <v-icon color="warning" class="mr-2">mdi-alert</v-icon>
          {{ confirmTitle }}
        </v-card-title>
        <v-card-text>{{ confirmMessage }}</v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="confirmDialog = false">
            {{ $t('common.cancel') }}
          </v-btn>
          <v-btn color="error" variant="flat" @click="executeConfirmedAction">
            {{ $t('common.confirm') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Job Details Dialog -->
    <v-dialog v-model="detailsDialog" max-width="800">
      <v-card v-if="selectedJob">
        <v-card-title>{{ $t('crawler.jobDetails') }}</v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="6">
              <strong>{{ $t('crawler.source') }}:</strong> {{ selectedJob.source_name }}
            </v-col>
            <v-col cols="6">
              <strong>{{ $t('crawler.category') }}:</strong> {{ selectedJob.category_name }}
            </v-col>
            <v-col cols="6">
              <strong>{{ $t('crawler.status') }}:</strong>
              <v-chip :color="getStatusColor(selectedJob.status)" size="small">
                {{ selectedJob.status }}
              </v-chip>
            </v-col>
            <v-col cols="6">
              <strong>{{ $t('crawler.duration') }}:</strong> {{ selectedJob.duration_seconds ? formatDuration(selectedJob.duration_seconds) : '-' }}
            </v-col>
          </v-row>

          <v-divider class="my-4"></v-divider>

          <v-row>
            <v-col cols="4">
              <v-card outlined>
                <v-card-text class="text-center">
                  <div class="text-h5">{{ selectedJob.pages_crawled }}</div>
                  <div class="text-caption">{{ $t('crawler.pagesCrawled') }}</div>
                </v-card-text>
              </v-card>
            </v-col>
            <v-col cols="4">
              <v-card outlined>
                <v-card-text class="text-center">
                  <div class="text-h5">{{ selectedJob.documents_found }}</div>
                  <div class="text-caption">{{ $t('crawler.documentsFound') }}</div>
                </v-card-text>
              </v-card>
            </v-col>
            <v-col cols="4">
              <v-card outlined>
                <v-card-text class="text-center">
                  <div class="text-h5">{{ selectedJob.documents_new }}</div>
                  <div class="text-caption">{{ $t('crawler.newDocuments') }}</div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>

          <div v-if="selectedJob.error_log && selectedJob.error_log.length > 0" class="mt-4">
            <strong>{{ $t('crawler.errors') }}:</strong>
            <v-alert
              v-for="(error, idx) in selectedJob.error_log"
              :key="idx"
              type="error"
              variant="tonal"
              class="mt-2"
            >
              {{ typeof error === 'string' ? error : error.error }}
            </v-alert>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-btn
            v-if="selectedJob.status === 'FAILED' || selectedJob.status === 'CANCELLED'"
            color="warning"
            variant="tonal"
            prepend-icon="mdi-refresh"
            @click="retryJob(selectedJob); detailsDialog = false"
          >
            {{ $t('crawler.retry') }}
          </v-btn>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="detailsDialog = false">{{ $t('crawler.close') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
/**
 * CrawlerView - Crawler monitoring and management
 *
 * Uses useCrawlerAdmin composable for all state and logic.
 * Supports real-time updates via SSE with polling fallback.
 */
import { onMounted } from 'vue'
import { useCrawlerAdmin } from '@/composables/useCrawlerAdmin'
import CrawlPresetsTab from '@/components/crawler/CrawlPresetsTab.vue'
import PageHeader from '@/components/common/PageHeader.vue'

// Initialize composable with all state and methods
const {
  // State
  loading,
  presetsDrawer,
  initialLoad,
  stoppingAll,
  jobs,
  runningJobs,
  runningAiTasks,
  jobLogs,
  statusFilter,
  detailsDialog,
  confirmDialog,
  confirmMessage,
  confirmTitle,
  selectedJob,
  status,
  stats,

  // Computed
  headers,
  filteredJobs,

  // Stores
  presetsStore,

  // Helper Functions
  getStatusColor,
  formatDate,
  formatDuration,
  formatLogTime,

  // Data Loading
  loadJobLog,

  // Job Actions
  cancelJob,
  retryJob,
  cancelAiTask,
  showJobDetails,

  // Confirmation
  executeConfirmedAction,

  // Stop All
  stopAllCrawlers,

  // Initialization
  initialize,
} = useCrawlerAdmin()

// Explicitly mark unused but template-required variables
void jobs

// Initialize on mount
onMounted(() => initialize())
</script>
