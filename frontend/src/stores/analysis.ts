/**
 * Analysis Store
 *
 * Manages analysis templates, overview, and reports for the Entity-Facet system.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { analysisApi } from '@/services/api'
import type { AnalysisTemplate, AnalysisOverviewItem, EntityReport } from './types/entity'
import { getErrorMessage } from './types/entity'

// ============================================================================
// Store Definition
// ============================================================================

export const useAnalysisStore = defineStore('analysis', () => {
  // ========================================
  // State
  // ========================================

  // Analysis Templates
  const analysisTemplates = ref<AnalysisTemplate[]>([])
  const analysisTemplatesLoading = ref(false)
  const selectedTemplate = ref<AnalysisTemplate | null>(null)

  // Analysis Overview
  const analysisOverview = ref<AnalysisOverviewItem[]>([])
  const analysisOverviewLoading = ref(false)

  // Entity Report
  const entityReport = ref<EntityReport | null>(null)
  const entityReportLoading = ref(false)

  // Error handling
  const error = ref<string | null>(null)

  // ========================================
  // Analysis Template Actions
  // ========================================

  async function fetchAnalysisTemplates(params?: Record<string, unknown>) {
    analysisTemplatesLoading.value = true
    error.value = null
    try {
      const response = await analysisApi.getTemplates(params)
      analysisTemplates.value = response.data.items
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch analysis templates'
      throw err
    } finally {
      analysisTemplatesLoading.value = false
    }
  }

  async function fetchAnalysisTemplate(id: string) {
    try {
      const response = await analysisApi.getTemplate(id)
      selectedTemplate.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch analysis template'
      throw err
    }
  }

  async function fetchAnalysisTemplateBySlug(slug: string) {
    try {
      const response = await analysisApi.getTemplateBySlug(slug)
      selectedTemplate.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch analysis template'
      throw err
    }
  }

  // ========================================
  // Analysis Overview & Report Actions
  // ========================================

  async function fetchAnalysisOverview(params?: Record<string, unknown>) {
    analysisOverviewLoading.value = true
    error.value = null
    try {
      const response = await analysisApi.getOverview(params)
      analysisOverview.value = response.data.entities
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch analysis overview'
      throw err
    } finally {
      analysisOverviewLoading.value = false
    }
  }

  async function fetchEntityReport(entityId: string, params?: Record<string, unknown>) {
    entityReportLoading.value = true
    error.value = null
    try {
      const response = await analysisApi.getEntityReport(entityId, params)
      entityReport.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch entity report'
      throw err
    } finally {
      entityReportLoading.value = false
    }
  }

  async function fetchAnalysisStats(params?: Record<string, unknown>) {
    try {
      const response = await analysisApi.getStats(params)
      return response.data
    } catch (err: unknown) {
      error.value = getErrorMessage(err) || 'Failed to fetch analysis stats'
      throw err
    }
  }

  // ========================================
  // Setters
  // ========================================

  function setSelectedTemplate(template: AnalysisTemplate | null) {
    selectedTemplate.value = template
  }

  // ========================================
  // Utility Functions
  // ========================================

  function clearError() {
    error.value = null
  }

  function resetState() {
    analysisTemplates.value = []
    analysisOverview.value = []
    selectedTemplate.value = null
    entityReport.value = null
    error.value = null
  }

  // ========================================
  // Return
  // ========================================

  return {
    // State
    analysisTemplates,
    analysisTemplatesLoading,
    selectedTemplate,
    analysisOverview,
    analysisOverviewLoading,
    entityReport,
    entityReportLoading,
    error,

    // Analysis Template Actions
    fetchAnalysisTemplates,
    fetchAnalysisTemplate,
    fetchAnalysisTemplateBySlug,

    // Analysis Overview & Report Actions
    fetchAnalysisOverview,
    fetchEntityReport,
    fetchAnalysisStats,

    // Setters
    setSelectedTemplate,

    // Utility
    clearError,
    resetState,
  }
})

// Re-export types for convenience
export type {
  AnalysisTemplate,
  AnalysisOverviewItem,
  EntityReport,
  FacetConfig,
  AggregationConfig,
  DisplayConfig,
} from './types/entity'
