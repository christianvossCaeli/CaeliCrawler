import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSnackbar } from './useSnackbar'
import { facetApi } from '@/services/api'
import { escapeCSV, downloadFile, getStructuredDescription, getStructuredType, getStructuredSeverity } from './useEntityDetailHelpers'
import type { Entity, EntityType } from '@/stores/entity'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('useEntityExport')

export interface ExportOptions {
  facets: boolean
  relations: boolean
  dataSources: boolean
  notes: boolean
}

export interface ExportData {
  entity: {
    id: string
    name: string
    type?: string
    external_id?: string
    attributes: any
  }
  facets?: Record<string, any[]>
  relations?: any[]
  dataSources?: any[]
  notes?: any[]
}

export function useEntityExport() {
  const { t } = useI18n()
  const { showSuccess, showError } = useSnackbar()

  const exporting = ref(false)
  const exportFormat = ref('csv')
  const exportOptions = ref<ExportOptions>({
    facets: true,
    relations: true,
    dataSources: false,
    notes: false,
  })

  function generateCSV(data: ExportData): string {
    const lines: string[] = []

    // Entity info
    lines.push(`# ${t('entityDetail.csv.entityInformation')}`)
    lines.push(`${t('entityDetail.csv.name')},${escapeCSV(data.entity.name)}`)
    lines.push(`${t('entityDetail.csv.type')},${escapeCSV(data.entity.type || '')}`)
    lines.push(`${t('entityDetail.csv.externalId')},${escapeCSV(data.entity.external_id || '')}`)
    lines.push('')

    // Facets
    if (data.facets) {
      for (const [typeName, facets] of Object.entries(data.facets)) {
        lines.push(`# ${typeName}`)
        lines.push(`${t('entityDetail.csv.value')},${t('entityDetail.csv.type')},${t('entityDetail.csv.severity')},${t('entityDetail.csv.verified')},${t('entityDetail.csv.confidence')}`)
        for (const f of facets as any[]) {
          lines.push([
            escapeCSV(f.value || ''),
            escapeCSV(f.type || ''),
            escapeCSV(f.severity || ''),
            f.verified ? t('common.yes') : t('common.no'),
            f.confidence ? `${Math.round(f.confidence * 100)}%` : '',
          ].join(','))
        }
        lines.push('')
      }
    }

    // Relations
    if (data.relations?.length) {
      lines.push(`# ${t('entityDetail.csv.relations')}`)
      lines.push(`${t('entityDetail.csv.type')},${t('entityDetail.csv.target')},${t('entityDetail.csv.verified')}`)
      for (const r of data.relations) {
        lines.push([
          escapeCSV(r.type),
          escapeCSV(r.target),
          r.verified ? t('common.yes') : t('common.no'),
        ].join(','))
      }
      lines.push('')
    }

    // Notes
    if (data.notes?.length) {
      lines.push(`# ${t('entityDetail.csv.notes')}`)
      lines.push(`${t('entityDetail.csv.date')},${t('entityDetail.csv.author')},${t('entityDetail.csv.content')}`)
      for (const n of data.notes) {
        lines.push([
          escapeCSV(n.date || ''),
          escapeCSV(n.author || ''),
          escapeCSV(n.content || ''),
        ].join(','))
      }
    }

    return lines.join('\n')
  }

  async function exportData(
    entity: Entity,
    entityType: EntityType | null,
    facetsSummary: any,
    relations: any[],
    dataSources: any[],
    notes: any[]
  ) {
    exporting.value = true

    try {
      const data: ExportData = {
        entity: {
          id: entity.id,
          name: entity.name,
          type: entityType?.name,
          external_id: entity.external_id ?? undefined,
          attributes: entity.core_attributes,
        },
      }

      // Collect selected data
      if (exportOptions.value.facets && facetsSummary?.facets_by_type) {
        data.facets = {}
        for (const group of facetsSummary.facets_by_type) {
          // Load all facets for this type
          const response = await facetApi.getFacetValues({
            entity_id: entity.id,
            facet_type_slug: group.facet_type_slug,
            per_page: 10000,
          })
          data.facets[group.facet_type_name] = (response.data.items || []).map((f: any) => ({
            value: f.text_representation || getStructuredDescription(f),
            type: getStructuredType(f),
            severity: getStructuredSeverity(f),
            verified: f.human_verified,
            confidence: f.confidence_score,
            source_url: f.source_url,
          }))
        }
      }

      if (exportOptions.value.relations) {
        data.relations = relations.map(r => ({
          type: r.relation_type_name,
          target: r.source_entity_id === entity.id ? r.target_entity_name : r.source_entity_name,
          verified: r.human_verified,
        }))
      }

      if (exportOptions.value.dataSources) {
        data.dataSources = dataSources.map(s => ({
          name: s.name,
          url: s.base_url,
          status: s.status,
        }))
      }

      if (exportOptions.value.notes) {
        data.notes = notes.map(n => ({
          content: n.content,
          author: n.author,
          date: n.created_at,
        }))
      }

      // Generate export file
      if (exportFormat.value === 'json') {
        downloadFile(
          JSON.stringify(data, null, 2),
          `${entity.name}_export.json`,
          'application/json'
        )
      } else if (exportFormat.value === 'csv') {
        const csv = generateCSV(data)
        downloadFile(csv, `${entity.name}_export.csv`, 'text/csv')
      } else if (exportFormat.value === 'pdf') {
        // For PDF, we'd need a library like jsPDF or generate on backend
        // For now, show message
        showError(t('entityDetail.messages.pdfNotAvailable'))
        return false
      }

      showSuccess(t('entityDetail.messages.exportSuccess'))
      return true
    } catch (e) {
      logger.error('Export failed', e)
      showError(t('entityDetail.messages.exportError'))
      return false
    } finally {
      exporting.value = false
    }
  }

  return {
    exporting,
    exportFormat,
    exportOptions,
    exportData,
  }
}
