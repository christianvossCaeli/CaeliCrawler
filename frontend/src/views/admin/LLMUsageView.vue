<template>
  <div>
    <!-- Header -->
    <PageHeader
      :title="t('admin.llmUsage.title')"
      :subtitle="t('admin.llmUsage.subtitle')"
      icon="mdi-brain"
    >
      <template #actions>
        <v-btn variant="tonal" :loading="isLoading" @click="refresh">
          <v-icon start>mdi-refresh</v-icon>
          {{ t('common.refresh') }}
        </v-btn>
        <v-menu>
          <template #activator="{ props: menuProps }">
            <v-btn variant="tonal" color="primary" v-bind="menuProps">
              <v-icon start>mdi-download</v-icon>
              {{ t('common.export') }}
            </v-btn>
          </template>
          <v-list>
            <v-list-item @click="exportData('csv')">
              <v-list-item-title>CSV</v-list-item-title>
            </v-list-item>
            <v-list-item @click="exportData('json')">
              <v-list-item-title>JSON</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
      </template>
    </PageHeader>

    <!-- Error Alert -->
    <v-alert
      v-if="store.error"
      type="error"
      variant="tonal"
      class="mb-4"
      closable
      @click:close="store.error = null"
    >
      <div class="d-flex align-center justify-space-between">
        <div>
          <v-icon start>mdi-alert-circle</v-icon>
          {{ store.error }}
        </div>
        <v-btn variant="text" size="small" @click="refresh">
          <v-icon start size="small">mdi-refresh</v-icon>
          {{ t('common.retry') }}
        </v-btn>
      </div>
    </v-alert>

    <!-- Budget Warnings -->
    <v-alert
      v-if="store.hasCritical"
      type="error"
      variant="tonal"
      class="mb-4"
      closable
    >
      <v-icon start>mdi-alert-circle</v-icon>
      {{ t('admin.llmUsage.budget.criticalWarning') }}
    </v-alert>
    <v-alert
      v-else-if="store.hasWarnings"
      type="warning"
      variant="tonal"
      class="mb-4"
      closable
    >
      <v-icon start>mdi-alert</v-icon>
      {{ t('admin.llmUsage.budget.warningAlert') }}
    </v-alert>

    <!-- Summary Cards -->
    <v-row class="mb-4">
      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="text-center">
            <v-icon size="32" color="primary" class="mb-2">mdi-counter</v-icon>
            <div class="text-h4">{{ formatNumber(store.totalRequests) }}</div>
            <div class="text-caption text-medium-emphasis">
              {{ t('admin.llmUsage.stats.requests') }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="text-center">
            <v-icon size="32" color="info" class="mb-2">mdi-text-box-multiple</v-icon>
            <div class="text-h4">{{ formatTokens(store.totalTokens) }}</div>
            <div class="text-caption text-medium-emphasis">
              {{ t('admin.llmUsage.stats.tokens') }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="text-center">
            <v-icon size="32" color="success" class="mb-2">mdi-currency-usd</v-icon>
            <div class="text-h4">{{ formatCost(store.totalCostCents) }}</div>
            <div class="text-caption text-medium-emphasis">
              {{ t('admin.llmUsage.stats.cost') }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="text-center">
            <v-icon size="32" color="warning" class="mb-2">mdi-chart-line</v-icon>
            <div class="text-h4">{{ formatCost(store.projectedCostCents) }}</div>
            <div class="text-caption text-medium-emphasis">
              {{ t('admin.llmUsage.stats.projected') }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row align="center">
          <v-col cols="12" sm="6" md="3">
            <v-select
              v-model="selectedPeriod"
              :label="t('admin.llmUsage.filters.period')"
              :items="periodOptions"
              hide-details
              @update:model-value="onFilterChange"
            />
          </v-col>
          <v-col cols="12" sm="6" md="3">
            <v-select
              v-model="selectedProvider"
              :label="t('admin.llmUsage.filters.provider')"
              :items="providerOptions"
              clearable
              hide-details
              @update:model-value="onFilterChange"
            />
          </v-col>
          <v-col cols="12" sm="6" md="3">
            <v-select
              v-model="selectedTaskType"
              :label="t('admin.llmUsage.filters.taskType')"
              :items="taskTypeOptions"
              clearable
              hide-details
              @update:model-value="onFilterChange"
            />
          </v-col>
          <v-col cols="12" sm="6" md="3">
            <v-btn
              variant="text"
              color="primary"
              @click="clearFilters"
            >
              <v-icon start>mdi-filter-off</v-icon>
              {{ t('admin.llmUsage.filters.clear') }}
            </v-btn>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Charts Row -->
    <v-row class="mb-4">
      <v-col cols="12" md="8">
        <v-card>
          <v-card-title>
            <v-icon start>mdi-chart-timeline-variant</v-icon>
            {{ t('admin.llmUsage.charts.trend') }}
          </v-card-title>
          <v-card-text>
            <UsageTrendChart
              v-if="store.analytics?.daily_trend"
              :data="store.analytics.daily_trend"
            />
            <div v-else class="text-center pa-4 text-medium-emphasis">
              {{ t('admin.llmUsage.noData') }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>
            <v-icon start>mdi-chart-pie</v-icon>
            {{ t('admin.llmUsage.charts.byModel') }}
          </v-card-title>
          <v-card-text>
            <ModelDistributionChart
              v-if="store.analytics?.by_model?.length"
              :data="store.analytics.by_model"
            />
            <div v-else class="text-center pa-4 text-medium-emphasis">
              {{ t('admin.llmUsage.noData') }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Usage by User -->
    <v-card class="mb-4">
      <v-card-title>
        <v-icon start>mdi-account-group</v-icon>
        {{ t('admin.llmUsage.tables.byUser') }}
      </v-card-title>
      <v-card-subtitle class="pb-2">
        {{ t('admin.llmUsage.tables.byUserHint') }}
      </v-card-subtitle>
      <v-data-table
        :headers="userHeaders"
        :items="store.analytics?.by_user || []"
        :items-per-page="10"
        density="compact"
      >
        <template #item.user_name="{ item }">
          <div class="d-flex align-center">
            <v-avatar size="28" color="primary" class="mr-2">
              <span class="text-caption">{{ getUserInitials(item) }}</span>
            </v-avatar>
            <div>
              <div class="font-weight-medium">
                {{ item.user_name || t('admin.llmUsage.systemUser') }}
              </div>
              <div class="text-caption text-medium-emphasis">
                {{ item.user_email || '-' }}
              </div>
            </div>
          </div>
        </template>
        <template #item.total_tokens="{ item }">
          <div>
            <div>{{ formatTokens(item.total_tokens) }}</div>
            <div class="text-caption text-medium-emphasis">
              ↑{{ formatTokens(item.prompt_tokens) }} / ↓{{ formatTokens(item.completion_tokens) }}
            </div>
          </div>
        </template>
        <template #item.cost_cents="{ item }">
          <span class="font-weight-medium">{{ formatCost(item.cost_cents) }}</span>
        </template>
        <template #item.models_used="{ item }">
          <div class="d-flex flex-wrap ga-1">
            <v-chip
              v-for="model in item.models_used.slice(0, 3)"
              :key="model"
              size="x-small"
              label
            >
              {{ model }}
            </v-chip>
            <v-chip v-if="item.models_used.length > 3" size="x-small" variant="text">
              +{{ item.models_used.length - 3 }}
            </v-chip>
          </div>
        </template>
        <template #item.has_credentials="{ item }">
          <v-tooltip :text="item.has_credentials ? t('admin.llmUsage.hasCredentials') : t('admin.llmUsage.noCredentials')">
            <template #activator="{ props: tooltipProps }">
              <v-icon
                v-bind="tooltipProps"
                :color="item.has_credentials ? 'success' : 'warning'"
                size="small"
              >
                {{ item.has_credentials ? 'mdi-key-check' : 'mdi-key-remove' }}
              </v-icon>
            </template>
          </v-tooltip>
        </template>
        <template #no-data>
          <div class="text-center py-8">
            <v-icon size="48" color="grey-lighten-1" class="mb-3">mdi-account-group</v-icon>
            <p class="text-body-2 text-medium-emphasis">{{ t('admin.llmUsage.noData') }}</p>
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- Tables Row -->
    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-icon start>mdi-format-list-bulleted-type</v-icon>
            {{ t('admin.llmUsage.tables.byTaskType') }}
          </v-card-title>
          <v-data-table
            :headers="taskTypeHeaders"
            :items="store.analytics?.by_task || []"
            :items-per-page="5"
            density="compact"
          >
            <template #item.task_type="{ item }">
              <v-chip size="small" label>{{ getTaskTypeLabel(item.task_type) }}</v-chip>
            </template>
            <template #item.total_tokens="{ item }">
              {{ formatTokens(item.total_tokens) }}
            </template>
            <template #item.cost_cents="{ item }">
              {{ formatCost(item.cost_cents) }}
            </template>
            <template #item.avg_duration_ms="{ item }">
              {{ item.avg_duration_ms?.toFixed(0) || '-' }} ms
            </template>
            <template #no-data>
              <div class="text-center py-8">
                <v-icon size="48" color="grey-lighten-1" class="mb-3">mdi-format-list-bulleted-type</v-icon>
                <p class="text-body-2 text-medium-emphasis">{{ t('admin.llmUsage.noData') }}</p>
              </div>
            </template>
          </v-data-table>
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-icon start>mdi-folder-multiple</v-icon>
            {{ t('admin.llmUsage.tables.byCategory') }}
          </v-card-title>
          <v-data-table
            :headers="categoryHeaders"
            :items="store.analytics?.by_category || []"
            :items-per-page="5"
            density="compact"
          >
            <template #item.category_name="{ item }">
              {{ item.category_name || t('admin.llmUsage.uncategorized') }}
            </template>
            <template #item.total_tokens="{ item }">
              {{ formatTokens(item.total_tokens) }}
            </template>
            <template #item.cost_cents="{ item }">
              {{ formatCost(item.cost_cents) }}
            </template>
            <template #no-data>
              <div class="text-center py-8">
                <v-icon size="48" color="grey-lighten-1" class="mb-3">mdi-folder-multiple</v-icon>
                <p class="text-body-2 text-medium-emphasis">{{ t('admin.llmUsage.noData') }}</p>
              </div>
            </template>
          </v-data-table>
        </v-card>
      </v-col>
    </v-row>

    <!-- Top Consumers -->
    <v-card class="mb-4">
      <v-card-title>
        <v-icon start>mdi-podium</v-icon>
        {{ t('admin.llmUsage.tables.topConsumers') }}
      </v-card-title>
      <v-data-table
        :headers="topConsumersHeaders"
        :items="store.analytics?.top_consumers || []"
        :items-per-page="10"
        density="compact"
      >
        <template #item.task_type="{ item }">
          <v-chip size="small" label>{{ getTaskTypeLabel(item.task_type) }}</v-chip>
        </template>
        <template #item.total_tokens="{ item }">
          {{ formatTokens(item.total_tokens) }}
        </template>
        <template #item.cost_cents="{ item }">
          {{ formatCost(item.cost_cents) }}
        </template>
        <template #no-data>
          <div class="text-center py-8">
            <v-icon size="48" color="grey-lighten-1" class="mb-3">mdi-podium</v-icon>
            <p class="text-body-2 text-medium-emphasis">{{ t('admin.llmUsage.noData') }}</p>
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- Budget Configuration Section -->
    <!-- Info Panel -->
    <v-alert
      v-if="!budgetInfoHidden"
      type="info"
      variant="tonal"
      density="compact"
      class="mb-4"
      closable
      @click:close="hideBudgetInfo"
    >
      <template #prepend>
        <v-icon>mdi-information-outline</v-icon>
      </template>
      <div>
        <strong>{{ t('admin.llmUsage.budget.info.title') }}</strong>
        <div class="text-caption mt-1">{{ t('admin.llmUsage.budget.info.overview') }}</div>
        <div class="text-caption mt-2">
          <strong>{{ t('admin.llmUsage.budget.info.typesTitle') }}</strong>
          <ul class="ml-4 mt-1">
            <li><strong>GLOBAL:</strong> {{ t('admin.llmUsage.budget.info.typeGlobal') }}</li>
            <li><strong>USER:</strong> {{ t('admin.llmUsage.budget.info.typeUser') }}</li>
            <li><strong>CATEGORY:</strong> {{ t('admin.llmUsage.budget.info.typeCategory') }}</li>
            <li><strong>TASK_TYPE:</strong> {{ t('admin.llmUsage.budget.info.typeTaskType') }}</li>
            <li><strong>MODEL:</strong> {{ t('admin.llmUsage.budget.info.typeModel') }}</li>
          </ul>
        </div>
        <div class="text-caption mt-2">
          <strong>{{ t('admin.llmUsage.budget.info.blockingTitle') }}</strong>
          {{ t('admin.llmUsage.budget.info.blockingDescription') }}
        </div>
      </div>
    </v-alert>
    <v-btn
      v-else
      variant="text"
      size="x-small"
      color="info"
      class="mb-2"
      prepend-icon="mdi-information-outline"
      @click="showBudgetInfo"
    >
      {{ t('admin.llmUsage.budget.info.show') }}
    </v-btn>

    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-wallet</v-icon>
        {{ t('admin.llmUsage.budget.title') }}
        <v-spacer />
        <v-btn variant="tonal" color="primary" size="small" @click="openBudgetDialog()">
          <v-icon start>mdi-plus</v-icon>
          {{ t('admin.llmUsage.budget.add') }}
        </v-btn>
      </v-card-title>
      <v-data-table
        :headers="budgetHeaders"
        :items="store.budgetConfigs"
        :loading="store.isLoadingBudgets"
        density="compact"
      >
        <template #item.budget_type="{ item }">
          <v-chip size="small" :color="getBudgetTypeColor(item.budget_type)" label>
            {{ getBudgetTypeLabel(item.budget_type) }}
          </v-chip>
        </template>
        <template #item.monthly_limit_cents="{ item }">
          {{ formatCost(item.monthly_limit_cents) }}
        </template>
        <template #item.is_active="{ item }">
          <v-icon :color="item.is_active ? 'success' : 'grey'">
            {{ item.is_active ? 'mdi-check-circle' : 'mdi-circle-outline' }}
          </v-icon>
        </template>
        <template #item.blocks_on_limit="{ item }">
          <v-tooltip :text="item.blocks_on_limit ? t('admin.llmUsage.budget.blocksOnLimitTooltip') : t('admin.llmUsage.budget.monitorOnlyTooltip')">
            <template #activator="{ props: tooltipProps }">
              <v-icon v-bind="tooltipProps" :color="item.blocks_on_limit ? 'error' : 'grey'">
                {{ item.blocks_on_limit ? 'mdi-shield-lock' : 'mdi-shield-outline' }}
              </v-icon>
            </template>
          </v-tooltip>
        </template>
        <template #item.status="{ item }">
          <BudgetStatusChip :budget-id="item.id" :status="getBudgetStatusById(item.id)" />
        </template>
        <template #item.actions="{ item }">
          <div class="d-flex justify-end ga-1">
            <v-btn
              icon="mdi-pencil"
              size="small"
              variant="tonal"
              @click="openBudgetDialog(item)"
            />
            <v-btn
              icon="mdi-delete"
              size="small"
              variant="tonal"
              color="error"
              @click="confirmDeleteBudget(item)"
            />
          </div>
        </template>
        <template #no-data>
          <div class="text-center py-8">
            <v-icon size="48" color="grey-lighten-1" class="mb-3">mdi-wallet-outline</v-icon>
            <h3 class="text-h6 mb-2">{{ t('admin.llmUsage.budget.noBudgets') }}</h3>
            <p class="text-body-2 text-medium-emphasis mb-4">{{ t('admin.llmUsage.budget.noBudgetsHint') }}</p>
            <v-btn variant="tonal" color="primary" @click="openBudgetDialog()">
              <v-icon start>mdi-plus</v-icon>
              {{ t('admin.llmUsage.budget.add') }}
            </v-btn>
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- Limit Requests Panel -->
    <LimitRequestsPanel class="mt-4" />

    <!-- Budget Dialog -->
    <v-dialog v-model="budgetDialogOpen" :max-width="DIALOG_SIZES.MD">
      <v-card>
        <v-card-title class="d-flex align-center pa-4 bg-primary">
          <v-icon class="mr-3">{{ editingBudget ? 'mdi-pencil' : 'mdi-plus' }}</v-icon>
          {{ editingBudget ? t('admin.llmUsage.budget.edit') : t('admin.llmUsage.budget.add') }}
        </v-card-title>
        <v-card-text class="pa-6">
          <v-form ref="budgetFormRef" @submit.prevent="saveBudget">
            <v-row>
              <v-col cols="12">
                <v-text-field
                  v-model="budgetForm.name"
                  :label="t('admin.llmUsage.budget.form.name')"
                  :rules="[required]"
                  variant="outlined"
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-select
                  v-model="budgetForm.budget_type"
                  :label="t('admin.llmUsage.budget.form.type')"
                  :items="budgetTypeOptions"
                  :rules="[required]"
                  variant="outlined"
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model.number="budgetForm.monthly_limit_cents"
                  :label="t('admin.llmUsage.budget.form.limit')"
                  type="number"
                  :rules="[required, positiveNumber]"
                  variant="outlined"
                  suffix="Cents"
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model.number="budgetForm.warning_threshold_percent"
                  :label="t('admin.llmUsage.budget.form.warningThreshold')"
                  type="number"
                  :rules="[required, percentRange]"
                  variant="outlined"
                  suffix="%"
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model.number="budgetForm.critical_threshold_percent"
                  :label="t('admin.llmUsage.budget.form.criticalThreshold')"
                  type="number"
                  :rules="[required, percentRange]"
                  variant="outlined"
                  suffix="%"
                />
              </v-col>
              <v-col cols="12">
                <v-combobox
                  v-model="budgetForm.alert_emails"
                  :label="t('admin.llmUsage.budget.form.alertEmails')"
                  variant="outlined"
                  multiple
                  chips
                  closable-chips
                  :hint="t('admin.llmUsage.budget.form.alertEmailsHint')"
                  persistent-hint
                />
              </v-col>
              <v-col cols="12">
                <v-textarea
                  v-model="budgetForm.description"
                  :label="t('admin.llmUsage.budget.form.description')"
                  variant="outlined"
                  rows="2"
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-switch
                  v-model="budgetForm.is_active"
                  :label="t('admin.llmUsage.budget.form.active')"
                  color="success"
                  hide-details
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-switch
                  v-model="budgetForm.blocks_on_limit"
                  :label="t('admin.llmUsage.budget.form.blocksOnLimit')"
                  :hint="t('admin.llmUsage.budget.form.blocksOnLimitHint')"
                  color="error"
                  persistent-hint
                />
              </v-col>
            </v-row>
          </v-form>
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-4">
          <v-btn variant="tonal" @click="budgetDialogOpen = false">
            {{ t('common.cancel') }}
          </v-btn>
          <v-spacer />
          <v-btn variant="tonal" color="primary" :loading="savingBudget" @click="saveBudget">
            <v-icon start>mdi-check</v-icon>
            {{ t('common.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialogOpen" :max-width="DIALOG_SIZES.XS">
      <v-card>
        <v-card-title class="d-flex align-center pa-4 bg-error">
          <v-icon class="mr-3">mdi-delete</v-icon>
          {{ t('admin.llmUsage.budget.deleteTitle') }}
        </v-card-title>
        <v-card-text class="pa-6">
          <v-alert type="error" variant="tonal">
            {{ t('admin.llmUsage.budget.deleteConfirm', { name: selectedBudget?.name }) }}
          </v-alert>
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-4">
          <v-btn variant="tonal" @click="deleteDialogOpen = false">
            {{ t('common.cancel') }}
          </v-btn>
          <v-spacer />
          <v-btn variant="tonal" color="error" :loading="savingBudget" @click="deleteBudget">
            <v-icon start>mdi-delete</v-icon>
            {{ t('common.delete') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar for operation feedback -->
    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="3000"
    >
      {{ snackbar.message }}
      <template #actions>
        <v-btn variant="text" @click="snackbar.show = false">
          {{ t('common.close') }}
        </v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { DIALOG_SIZES } from '@/config/ui'
import { useLLMUsageStore } from '@/stores/llmUsage'
import PageHeader from '@/components/common/PageHeader.vue'
import UsageTrendChart from '@/components/admin/llm-usage/UsageTrendChart.vue'
import ModelDistributionChart from '@/components/admin/llm-usage/ModelDistributionChart.vue'
import BudgetStatusChip from '@/components/admin/llm-usage/BudgetStatusChip.vue'
import LimitRequestsPanel from '@/components/admin/LimitRequestsPanel.vue'
import {
  PERIOD_OPTIONS,
  PROVIDER_LABELS,
  TASK_TYPE_LABELS,
  BUDGET_TYPE_LABELS,
  type LLMBudgetConfig,
  type LLMProvider,
  type LLMTaskType,
  type BudgetType,
  type BudgetStatus,
  type LLMUsageByUser,
} from '@/types/llm-usage'
import { useLogger } from '@/composables/useLogger'
import { useDateFormatter } from '@/composables'

const logger = useLogger('LLMUsageView')
const { formatNumber } = useDateFormatter()
const { t } = useI18n()
const store = useLLMUsageStore()

// State
const isLoading = computed(() => store.isLoading)

// Filters
const selectedPeriod = ref<'24h' | '7d' | '30d' | '90d'>('7d')
const selectedProvider = ref<LLMProvider | null>(null)
const selectedTaskType = ref<LLMTaskType | null>(null)

// Budget dialog
const budgetDialogOpen = ref(false)
const deleteDialogOpen = ref(false)
const editingBudget = ref<LLMBudgetConfig | null>(null)
const selectedBudget = ref<LLMBudgetConfig | null>(null)
const savingBudget = ref(false)
const budgetFormRef = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)

// Budget info panel visibility
const BUDGET_INFO_STORAGE_KEY = 'llm-budget-info-hidden'
const budgetInfoHidden = ref(localStorage.getItem(BUDGET_INFO_STORAGE_KEY) === 'true')

function hideBudgetInfo() {
  budgetInfoHidden.value = true
  localStorage.setItem(BUDGET_INFO_STORAGE_KEY, 'true')
}

function showBudgetInfo() {
  budgetInfoHidden.value = false
  localStorage.removeItem(BUDGET_INFO_STORAGE_KEY)
}

const budgetForm = reactive({
  name: '',
  budget_type: 'GLOBAL' as BudgetType,
  monthly_limit_cents: 10000,
  warning_threshold_percent: 80,
  critical_threshold_percent: 95,
  alert_emails: [] as string[],
  description: '',
  is_active: true,
  blocks_on_limit: false,
})

// Snackbar state
const snackbar = reactive({
  show: false,
  message: '',
  color: 'success' as 'success' | 'error' | 'info',
})

function showSnackbar(message: string, color: 'success' | 'error' | 'info' = 'success') {
  snackbar.message = message
  snackbar.color = color
  snackbar.show = true
}

// Options for selects
const periodOptions = PERIOD_OPTIONS.map((p) => ({
  title: p.label,
  value: p.value,
}))

const providerOptions = computed(() =>
  Object.entries(PROVIDER_LABELS).map(([value, title]) => ({ title, value }))
)

const taskTypeOptions = computed(() =>
  Object.entries(TASK_TYPE_LABELS).map(([value, title]) => ({ title, value }))
)

const budgetTypeOptions = computed(() =>
  Object.entries(BUDGET_TYPE_LABELS).map(([value, title]) => ({ title, value }))
)

// Table headers
const userHeaders = computed(() => [
  { title: t('admin.llmUsage.tables.headers.user'), key: 'user_name' },
  { title: t('admin.llmUsage.tables.headers.requests'), key: 'request_count', align: 'end' as const },
  { title: t('admin.llmUsage.tables.headers.tokens'), key: 'total_tokens', align: 'end' as const },
  { title: t('admin.llmUsage.tables.headers.cost'), key: 'cost_cents', align: 'end' as const },
  { title: t('admin.llmUsage.tables.headers.models'), key: 'models_used' },
  { title: 'API', key: 'has_credentials', align: 'center' as const },
])

const taskTypeHeaders = computed(() => [
  { title: t('admin.llmUsage.tables.headers.taskType'), key: 'task_type' },
  { title: t('admin.llmUsage.tables.headers.requests'), key: 'request_count', align: 'end' as const },
  { title: t('admin.llmUsage.tables.headers.tokens'), key: 'total_tokens', align: 'end' as const },
  { title: t('admin.llmUsage.tables.headers.cost'), key: 'cost_cents', align: 'end' as const },
  { title: t('admin.llmUsage.tables.headers.avgDuration'), key: 'avg_duration_ms', align: 'end' as const },
])

const categoryHeaders = computed(() => [
  { title: t('admin.llmUsage.tables.headers.category'), key: 'category_name' },
  { title: t('admin.llmUsage.tables.headers.requests'), key: 'request_count', align: 'end' as const },
  { title: t('admin.llmUsage.tables.headers.tokens'), key: 'total_tokens', align: 'end' as const },
  { title: t('admin.llmUsage.tables.headers.cost'), key: 'cost_cents', align: 'end' as const },
])

const topConsumersHeaders = computed(() => [
  { title: t('admin.llmUsage.tables.headers.taskName'), key: 'task_name' },
  { title: t('admin.llmUsage.tables.headers.taskType'), key: 'task_type' },
  { title: t('admin.llmUsage.tables.headers.requests'), key: 'request_count', align: 'end' as const },
  { title: t('admin.llmUsage.tables.headers.tokens'), key: 'total_tokens', align: 'end' as const },
  { title: t('admin.llmUsage.tables.headers.cost'), key: 'cost_cents', align: 'end' as const },
])

const budgetHeaders = computed(() => [
  { title: t('admin.llmUsage.budget.headers.name'), key: 'name' },
  { title: t('admin.llmUsage.budget.headers.type'), key: 'budget_type' },
  { title: t('admin.llmUsage.budget.headers.limit'), key: 'monthly_limit_cents', align: 'end' as const },
  { title: t('admin.llmUsage.budget.headers.status'), key: 'status', align: 'center' as const },
  { title: t('admin.llmUsage.budget.headers.active'), key: 'is_active', align: 'center' as const },
  { title: t('admin.llmUsage.budget.headers.blocking'), key: 'blocks_on_limit', align: 'center' as const },
  { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' as const },
])

// Validation rules
const required = (v: unknown) => !!v || t('validation.required')
const positiveNumber = (v: number) => v > 0 || t('validation.positiveNumber')
const percentRange = (v: number) => (v >= 0 && v <= 100) || t('validation.percentRange')

// Formatting helpers (formatNumber from useDateFormatter composable)

function formatTokens(tokens: number): string {
  if (tokens >= 1000000) {
    return `${(tokens / 1000000).toFixed(1)}M`
  }
  if (tokens >= 1000) {
    return `${(tokens / 1000).toFixed(1)}K`
  }
  return tokens.toString()
}

function formatCost(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`
}

function getTaskTypeLabel(taskType: LLMTaskType): string {
  return TASK_TYPE_LABELS[taskType] || taskType
}

function getBudgetTypeLabel(budgetType: BudgetType): string {
  return BUDGET_TYPE_LABELS[budgetType] || budgetType
}

function getBudgetTypeColor(budgetType: BudgetType): string {
  const colors: Record<BudgetType, string> = {
    GLOBAL: 'primary',
    CATEGORY: 'info',
    TASK_TYPE: 'success',
    MODEL: 'warning',
    USER: 'secondary',
  }
  return colors[budgetType] || 'grey'
}

function getBudgetStatusById(budgetId: string): BudgetStatus | undefined {
  return store.budgetStatus?.budgets.find((b) => b.budget_id === budgetId)
}

function getUserInitials(item: LLMUsageByUser): string {
  if (item.user_name) {
    const parts = item.user_name.split(' ')
    return parts.length >= 2
      ? (parts[0][0] + parts[1][0]).toUpperCase()
      : item.user_name.substring(0, 2).toUpperCase()
  }
  return item.user_id ? 'U' : 'S'
}

// Actions
async function onFilterChange() {
  store.setPeriod(selectedPeriod.value)
  store.setProvider(selectedProvider.value)
  store.setTaskType(selectedTaskType.value)
  await store.loadAnalytics()
}

function clearFilters() {
  selectedProvider.value = null
  selectedTaskType.value = null
  store.clearFilters()
  store.loadAnalytics()
}

async function refresh() {
  await store.refresh()
}

async function exportData(format: 'csv' | 'json') {
  const blob = await store.exportData(format)
  if (blob) {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `llm-usage-${selectedPeriod.value}.${format}`
    a.click()
    URL.revokeObjectURL(url)
  }
}

function openBudgetDialog(budget?: LLMBudgetConfig) {
  editingBudget.value = budget || null
  if (budget) {
    Object.assign(budgetForm, {
      name: budget.name,
      budget_type: budget.budget_type,
      monthly_limit_cents: budget.monthly_limit_cents,
      warning_threshold_percent: budget.warning_threshold_percent,
      critical_threshold_percent: budget.critical_threshold_percent,
      alert_emails: budget.alert_emails,
      description: budget.description || '',
      is_active: budget.is_active,
      blocks_on_limit: budget.blocks_on_limit ?? false,
    })
  } else {
    Object.assign(budgetForm, {
      name: '',
      budget_type: 'GLOBAL',
      monthly_limit_cents: 10000,
      warning_threshold_percent: 80,
      critical_threshold_percent: 95,
      alert_emails: [],
      description: '',
      is_active: true,
      blocks_on_limit: false,
    })
  }
  budgetDialogOpen.value = true
}

async function saveBudget() {
  const valid = await budgetFormRef.value?.validate()
  if (!valid?.valid) return

  savingBudget.value = true
  try {
    if (editingBudget.value) {
      await store.saveBudget(editingBudget.value.id, budgetForm)
      showSnackbar(t('admin.llmUsage.budget.updateSuccess'))
    } else {
      await store.addBudget(budgetForm)
      showSnackbar(t('admin.llmUsage.budget.createSuccess'))
    }
    budgetDialogOpen.value = false
    await store.loadBudgetStatus()
  } catch (error) {
    logger.error('Failed to save budget:', error)
    showSnackbar(t('admin.llmUsage.budget.saveError'), 'error')
  } finally {
    savingBudget.value = false
  }
}

function confirmDeleteBudget(budget: LLMBudgetConfig) {
  selectedBudget.value = budget
  deleteDialogOpen.value = true
}

async function deleteBudget() {
  if (!selectedBudget.value) return

  savingBudget.value = true
  try {
    await store.removeBudget(selectedBudget.value.id)
    deleteDialogOpen.value = false
    showSnackbar(t('admin.llmUsage.budget.deleteSuccess'))
    await store.loadBudgetStatus()
  } catch (error) {
    logger.error('Failed to delete budget:', error)
    showSnackbar(t('admin.llmUsage.budget.deleteError'), 'error')
  } finally {
    savingBudget.value = false
  }
}

onMounted(async () => {
  await store.initialize()
  await store.loadBudgets()
})
</script>
