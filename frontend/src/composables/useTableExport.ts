/**
 * Table Export Composable.
 *
 * Provides utilities for exporting table data to CSV and JSON formats.
 * Eliminates code duplication across DocumentsView, ResultsView, etc.
 */

import { escapeCSV, downloadFile, formatDate } from '@/utils/viewHelpers'

export interface ExportColumn {
  /** Column key in data object */
  key: string
  /** Column header label */
  label: string
  /** Optional formatter function */
  formatter?: (value: any, row: any) => string
}

export interface ExportOptions {
  /** File name without extension */
  filename: string
  /** Column definitions */
  columns: ExportColumn[]
  /** Include BOM for Excel compatibility */
  includeBom?: boolean
  /** Date format for date columns */
  dateFormat?: Intl.DateTimeFormatOptions
}

/**
 * Composable for table data export functionality.
 */
export function useTableExport() {
  /**
   * Export data to CSV format.
   * @param data - Array of data objects
   * @param options - Export options
   */
  function exportToCsv<T extends Record<string, any>>(
    data: T[],
    options: ExportOptions
  ): void {
    const { filename, columns, includeBom = true } = options

    // Build header row
    const headers = columns.map(col => escapeCSV(col.label)).join(',')

    // Build data rows
    const rows = data.map(row => {
      return columns.map(col => {
        const value = row[col.key]
        const formatted = col.formatter ? col.formatter(value, row) : formatValue(value)
        return escapeCSV(formatted)
      }).join(',')
    })

    // Combine with newlines
    const csv = [headers, ...rows].join('\n')

    // Add BOM for Excel compatibility
    const content = includeBom ? '\ufeff' + csv : csv

    downloadFile(content, `${filename}.csv`, 'text/csv;charset=utf-8')
  }

  /**
   * Export data to JSON format.
   * @param data - Array of data objects
   * @param options - Export options (only filename used)
   */
  function exportToJson<T extends Record<string, any>>(
    data: T[],
    options: Pick<ExportOptions, 'filename' | 'columns'>
  ): void {
    const { filename, columns } = options

    // If columns specified, only export those fields
    let exportData: Record<string, any>[] = data
    if (columns.length > 0) {
      exportData = data.map(row => {
        const obj: Record<string, any> = {}
        columns.forEach(col => {
          const value = row[col.key]
          obj[col.label] = col.formatter ? col.formatter(value, row) : value
        })
        return obj
      })
    }

    const json = JSON.stringify(exportData, null, 2)
    downloadFile(json, `${filename}.json`, 'application/json')
  }

  /**
   * Format a value for CSV export.
   */
  function formatValue(value: any): string {
    if (value === null || value === undefined) return ''
    if (value instanceof Date) return formatDate(value)
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  /**
   * Create a date formatter for export columns.
   */
  function dateFormatter(options?: Intl.DateTimeFormatOptions) {
    return (value: any) => {
      if (!value) return ''
      return formatDate(value, options)
    }
  }

  /**
   * Create a boolean formatter (Ja/Nein).
   */
  function booleanFormatter(trueLabel = 'Ja', falseLabel = 'Nein') {
    return (value: any) => value ? trueLabel : falseLabel
  }

  /**
   * Create a number formatter.
   */
  function numberFormatter(options?: Intl.NumberFormatOptions) {
    return (value: any) => {
      if (value === null || value === undefined) return ''
      return Number(value).toLocaleString('de-DE', options)
    }
  }

  /**
   * Create a percent formatter.
   */
  function percentFormatter(decimals = 0) {
    return (value: any) => {
      if (value === null || value === undefined) return ''
      const num = Number(value)
      if (isNaN(num)) return ''
      return `${(num * 100).toFixed(decimals)}%`
    }
  }

  return {
    exportToCsv,
    exportToJson,
    // Formatters
    dateFormatter,
    booleanFormatter,
    numberFormatter,
    percentFormatter,
  }
}
