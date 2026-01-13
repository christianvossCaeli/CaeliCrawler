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
        <v-btn
          variant="tonal"
          color="warning"
          :loading="recalculating"
          @click="openRecalculateDialog"
        >
          <v-icon start>mdi-calculator-variant</v-icon>
          {{ t('admin.llmUsage.recalculate.button') }}
        </v-btn>
      </template>
    </PageHeader>

    <!-- Consolidated Status Banner -->
    <v-alert
      v-if="store.error"
      type="error"
      variant="tonal"
      density="compact"
      class="mb-4"
      closable
      @click:close="store.error = null"
    >
      <div class="d-flex align-center justify-space-between">
        <span>{{ store.error }}</span>
        <v-btn variant="text" size="small" @click="refresh">
          <v-icon start size="small">mdi-refresh</v-icon>
          {{ t('common.retry') }}
        </v-btn>
      </div>
    </v-alert>

    <!-- Budget Warning Banner (compact) -->
    <v-banner
      v-if="store.hasCritical || store.hasWarnings"
      :color="store.hasCritical ? 'error' : 'warning'"
      density="compact"
      class="mb-4 rounded"
      lines="one"
    >
      <template #prepend>
        <v-icon>{{ store.hasCritical ? 'mdi-alert-circle' : 'mdi-alert' }}</v-icon>
      </template>
      <span class="text-body-2">
        {{ store.hasCritical ? t('admin.llmUsage.budget.criticalWarning') : t('admin.llmUsage.budget.warningAlert') }}
      </span>
      <template #actions>
        <v-btn variant="text" size="small" @click="activeTab = 'budgets'">
          {{ t('admin.llmUsage.budget.viewBudgets') }}
        </v-btn>
      </template>
    </v-banner>

    <!-- Summary Cards -->
    <v-row class="mb-4">
      <v-col cols="6" sm="6" md="3">
        <v-card variant="outlined">
          <v-card-text class="text-center pa-3">
            <v-icon size="28" color="primary" class="mb-1">mdi-counter</v-icon>
            <div class="text-h5 font-weight-bold">{{ formatNumber(store.totalRequests) }}</div>
            <div class="text-caption text-medium-emphasis">
              {{ t('admin.llmUsage.stats.requests') }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="6" md="3">
        <v-card variant="outlined">
          <v-card-text class="text-center pa-3">
            <v-icon size="28" color="info" class="mb-1">mdi-text-box-multiple</v-icon>
            <div class="text-h5 font-weight-bold">{{ formatTokens(store.totalTokens) }}</div>
            <div class="text-caption text-medium-emphasis">
              {{ t('admin.llmUsage.stats.tokens') }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="6" md="3">
        <v-card variant="outlined" :class="{ 'border-error': store.hasCritical }">
          <v-card-text class="text-center pa-3">
            <v-icon size="28" color="success" class="mb-1">mdi-currency-usd</v-icon>
            <div class="text-h5 font-weight-bold">{{ formatCurrency(store.totalCostCents) }}</div>
            <div class="text-caption text-medium-emphasis">
              {{ t('admin.llmUsage.stats.cost') }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="6" md="3">
        <v-card variant="outlined">
          <v-card-text class="text-center pa-3">
            <v-icon size="28" color="warning" class="mb-1">mdi-chart-line</v-icon>
            <div class="text-h5 font-weight-bold">{{ formatCurrency(store.projectedCostCents) }}</div>
            <div class="text-caption text-medium-emphasis">
              {{ t('admin.llmUsage.stats.projected') }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Tabs -->
    <v-card>
      <v-tabs v-model="activeTab" color="primary" grow>
        <v-tab value="budgets">
          <v-icon start>mdi-wallet</v-icon>
          {{ t('admin.llmUsage.tabs.budgets') }}
          <v-badge
            v-if="store.hasCritical || store.hasWarnings"
            :color="store.hasCritical ? 'error' : 'warning'"
            dot
            inline
            class="ml-2"
          />
        </v-tab>
        <v-tab value="analytics">
          <v-icon start>mdi-chart-bar</v-icon>
          {{ t('admin.llmUsage.tabs.analytics') }}
        </v-tab>
      </v-tabs>

      <v-divider />

      <v-tabs-window v-model="activeTab">
        <!-- ==================== BUDGETS TAB ==================== -->
        <v-tabs-window-item value="budgets">
          <v-card-text>
            <!-- Budget Info Box (compact) -->
            <v-alert
              type="info"
              variant="tonal"
              density="compact"
              class="mb-4"
            >
              <div class="d-flex flex-wrap align-center ga-2">
                <span class="text-body-2">{{ t('admin.llmUsage.budget.infoCompact') }}</span>
                <v-chip-group>
                  <v-tooltip v-for="type in budgetTypeInfo" :key="type.value" :text="type.description" location="top">
                    <template #activator="{ props: tooltipProps }">
                      <v-chip v-bind="tooltipProps" size="x-small" :color="type.color" label>
                        {{ type.label }}
                      </v-chip>
                    </template>
                  </v-tooltip>
                </v-chip-group>
              </div>
            </v-alert>

            <!-- Budget Table -->
            <div class="d-flex align-center justify-space-between mb-3">
              <h3 class="text-h6">{{ t('admin.llmUsage.budget.title') }}</h3>
              <v-btn variant="tonal" color="primary" size="small" @click="openBudgetDialog()">
                <v-icon start>mdi-plus</v-icon>
                {{ t('admin.llmUsage.budget.add') }}
              </v-btn>
            </div>

            <v-data-table
              :headers="budgetHeaders"
              :items="store.budgetConfigs"
              :loading="store.isLoadingBudgets"
              density="compact"
              class="mb-6"
            >
              <template #item.budget_type="{ item }">
                <v-chip size="small" :color="getBudgetTypeColor(item.budget_type)" label>
                  {{ getBudgetTypeLabel(item.budget_type) }}
                </v-chip>
              </template>
              <template #item.monthly_limit_cents="{ item }">
                {{ formatCurrency(item.monthly_limit_cents) }}
              </template>
              <template #item.is_active="{ item }">
                <v-icon :color="item.is_active ? 'success' : 'grey'" size="small">
                  {{ item.is_active ? 'mdi-check-circle' : 'mdi-circle-outline' }}
                </v-icon>
              </template>
              <template #item.blocks_on_limit="{ item }">
                <v-tooltip :text="item.blocks_on_limit ? t('admin.llmUsage.budget.blocksOnLimitTooltip') : t('admin.llmUsage.budget.monitorOnlyTooltip')">
                  <template #activator="{ props: tooltipProps }">
                    <v-icon v-bind="tooltipProps" :color="item.blocks_on_limit ? 'error' : 'grey'" size="small">
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
                  <v-btn icon="mdi-pencil" size="x-small" variant="text" @click="openBudgetDialog(item)" />
                  <v-btn icon="mdi-delete" size="x-small" variant="text" color="error" @click="confirmDeleteBudget(item)" />
                </div>
              </template>
              <template #no-data>
                <div class="text-center py-6">
                  <v-icon size="40" color="grey-lighten-1" class="mb-2">mdi-wallet-outline</v-icon>
                  <p class="text-body-2 text-medium-emphasis mb-3">{{ t('admin.llmUsage.budget.noBudgets') }}</p>
                  <v-btn variant="tonal" color="primary" size="small" @click="openBudgetDialog()">
                    <v-icon start>mdi-plus</v-icon>
                    {{ t('admin.llmUsage.budget.add') }}
                  </v-btn>
                </div>
              </template>
            </v-data-table>

            <!-- Limit Requests Section -->
            <v-divider class="mb-4" />
            <LimitRequestsPanel />
          </v-card-text>
        </v-tabs-window-item>

        <!-- ==================== ANALYTICS TAB ==================== -->
        <v-tabs-window-item value="analytics">
          <v-card-text>
            <!-- Analytics Info Box -->
            <v-alert
              type="info"
              variant="tonal"
              density="compact"
              class="mb-4"
            >
              <span class="text-body-2">{{ t('admin.llmUsage.analytics.infoCompact') }}</span>
            </v-alert>

            <!-- Filters -->
            <v-row align="center" class="mb-4">
              <v-col cols="12" sm="4" md="3">
                <v-select
                  v-model="selectedPeriod"
                  :label="t('admin.llmUsage.filters.period')"
                  :items="periodOptions"
                  density="compact"
                  hide-details
                  @update:model-value="onFilterChange"
                />
              </v-col>
              <v-col cols="12" sm="4" md="3">
                <v-select
                  v-model="selectedProvider"
                  :label="t('admin.llmUsage.filters.provider')"
                  :items="providerOptions"
                  density="compact"
                  clearable
                  hide-details
                  @update:model-value="onFilterChange"
                />
              </v-col>
              <v-col cols="12" sm="4" md="3">
                <v-select
                  v-model="selectedTaskType"
                  :label="t('admin.llmUsage.filters.taskType')"
                  :items="taskTypeOptions"
                  density="compact"
                  clearable
                  hide-details
                  @update:model-value="onFilterChange"
                />
              </v-col>
              <v-col cols="12" sm="12" md="3">
                <v-btn variant="text" color="primary" size="small" @click="clearFilters">
                  <v-icon start>mdi-filter-off</v-icon>
                  {{ t('admin.llmUsage.filters.clear') }}
                </v-btn>
              </v-col>
            </v-row>

            <!-- Charts Row -->
            <v-row class="mb-4">
              <v-col cols="12" md="8">
                <v-card variant="outlined">
                  <v-card-title class="text-subtitle-1 py-2">
                    <v-icon start size="small">mdi-chart-timeline-variant</v-icon>
                    {{ t('admin.llmUsage.charts.trend') }}
                  </v-card-title>
                  <v-divider />
                  <v-card-text class="pa-2">
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
                <v-card variant="outlined">
                  <v-card-title class="text-subtitle-1 py-2">
                    <v-icon start size="small">mdi-chart-pie</v-icon>
                    {{ t('admin.llmUsage.charts.byModel') }}
                  </v-card-title>
                  <v-divider />
                  <v-card-text class="pa-2">
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
            <v-card variant="outlined" class="mb-4">
              <v-card-title class="text-subtitle-1 py-2">
                <v-icon start size="small">mdi-account-group</v-icon>
                {{ t('admin.llmUsage.tables.byUser') }}
              </v-card-title>
              <v-divider />
              <v-data-table
                :headers="userHeaders"
                :items="store.analytics?.by_user || []"
                :items-per-page="5"
                density="compact"
              >
                <template #item.user_name="{ item }">
                  <div class="d-flex align-center">
                    <v-avatar size="24" color="primary" class="mr-2">
                      <span class="text-caption">{{ getUserInitials(item) }}</span>
                    </v-avatar>
                    <div>
                      <span class="font-weight-medium">
                        {{ item.user_name || t('admin.llmUsage.systemUser') }}
                      </span>
                    </div>
                  </div>
                </template>
                <template #item.total_tokens="{ item }">
                  {{ formatTokens(item.total_tokens) }}
                </template>
                <template #item.cost_cents="{ item }">
                  <span class="font-weight-medium">{{ formatCurrency(item.cost_cents) }}</span>
                </template>
                <template #item.models_used="{ item }">
                  <div class="d-flex flex-wrap ga-1">
                    <v-chip
                      v-for="model in item.models_used.slice(0, 2)"
                      :key="model"
                      size="x-small"
                      label
                    >
                      {{ model }}
                    </v-chip>
                    <v-chip v-if="item.models_used.length > 2" size="x-small" variant="text">
                      +{{ item.models_used.length - 2 }}
                    </v-chip>
                  </div>
                </template>
                <template #item.has_credentials="{ item }">
                  <v-icon :color="item.has_credentials ? 'success' : 'warning'" size="small">
                    {{ item.has_credentials ? 'mdi-key-check' : 'mdi-key-remove' }}
                  </v-icon>
                </template>
                <template #no-data>
                  <div class="text-center py-4 text-medium-emphasis">
                    {{ t('admin.llmUsage.noData') }}
                  </div>
                </template>
              </v-data-table>
            </v-card>

            <!-- Task Type Table -->
            <v-card variant="outlined" class="mb-4">
              <v-card-title class="text-subtitle-1 py-2">
                <v-icon start size="small">mdi-format-list-bulleted-type</v-icon>
                {{ t('admin.llmUsage.tables.byTaskType') }}
              </v-card-title>
              <v-divider />
              <v-data-table
                :headers="taskTypeHeaders"
                :items="store.analytics?.by_task || []"
                :items-per-page="5"
                density="compact"
              >
                <template #item.task_type="{ item }">
                  <v-chip size="x-small" label>{{ getTaskTypeLabel(item.task_type) }}</v-chip>
                </template>
                <template #item.total_tokens="{ item }">
                  {{ formatTokens(item.total_tokens) }}
                </template>
                <template #item.cost_cents="{ item }">
                  {{ formatCurrency(item.cost_cents) }}
                </template>
                <template #item.avg_duration_ms="{ item }">
                  {{ item.avg_duration_ms?.toFixed(0) || '-' }} ms
                </template>
                <template #no-data>
                  <div class="text-center py-4 text-medium-emphasis">
                    {{ t('admin.llmUsage.noData') }}
                  </div>
                </template>
              </v-data-table>
            </v-card>

            <!-- Top Consumers -->
            <v-card variant="outlined">
              <v-card-title class="text-subtitle-1 py-2">
                <v-icon start size="small">mdi-podium</v-icon>
                {{ t('admin.llmUsage.tables.topConsumers') }}
              </v-card-title>
              <v-divider />
              <v-data-table
                :headers="topConsumersHeaders"
                :items="store.analytics?.top_consumers || []"
                :items-per-page="5"
                density="compact"
              >
                <template #item.task_type="{ item }">
                  <v-chip size="x-small" label>{{ getTaskTypeLabel(item.task_type) }}</v-chip>
                </template>
                <template #item.total_tokens="{ item }">
                  {{ formatTokens(item.total_tokens) }}
                </template>
                <template #item.cost_cents="{ item }">
                  {{ formatCurrency(item.cost_cents) }}
                </template>
                <template #no-data>
                  <div class="text-center py-4 text-medium-emphasis">
                    {{ t('admin.llmUsage.noData') }}
                  </div>
                </template>
              </v-data-table>
            </v-card>
          </v-card-text>
        </v-tabs-window-item>
      </v-tabs-window>
    </v-card>

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
                >
                  <template #item="{ item, props: itemProps }">
                    <v-list-item v-bind="itemProps">
                      <template #prepend>
                        <v-chip size="x-small" :color="getBudgetTypeColor(item.value as BudgetType)" label class="mr-2">
                          {{ item.value }}
                        </v-chip>
                      </template>
                    </v-list-item>
                  </template>
                </v-select>
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

    <!-- Recalculate Costs Dialog -->
    <v-dialog v-model="recalculateDialogOpen" :max-width="DIALOG_SIZES.SM">
      <v-card>
        <v-card-title class="d-flex align-center pa-4 bg-warning">
          <v-icon class="mr-3">mdi-calculator-variant</v-icon>
          {{ t('admin.llmUsage.recalculate.title') }}
        </v-card-title>
        <v-card-text class="pa-6">
          <v-alert type="info" variant="tonal" class="mb-4">
            {{ t('admin.llmUsage.recalculate.description') }}
          </v-alert>

          <v-select
            v-model="recalculateForm.period"
            :label="t('admin.llmUsage.recalculate.period')"
            :items="recalculatePeriodOptions"
            variant="outlined"
            class="mb-4"
          />

          <v-switch
            v-model="recalculateForm.onlyZeroCosts"
            :label="t('admin.llmUsage.recalculate.onlyZeroCosts')"
            :hint="t('admin.llmUsage.recalculate.onlyZeroCostsHint')"
            color="primary"
            persistent-hint
            class="mb-4"
          />

          <!-- Dry Run Results -->
          <v-alert v-if="recalculateResult" type="success" variant="tonal" class="mt-4">
            <div class="text-subtitle-2 mb-2">{{ t('admin.llmUsage.recalculate.results') }}</div>
            <div class="text-body-2">
              <div>{{ t('admin.llmUsage.recalculate.totalRecords') }}: {{ recalculateResult.total_records }}</div>
              <div>{{ t('admin.llmUsage.recalculate.updatedRecords') }}: {{ recalculateResult.updated_records }}</div>
              <div>
                {{ t('admin.llmUsage.recalculate.costBefore') }}: {{ formatCurrency(recalculateResult.total_cost_before_cents) }}
                → {{ t('admin.llmUsage.recalculate.costAfter') }}: {{ formatCurrency(recalculateResult.total_cost_after_cents) }}
              </div>
            </div>
          </v-alert>
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-4">
          <v-btn variant="tonal" @click="recalculateDialogOpen = false">
            {{ t('common.cancel') }}
          </v-btn>
          <v-spacer />
          <v-btn
            variant="tonal"
            color="info"
            :loading="recalculating"
            @click="executeRecalculate(true)"
          >
            <v-icon start>mdi-eye</v-icon>
            {{ t('admin.llmUsage.recalculate.preview') }}
          </v-btn>
          <v-btn
            variant="tonal"
            color="warning"
            :loading="recalculating"
            @click="executeRecalculate(false)"
          >
            <v-icon start>mdi-calculator-variant</v-icon>
            {{ t('admin.llmUsage.recalculate.execute') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
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
import { formatCurrency, formatTokens } from '@/utils/llmFormatting'
import { useLogger } from '@/composables/useLogger'
import { useDateFormatter } from '@/composables'
import { recalculateLLMCosts, type RecalculateCostsResponse } from '@/services/api/admin'

const logger = useLogger('LLMUsageView')
const { formatNumber } = useDateFormatter()
const { t } = useI18n()
const store = useLLMUsageStore()

// State
const isLoading = computed(() => store.isLoading)
const activeTab = ref<'budgets' | 'analytics'>('budgets')

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

// Recalculate costs dialog
const recalculateDialogOpen = ref(false)
const recalculating = ref(false)
const recalculateResult = ref<RecalculateCostsResponse | null>(null)
const recalculateForm = reactive({
  period: 'all' as '24h' | '7d' | '30d' | '90d' | 'all',
  onlyZeroCosts: true,
})
const recalculatePeriodOptions = [
  { title: 'Alle', value: 'all' },
  { title: 'Letzte 24 Stunden', value: '24h' },
  { title: 'Letzte 7 Tage', value: '7d' },
  { title: 'Letzte 30 Tage', value: '30d' },
  { title: 'Letzte 90 Tage', value: '90d' },
]

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

// Budget type info for compact display
const budgetTypeInfo = computed(() => [
  { value: 'GLOBAL', label: 'GLOBAL', color: 'primary', description: t('admin.llmUsage.budget.typeDescriptions.global') },
  { value: 'USER', label: 'USER', color: 'secondary', description: t('admin.llmUsage.budget.typeDescriptions.user') },
  { value: 'CATEGORY', label: 'CATEGORY', color: 'info', description: t('admin.llmUsage.budget.typeDescriptions.category') },
  { value: 'TASK_TYPE', label: 'TASK_TYPE', color: 'success', description: t('admin.llmUsage.budget.typeDescriptions.taskType') },
  { value: 'MODEL', label: 'MODEL', color: 'warning', description: t('admin.llmUsage.budget.typeDescriptions.model') },
])

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

// Formatting helpers
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
  // Sync period to store before export
  store.setPeriod(selectedPeriod.value)

  const blob = await store.exportData(format)
  if (blob) {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `llm-usage-${selectedPeriod.value}.${format}`
    a.style.display = 'none'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    showSnackbar(t('common.csvExported'), 'success')
  } else {
    showSnackbar(t('common.exportFailed'), 'error')
  }
}

function openRecalculateDialog() {
  recalculateResult.value = null
  recalculateDialogOpen.value = true
}

async function executeRecalculate(dryRun: boolean) {
  recalculating.value = true
  try {
    const response = await recalculateLLMCosts({
      only_zero_costs: recalculateForm.onlyZeroCosts,
      period: recalculateForm.period,
      dry_run: dryRun,
    })
    recalculateResult.value = response.data

    if (!dryRun) {
      showSnackbar(
        t('admin.llmUsage.recalculate.success', { count: response.data.updated_records }),
        'success'
      )
      recalculateDialogOpen.value = false
      // Refresh analytics to show updated costs
      await store.refresh()
    }
  } catch (error) {
    logger.error('Failed to recalculate costs:', error)
    showSnackbar(t('admin.llmUsage.recalculate.error'), 'error')
  } finally {
    recalculating.value = false
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

<style scoped>
.border-error {
  border-color: rgb(var(--v-theme-error)) !important;
}
</style>
