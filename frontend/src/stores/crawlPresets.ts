/**
 * Crawl Presets Store
 *
 * Manages saved crawl filter configurations for deterministic re-execution.
 * Unlike Smart Query History (which saves AI-interpreted commands),
 * presets store the exact technical filter configuration.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { crawlPresetsApi } from '@/services/api'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('CrawlPresetsStore')

export interface CrawlPresetFilters {
  category_id?: string
  tags?: string[]
  entity_type?: string[]  // Multi-select: array of entity type slugs
  admin_level_1?: string  // Deprecated - use tags instead
  entity_filters?: Record<string, any>
  country?: string
  source_type?: string[]  // Multi-select: array of source types
  status?: string
  search?: string
  limit?: number
}

/**
 * Utility function to clean filter objects by removing empty values.
 * Removes undefined, null, empty strings, and empty arrays.
 */
export function cleanFilters(filters: CrawlPresetFilters): CrawlPresetFilters {
  const cleaned: CrawlPresetFilters = {}

  for (const [key, value] of Object.entries(filters)) {
    // Skip undefined, null, empty strings
    if (value === undefined || value === null || value === '') continue
    // Skip empty arrays
    if (Array.isArray(value) && value.length === 0) continue
    // Skip empty objects
    if (typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === 0) continue

    cleaned[key as keyof CrawlPresetFilters] = value
  }

  return cleaned
}

/** Maximum number of presets shown in QuickActions widget */
export const MAX_QUICK_ACTION_PRESETS = 5

export interface CrawlPreset {
  id: string
  user_id: string
  name: string
  description: string | null
  filters: CrawlPresetFilters
  filter_summary: string
  schedule_cron: string | null
  schedule_enabled: boolean
  next_run_at: string | null
  usage_count: number
  last_used_at: string | null
  last_scheduled_run_at: string | null
  is_favorite: boolean
  status: 'active' | 'archived'
  created_at: string
  updated_at: string
}

export interface CrawlPresetCreate {
  name: string
  description?: string
  filters: CrawlPresetFilters
  schedule_cron?: string
  schedule_enabled?: boolean
}

export interface CrawlPresetUpdate {
  name?: string
  description?: string
  filters?: CrawlPresetFilters
  schedule_cron?: string
  schedule_enabled?: boolean
  is_favorite?: boolean
  status?: 'active' | 'archived'
}

export const useCrawlPresetsStore = defineStore('crawlPresets', () => {
  // State
  const presets = ref<CrawlPreset[]>([])
  const favoriteIds = ref<Set<string>>(new Set())
  const isLoading = ref(false)
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(20)
  const error = ref<string | null>(null)

  // Computed
  const favoriteCount = computed(() => favoriteIds.value.size)
  const favorites = computed(() => presets.value.filter((p) => p.is_favorite))
  const activePresets = computed(() => presets.value.filter((p) => p.status === 'active'))
  const scheduledPresets = computed(() => presets.value.filter((p) => p.schedule_enabled))

  /**
   * Check if preset is favorited (instant lookup)
   */
  function isFavorited(presetId: string): boolean {
    return favoriteIds.value.has(presetId)
  }

  /**
   * Get preset by ID
   */
  function getPresetById(presetId: string): CrawlPreset | undefined {
    return presets.value.find((p) => p.id === presetId)
  }

  /**
   * Load presets from API
   */
  async function loadPresets(options?: {
    page?: number
    per_page?: number
    favorites_only?: boolean
    status?: string
    search?: string
  }): Promise<void> {
    isLoading.value = true
    error.value = null

    if (options?.per_page) {
      perPage.value = options.per_page
    }

    try {
      const response = await crawlPresetsApi.list({
        page: options?.page || page.value,
        per_page: perPage.value,
        favorites_only: options?.favorites_only,
        status: options?.status,
        search: options?.search,
      })

      presets.value = response.data.items
      total.value = response.data.total
      page.value = response.data.page

      // Update favoriteIds set for quick lookup
      favoriteIds.value = new Set(presets.value.filter((p) => p.is_favorite).map((p) => p.id))
    } catch (e) {
      logger.error('Failed to load crawl presets:', e)
      error.value = 'Failed to load presets'
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Create a new preset
   */
  async function createPreset(data: CrawlPresetCreate): Promise<CrawlPreset | null> {
    try {
      const response = await crawlPresetsApi.create(data)
      const newPreset = response.data

      // Add to local state
      presets.value.unshift(newPreset)
      total.value++

      if (newPreset.is_favorite) {
        favoriteIds.value.add(newPreset.id)
      }

      return newPreset
    } catch (e) {
      logger.error('Failed to create preset:', e)
      error.value = 'Failed to create preset'
      return null
    }
  }

  /**
   * Update an existing preset
   */
  async function updatePreset(presetId: string, data: CrawlPresetUpdate): Promise<CrawlPreset | null> {
    try {
      const response = await crawlPresetsApi.update(presetId, data)
      const updatedPreset = response.data

      // Update local state
      const index = presets.value.findIndex((p) => p.id === presetId)
      if (index > -1) {
        presets.value[index] = updatedPreset
      }

      // Update favorite set
      if (updatedPreset.is_favorite) {
        favoriteIds.value.add(presetId)
      } else {
        favoriteIds.value.delete(presetId)
      }

      return updatedPreset
    } catch (e) {
      logger.error('Failed to update preset:', e)
      error.value = 'Failed to update preset'
      return null
    }
  }

  /**
   * Delete a preset
   */
  async function deletePreset(presetId: string): Promise<boolean> {
    try {
      await crawlPresetsApi.delete(presetId)

      // Remove from local state
      const index = presets.value.findIndex((p) => p.id === presetId)
      if (index > -1) {
        presets.value.splice(index, 1)
      }
      favoriteIds.value.delete(presetId)
      total.value = Math.max(0, total.value - 1)

      return true
    } catch (e) {
      logger.error('Failed to delete preset:', e)
      error.value = 'Failed to delete preset'
      return false
    }
  }

  /**
   * Execute a preset (start crawl with preset filters)
   */
  async function executePreset(presetId: string, force: boolean = false): Promise<{
    success: boolean
    jobs_created: number
    sources_matched: number
    message: string
  } | null> {
    try {
      const response = await crawlPresetsApi.execute(presetId, { force })

      // Update local state
      const preset = presets.value.find((p) => p.id === presetId)
      if (preset) {
        preset.usage_count++
        preset.last_used_at = new Date().toISOString()
      }

      return {
        success: true,
        jobs_created: response.data.jobs_created,
        sources_matched: response.data.sources_matched,
        message: response.data.message,
      }
    } catch (e) {
      logger.error('Failed to execute preset:', e)
      error.value = 'Failed to execute preset'
      return null
    }
  }

  /**
   * Toggle favorite status
   */
  async function toggleFavorite(presetId: string): Promise<boolean> {
    try {
      const response = await crawlPresetsApi.toggleFavorite(presetId)
      const newState = response.data.is_favorite

      // Update local state
      const preset = presets.value.find((p) => p.id === presetId)
      if (preset) {
        preset.is_favorite = newState
      }

      if (newState) {
        favoriteIds.value.add(presetId)
      } else {
        favoriteIds.value.delete(presetId)
      }

      return newState
    } catch (e) {
      logger.error('Failed to toggle favorite:', e)
      error.value = 'Failed to toggle favorite'
      return false
    }
  }

  /**
   * Create preset from current filter selection
   */
  async function createFromFilters(
    name: string,
    filters: CrawlPresetFilters,
    options?: {
      description?: string
      schedule_cron?: string
      schedule_enabled?: boolean
    }
  ): Promise<CrawlPreset | null> {
    try {
      const response = await crawlPresetsApi.createFromFilters({
        name,
        filters,
        description: options?.description,
        schedule_cron: options?.schedule_cron,
        schedule_enabled: options?.schedule_enabled || false,
      })
      const newPreset = response.data

      // Add to local state
      presets.value.unshift(newPreset)
      total.value++

      return newPreset
    } catch (e) {
      logger.error('Failed to create preset from filters:', e)
      error.value = 'Failed to create preset'
      return null
    }
  }

  /**
   * Preview how many sources would be crawled
   */
  async function previewPreset(presetId: string): Promise<{
    sources_count: number
    sources_preview: Array<{ id: string; name: string; url: string }>
    has_more: boolean
  } | null> {
    try {
      const response = await crawlPresetsApi.preview(presetId)
      return response.data
    } catch (e) {
      logger.error('Failed to preview preset:', e)
      error.value = 'Failed to preview preset'
      return null
    }
  }

  /**
   * Clear store on logout
   */
  function clearStore(): void {
    presets.value = []
    favoriteIds.value.clear()
    total.value = 0
    page.value = 1
    error.value = null
  }

  return {
    // State
    presets,
    favoriteIds,
    isLoading,
    total,
    page,
    perPage,
    error,

    // Computed
    favoriteCount,
    favorites,
    activePresets,
    scheduledPresets,

    // Actions
    isFavorited,
    getPresetById,
    loadPresets,
    createPreset,
    updatePreset,
    deletePreset,
    executePreset,
    toggleFavorite,
    createFromFilters,
    previewPreset,
    clearStore,
  }
})
