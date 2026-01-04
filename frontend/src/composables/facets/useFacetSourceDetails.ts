/**
 * Facet Source Details Composable
 *
 * Handles displaying source/metadata details for facets.
 */

import { ref } from 'vue'
import type { FacetValue, SourceFacet } from './types'

export function useFacetSourceDetails() {
  // State
  const selectedSourceFacet = ref<SourceFacet | null>(null)

  // Functions
  function openSourceDetails(facet: FacetValue) {
    selectedSourceFacet.value = {
      source_type: facet.source_type || 'DOCUMENT',
      source_url: facet.source_url,
      document_title: facet.document_title,
      document_url: facet.document_url,
      verified_by: facet.verified_by,
      ai_model_used: facet.ai_model_used,
      confidence_score: facet.confidence_score,
      created_at: facet.created_at,
      verified_at: facet.verified_at,
      human_verified: facet.human_verified,
      value: facet.value as Record<string, unknown> | null,
    }
  }

  function closeSourceDetails() {
    selectedSourceFacet.value = null
  }

  return {
    // State
    selectedSourceFacet,

    // Functions
    openSourceDetails,
    closeSourceDetails,
  }
}
