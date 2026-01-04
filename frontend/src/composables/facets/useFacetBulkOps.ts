/**
 * Facet Bulk Operations Composable
 *
 * Handles bulk verification and deletion of facets.
 */

import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSnackbar } from '@/composables/useSnackbar'
import { useEntityStore } from '@/stores/entity'
import { facetApi } from '@/services/api'

export function useFacetBulkOps(
  onFacetsSummaryUpdate: () => Promise<void>,
  resetExpandedFacetValues: () => void,
) {
  const { t } = useI18n()
  const { showSuccess, showError } = useSnackbar()
  const store = useEntityStore()

  // State
  const bulkMode = ref(false)
  const selectedFacetIds = ref<string[]>([])
  const bulkActionLoading = ref(false)

  // Functions
  function toggleFacetSelection(id: string) {
    const idx = selectedFacetIds.value.indexOf(id)
    if (idx >= 0) {
      selectedFacetIds.value.splice(idx, 1)
    } else {
      selectedFacetIds.value.push(id)
    }
  }

  async function bulkVerify() {
    if (selectedFacetIds.value.length === 0) return

    bulkActionLoading.value = true
    try {
      await Promise.all(selectedFacetIds.value.map((id) => store.verifyFacetValue(id, true)))

      showSuccess(t('entityDetail.messages.facetsVerified', { count: selectedFacetIds.value.length }))

      selectedFacetIds.value = []
      bulkMode.value = false
      await onFacetsSummaryUpdate()
    } catch {
      showError(t('entityDetail.messages.verifyError'))
    } finally {
      bulkActionLoading.value = false
    }
  }

  async function bulkDelete() {
    if (selectedFacetIds.value.length === 0) return

    bulkActionLoading.value = true
    try {
      await Promise.all(selectedFacetIds.value.map((id) => facetApi.deleteFacetValue(id)))

      showSuccess(t('entityDetail.messages.facetsDeleted', { count: selectedFacetIds.value.length }))

      selectedFacetIds.value = []
      bulkMode.value = false
      resetExpandedFacetValues()

      await onFacetsSummaryUpdate()
    } catch {
      showError(t('entityDetail.messages.deleteError'))
    } finally {
      bulkActionLoading.value = false
    }
  }

  function resetBulkMode() {
    bulkMode.value = false
    selectedFacetIds.value = []
  }

  function enterBulkMode() {
    bulkMode.value = true
    selectedFacetIds.value = []
  }

  function isFacetSelected(id: string): boolean {
    return selectedFacetIds.value.includes(id)
  }

  return {
    // State
    bulkMode,
    selectedFacetIds,
    bulkActionLoading,

    // Functions
    toggleFacetSelection,
    bulkVerify,
    bulkDelete,
    resetBulkMode,
    enterBulkMode,
    isFacetSelected,
  }
}
