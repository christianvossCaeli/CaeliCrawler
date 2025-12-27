/**
 * Tests for useTableExport composable
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useTableExport, type ExportColumn } from './useTableExport'

// Mock viewHelpers
const mockDownloadFile = vi.fn()
vi.mock('@/utils/viewHelpers', () => ({
  escapeCSV: (value: string) => {
    if (value.includes(',') || value.includes('"') || value.includes('\n')) {
      return `"${value.replace(/"/g, '""')}"`
    }
    return value
  },
  downloadFile: (...args: unknown[]) => mockDownloadFile(...args),
  formatDate: (value: Date | string, _options?: Intl.DateTimeFormatOptions) => {
    const date = value instanceof Date ? value : new Date(value)
    return date.toISOString().split('T')[0]
  },
  formatNumber: (value: number, options?: Intl.NumberFormatOptions) => value.toLocaleString('de-DE', options),
}))

describe('useTableExport', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('exportToCsv', () => {
    it('should export data with headers', () => {
      const { exportToCsv } = useTableExport()
      const data = [
        { name: 'Alice', age: 30 },
        { name: 'Bob', age: 25 },
      ]
      const columns: ExportColumn[] = [
        { key: 'name', label: 'Name' },
        { key: 'age', label: 'Age' },
      ]

      exportToCsv(data, { filename: 'test', columns })

      expect(mockDownloadFile).toHaveBeenCalledWith(
        expect.stringContaining('Name,Age'),
        'test.csv',
        'text/csv;charset=utf-8'
      )
    })

    it('should include BOM by default', () => {
      const { exportToCsv } = useTableExport()
      const data = [{ name: 'Test' }]
      const columns: ExportColumn[] = [{ key: 'name', label: 'Name' }]

      exportToCsv(data, { filename: 'test', columns })

      const [content] = mockDownloadFile.mock.calls[0]
      expect(content.startsWith('\ufeff')).toBe(true)
    })

    it('should not include BOM when disabled', () => {
      const { exportToCsv } = useTableExport()
      const data = [{ name: 'Test' }]
      const columns: ExportColumn[] = [{ key: 'name', label: 'Name' }]

      exportToCsv(data, { filename: 'test', columns, includeBom: false })

      const [content] = mockDownloadFile.mock.calls[0]
      expect(content.startsWith('\ufeff')).toBe(false)
    })

    it('should use column formatter if provided', () => {
      const { exportToCsv } = useTableExport()
      const data = [{ price: 1000 }]
      const columns: ExportColumn[] = [
        { key: 'price', label: 'Price', formatter: (v) => `$${v}` },
      ]

      exportToCsv(data, { filename: 'test', columns })

      const [content] = mockDownloadFile.mock.calls[0]
      expect(content).toContain('$1000')
    })

    it('should handle null/undefined values', () => {
      const { exportToCsv } = useTableExport()
      const data = [{ name: null, age: undefined }]
      const columns: ExportColumn[] = [
        { key: 'name', label: 'Name' },
        { key: 'age', label: 'Age' },
      ]

      exportToCsv(data, { filename: 'test', columns })

      const [content] = mockDownloadFile.mock.calls[0]
      // Should have empty values (just comma between)
      expect(content).toContain(',')
    })

    it('should escape CSV special characters', () => {
      const { exportToCsv } = useTableExport()
      const data = [{ name: 'Smith, John' }]
      const columns: ExportColumn[] = [{ key: 'name', label: 'Name' }]

      exportToCsv(data, { filename: 'test', columns })

      const [content] = mockDownloadFile.mock.calls[0]
      expect(content).toContain('"Smith, John"')
    })

    it('should handle Date objects', () => {
      const { exportToCsv } = useTableExport()
      const testDate = new Date('2024-01-15')
      const data = [{ date: testDate }]
      const columns: ExportColumn[] = [{ key: 'date', label: 'Date' }]

      exportToCsv(data, { filename: 'test', columns })

      const [content] = mockDownloadFile.mock.calls[0]
      expect(content).toContain('2024-01-15')
    })

    it('should stringify objects', () => {
      const { exportToCsv } = useTableExport()
      const data = [{ meta: { foo: 'bar' } }]
      const columns: ExportColumn[] = [{ key: 'meta', label: 'Meta' }]

      exportToCsv(data, { filename: 'test', columns })

      const [content] = mockDownloadFile.mock.calls[0]
      // The JSON is escaped for CSV (quotes doubled)
      expect(content).toContain('foo')
      expect(content).toContain('bar')
    })
  })

  describe('exportToJson', () => {
    it('should export data as JSON', () => {
      const { exportToJson } = useTableExport()
      const data = [
        { name: 'Alice', age: 30 },
        { name: 'Bob', age: 25 },
      ]
      const columns: ExportColumn[] = [
        { key: 'name', label: 'Name' },
        { key: 'age', label: 'Age' },
      ]

      exportToJson(data, { filename: 'test', columns })

      expect(mockDownloadFile).toHaveBeenCalledWith(
        expect.any(String),
        'test.json',
        'application/json'
      )
    })

    it('should use column labels as keys', () => {
      const { exportToJson } = useTableExport()
      const data = [{ name: 'Alice' }]
      const columns: ExportColumn[] = [
        { key: 'name', label: 'Full Name' },
      ]

      exportToJson(data, { filename: 'test', columns })

      const [content] = mockDownloadFile.mock.calls[0]
      const parsed = JSON.parse(content)
      expect(parsed[0]).toHaveProperty('Full Name', 'Alice')
    })

    it('should apply column formatters', () => {
      const { exportToJson } = useTableExport()
      const data = [{ price: 1000 }]
      const columns: ExportColumn[] = [
        { key: 'price', label: 'Price', formatter: (v) => `$${v}` },
      ]

      exportToJson(data, { filename: 'test', columns })

      const [content] = mockDownloadFile.mock.calls[0]
      const parsed = JSON.parse(content)
      expect(parsed[0].Price).toBe('$1000')
    })

    it('should format JSON with indentation', () => {
      const { exportToJson } = useTableExport()
      const data = [{ name: 'Test' }]
      const columns: ExportColumn[] = [{ key: 'name', label: 'Name' }]

      exportToJson(data, { filename: 'test', columns })

      const [content] = mockDownloadFile.mock.calls[0]
      expect(content).toContain('\n')
    })
  })

  describe('dateFormatter', () => {
    it('should format dates', () => {
      const { dateFormatter } = useTableExport()
      const formatter = dateFormatter()

      expect(formatter(new Date('2024-01-15'))).toBe('2024-01-15')
    })

    it('should handle null/undefined', () => {
      const { dateFormatter } = useTableExport()
      const formatter = dateFormatter()

      expect(formatter(null)).toBe('')
      expect(formatter(undefined)).toBe('')
    })

    it('should handle date strings', () => {
      const { dateFormatter } = useTableExport()
      const formatter = dateFormatter()

      expect(formatter('2024-01-15T10:00:00Z')).toBe('2024-01-15')
    })
  })

  describe('booleanFormatter', () => {
    it('should return default labels', () => {
      const { booleanFormatter } = useTableExport()
      const formatter = booleanFormatter()

      expect(formatter(true)).toBe('Ja')
      expect(formatter(false)).toBe('Nein')
    })

    it('should use custom labels', () => {
      const { booleanFormatter } = useTableExport()
      const formatter = booleanFormatter('Yes', 'No')

      expect(formatter(true)).toBe('Yes')
      expect(formatter(false)).toBe('No')
    })

    it('should handle truthy/falsy values', () => {
      const { booleanFormatter } = useTableExport()
      const formatter = booleanFormatter()

      expect(formatter(1)).toBe('Ja')
      expect(formatter(0)).toBe('Nein')
      expect(formatter('')).toBe('Nein')
      expect(formatter('yes')).toBe('Ja')
    })
  })

  describe('numberFormatter', () => {
    it('should format numbers with German locale', () => {
      const { numberFormatter } = useTableExport()
      const formatter = numberFormatter()

      // German locale uses . for thousands and , for decimals
      expect(formatter(1000)).toBe('1.000')
    })

    it('should handle null/undefined', () => {
      const { numberFormatter } = useTableExport()
      const formatter = numberFormatter()

      expect(formatter(null)).toBe('')
      expect(formatter(undefined)).toBe('')
    })

    it('should accept Intl options', () => {
      const { numberFormatter } = useTableExport()
      const formatter = numberFormatter({ minimumFractionDigits: 2 })

      expect(formatter(100)).toContain('00')
    })
  })

  describe('percentFormatter', () => {
    it('should format as percentage', () => {
      const { percentFormatter } = useTableExport()
      const formatter = percentFormatter()

      expect(formatter(0.5)).toBe('50%')
      expect(formatter(1)).toBe('100%')
    })

    it('should use specified decimals', () => {
      const { percentFormatter } = useTableExport()
      const formatter = percentFormatter(2)

      expect(formatter(0.5555)).toBe('55.55%')
    })

    it('should handle null/undefined', () => {
      const { percentFormatter } = useTableExport()
      const formatter = percentFormatter()

      expect(formatter(null)).toBe('')
      expect(formatter(undefined)).toBe('')
    })

    it('should handle NaN', () => {
      const { percentFormatter } = useTableExport()
      const formatter = percentFormatter()

      expect(formatter('not a number')).toBe('')
    })
  })
})
