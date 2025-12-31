/**
 * LLM Usage Store
 *
 * Manages LLM usage analytics, cost projections, and budget configurations.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getLLMAnalytics,
  getLLMCostProjection,
  exportLLMUsageData,
  getLLMBudgets,
  getLLMBudgetStatus,
  getLLMBudgetAlerts,
  createLLMBudget,
  updateLLMBudget,
  deleteLLMBudget,
  triggerLLMBudgetCheck,
} from '@/services/api/admin'
import type {
  LLMUsageAnalytics,
  LLMCostProjection,
  LLMBudgetConfig,
  BudgetStatusList,
  BudgetAlert,
  LLMUsageQueryParams,
  LLMBudgetCreateRequest,
  LLMBudgetUpdateRequest,
  LLMProvider,
  LLMTaskType,
} from '@/types/llm-usage'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('LLMUsageStore')

export const useLLMUsageStore = defineStore('llm-usage', () => {
  // State
  const analytics = ref<LLMUsageAnalytics | null>(null)
  const costProjection = ref<LLMCostProjection | null>(null)
  const budgetConfigs = ref<LLMBudgetConfig[]>([])
  const budgetStatus = ref<BudgetStatusList | null>(null)
  const budgetAlerts = ref<BudgetAlert[]>([])

  // Filters
  const selectedPeriod = ref<'24h' | '7d' | '30d' | '90d'>('7d')
  const selectedProvider = ref<LLMProvider | null>(null)
  const selectedModel = ref<string | null>(null)
  const selectedTaskType = ref<LLMTaskType | null>(null)
  const selectedCategoryId = ref<string | null>(null)

  // UI State
  const isLoading = ref(false)
  const isLoadingBudgets = ref(false)
  const error = ref<string | null>(null)
  const lastUpdated = ref<Date | null>(null)

  // Computed
  const hasWarnings = computed(() => budgetStatus.value?.any_warning ?? false)
  const hasCritical = computed(() => budgetStatus.value?.any_critical ?? false)

  const totalCostCents = computed(
    () => analytics.value?.summary.total_cost_cents ?? 0
  )

  const totalTokens = computed(
    () => analytics.value?.summary.total_tokens ?? 0
  )

  const totalRequests = computed(
    () => analytics.value?.summary.total_requests ?? 0
  )

  const errorRate = computed(
    () => analytics.value?.summary.error_rate ?? 0
  )

  const projectedCostCents = computed(
    () => costProjection.value?.projected_month_cost_cents ?? 0
  )

  const currentFilters = computed<LLMUsageQueryParams>(() => ({
    period: selectedPeriod.value,
    provider: selectedProvider.value ?? undefined,
    model: selectedModel.value ?? undefined,
    task_type: selectedTaskType.value ?? undefined,
    category_id: selectedCategoryId.value ?? undefined,
  }))

  const activeBudgets = computed(() =>
    budgetConfigs.value.filter((b) => b.is_active)
  )

  // Actions

  /**
   * Load analytics data with current filters
   */
  async function loadAnalytics(): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      const response = await getLLMAnalytics(currentFilters.value)
      analytics.value = response.data
      lastUpdated.value = new Date()
    } catch (e) {
      logger.error('Failed to load LLM analytics:', e)
      error.value = 'Fehler beim Laden der Analytics'
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Load cost projection for current month
   */
  async function loadCostProjection(): Promise<void> {
    try {
      const response = await getLLMCostProjection()
      costProjection.value = response.data
    } catch (e) {
      logger.error('Failed to load cost projection:', e)
    }
  }

  /**
   * Load all budget configurations
   */
  async function loadBudgets(activeOnly: boolean = false): Promise<void> {
    isLoadingBudgets.value = true

    try {
      const response = await getLLMBudgets({ active_only: activeOnly })
      budgetConfigs.value = response.data
    } catch (e) {
      logger.error('Failed to load budgets:', e)
      error.value = 'Fehler beim Laden der Budgets'
    } finally {
      isLoadingBudgets.value = false
    }
  }

  /**
   * Load budget status for all active budgets
   */
  async function loadBudgetStatus(): Promise<void> {
    try {
      const response = await getLLMBudgetStatus()
      budgetStatus.value = response.data
    } catch (e) {
      logger.error('Failed to load budget status:', e)
    }
  }

  /**
   * Load budget alert history
   */
  async function loadBudgetAlerts(
    budgetId?: string,
    limit: number = 50
  ): Promise<void> {
    try {
      const response = await getLLMBudgetAlerts({ budget_id: budgetId, limit })
      budgetAlerts.value = response.data
    } catch (e) {
      logger.error('Failed to load budget alerts:', e)
    }
  }

  /**
   * Create a new budget configuration
   */
  async function addBudget(data: LLMBudgetCreateRequest): Promise<LLMBudgetConfig | null> {
    try {
      const response = await createLLMBudget(data)
      budgetConfigs.value.push(response.data)
      return response.data
    } catch (e) {
      logger.error('Failed to create budget:', e)
      error.value = 'Fehler beim Erstellen des Budgets'
      return null
    }
  }

  /**
   * Update an existing budget configuration
   */
  async function saveBudget(
    id: string,
    data: LLMBudgetUpdateRequest
  ): Promise<LLMBudgetConfig | null> {
    try {
      const response = await updateLLMBudget(id, data)
      const index = budgetConfigs.value.findIndex((b) => b.id === id)
      if (index !== -1) {
        budgetConfigs.value[index] = response.data
      }
      return response.data
    } catch (e) {
      logger.error('Failed to update budget:', e)
      error.value = 'Fehler beim Speichern des Budgets'
      return null
    }
  }

  /**
   * Delete a budget configuration
   */
  async function removeBudget(id: string): Promise<boolean> {
    try {
      await deleteLLMBudget(id)
      budgetConfigs.value = budgetConfigs.value.filter((b) => b.id !== id)
      return true
    } catch (e) {
      logger.error('Failed to delete budget:', e)
      error.value = 'Fehler beim Löschen des Budgets'
      return false
    }
  }

  /**
   * Manually trigger budget check
   */
  async function checkBudgets(): Promise<{ alerts_triggered: number } | null> {
    try {
      const response = await triggerLLMBudgetCheck()
      await loadBudgetStatus()
      return response.data
    } catch (e) {
      logger.error('Failed to trigger budget check:', e)
      return null
    }
  }

  /**
   * Export usage data
   */
  async function exportData(format: 'csv' | 'json' = 'csv'): Promise<Blob | null> {
    try {
      const response = await exportLLMUsageData({ period: selectedPeriod.value, format })
      return response.data
    } catch (e) {
      logger.error('Failed to export data:', e)
      error.value = 'Fehler beim Exportieren der Daten'
      return null
    }
  }

  /**
   * Set filter: period
   */
  function setPeriod(period: '24h' | '7d' | '30d' | '90d'): void {
    selectedPeriod.value = period
  }

  /**
   * Set filter: provider
   */
  function setProvider(provider: LLMProvider | null): void {
    selectedProvider.value = provider
  }

  /**
   * Set filter: model
   */
  function setModel(model: string | null): void {
    selectedModel.value = model
  }

  /**
   * Set filter: task type
   */
  function setTaskType(taskType: LLMTaskType | null): void {
    selectedTaskType.value = taskType
  }

  /**
   * Set filter: category
   */
  function setCategoryId(categoryId: string | null): void {
    selectedCategoryId.value = categoryId
  }

  /**
   * Clear all filters
   */
  function clearFilters(): void {
    selectedProvider.value = null
    selectedModel.value = null
    selectedTaskType.value = null
    selectedCategoryId.value = null
  }

  /**
   * Refresh all data
   */
  async function refresh(): Promise<void> {
    await Promise.all([
      loadAnalytics(),
      loadCostProjection(),
      loadBudgetStatus(),
    ])
  }

  /**
   * Initialize store (load all initial data)
   */
  async function initialize(): Promise<void> {
    await Promise.all([
      loadAnalytics(),
      loadCostProjection(),
      loadBudgets(true),
      loadBudgetStatus(),
    ])
  }

  return {
    // State
    analytics,
    costProjection,
    budgetConfigs,
    budgetStatus,
    budgetAlerts,

    // Filters
    selectedPeriod,
    selectedProvider,
    selectedModel,
    selectedTaskType,
    selectedCategoryId,

    // UI State
    isLoading,
    isLoadingBudgets,
    error,
    lastUpdated,

    // Computed
    hasWarnings,
    hasCritical,
    totalCostCents,
    totalTokens,
    totalRequests,
    errorRate,
    projectedCostCents,
    currentFilters,
    activeBudgets,

    // Actions
    loadAnalytics,
    loadCostProjection,
    loadBudgets,
    loadBudgetStatus,
    loadBudgetAlerts,
    addBudget,
    saveBudget,
    removeBudget,
    checkBudgets,
    exportData,
    setPeriod,
    setProvider,
    setModel,
    setTaskType,
    setCategoryId,
    clearFilters,
    refresh,
    initialize,
  }
})
