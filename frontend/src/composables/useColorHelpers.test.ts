/**
 * Tests for useColorHelpers composable
 */
import { describe, it, expect } from 'vitest'
import { isLightColor, getContrastColor, useColorHelpers } from './useColorHelpers'

describe('isLightColor', () => {
  describe('valid hex colors', () => {
    it('should return true for white (#FFFFFF)', () => {
      expect(isLightColor('#FFFFFF')).toBe(true)
      expect(isLightColor('#ffffff')).toBe(true)
    })

    it('should return false for black (#000000)', () => {
      expect(isLightColor('#000000')).toBe(false)
    })

    it('should return true for light gray (#CCCCCC)', () => {
      expect(isLightColor('#CCCCCC')).toBe(true)
    })

    it('should return false for dark gray (#333333)', () => {
      expect(isLightColor('#333333')).toBe(false)
    })

    it('should return true for light yellow (#FFFF00)', () => {
      expect(isLightColor('#FFFF00')).toBe(true)
    })

    it('should return false for dark blue (#000080)', () => {
      expect(isLightColor('#000080')).toBe(false)
    })

    it('should handle 3-digit hex colors', () => {
      expect(isLightColor('#FFF')).toBe(true)
      expect(isLightColor('#000')).toBe(false)
      expect(isLightColor('#CCC')).toBe(true)
    })
  })

  describe('invalid inputs', () => {
    it('should return false for undefined', () => {
      expect(isLightColor(undefined)).toBe(false)
    })

    it('should return false for empty string', () => {
      expect(isLightColor('')).toBe(false)
    })

    it('should return false for non-hex colors', () => {
      expect(isLightColor('red')).toBe(false)
      expect(isLightColor('primary')).toBe(false)
    })

    it('should return false for invalid hex lengths', () => {
      expect(isLightColor('#FF')).toBe(false)
      expect(isLightColor('#FFFFFFF')).toBe(false)
    })

    it('should return false for colors without #', () => {
      expect(isLightColor('FFFFFF')).toBe(false)
    })
  })

  describe('edge cases', () => {
    it('should handle mid-tone grays around threshold', () => {
      // Luminance threshold is 0.6
      // At luminance ~0.6, color is around #999999
      expect(isLightColor('#AAAAAA')).toBe(true)  // Above threshold
      expect(isLightColor('#888888')).toBe(false) // Below threshold
    })

    it('should consider green more luminous than red (per ITU-R BT.709)', () => {
      // Green contributes more to perceived brightness (0.587 coefficient)
      // Pure green #00FF00 has luminance of 0.587, which is < 0.6 threshold
      // But green is more luminous than pure red (0.299 coefficient)
      // Using lighter greens and reds to demonstrate:
      expect(isLightColor('#90EE90')).toBe(true)  // Light green - above threshold
      expect(isLightColor('#FF6666')).toBe(false) // Light red - still below threshold
    })
  })
})

describe('getContrastColor', () => {
  describe('hex colors', () => {
    it('should return dark color for light backgrounds', () => {
      expect(getContrastColor('#FFFFFF')).toBe('black')
      expect(getContrastColor('#FFFF00')).toBe('black')
    })

    it('should return light color for dark backgrounds', () => {
      expect(getContrastColor('#000000')).toBe('white')
      expect(getContrastColor('#000080')).toBe('white')
    })

    it('should use custom fallback colors', () => {
      expect(getContrastColor('#FFFFFF', 'grey-darken-4', 'grey-lighten-4')).toBe('grey-darken-4')
      expect(getContrastColor('#000000', 'grey-darken-4', 'grey-lighten-4')).toBe('grey-lighten-4')
    })
  })

  describe('Vuetify semantic colors', () => {
    it('should return on-* variant for primary', () => {
      expect(getContrastColor('primary')).toBe('on-primary')
    })

    it('should return on-* variant for secondary', () => {
      expect(getContrastColor('secondary')).toBe('on-secondary')
    })

    it('should return on-* variant for success', () => {
      expect(getContrastColor('success')).toBe('on-success')
    })

    it('should return on-* variant for info', () => {
      expect(getContrastColor('info')).toBe('on-info')
    })

    it('should return on-* variant for warning', () => {
      expect(getContrastColor('warning')).toBe('on-warning')
    })

    it('should return on-* variant for error', () => {
      expect(getContrastColor('error')).toBe('on-error')
    })

    it('should handle darken/lighten variants', () => {
      expect(getContrastColor('primary-darken-1')).toBe('on-primary')
      expect(getContrastColor('secondary-lighten-2')).toBe('on-secondary')
    })
  })

  describe('edge cases', () => {
    it('should return fallbackLight for undefined', () => {
      expect(getContrastColor(undefined)).toBe('white')
    })

    it('should return fallbackLight for empty string', () => {
      expect(getContrastColor('')).toBe('white')
    })

    it('should return fallbackLight for unknown colors', () => {
      expect(getContrastColor('unknown-color')).toBe('white')
    })

    it('should use custom fallbackLight', () => {
      expect(getContrastColor(undefined, 'black', 'gray')).toBe('gray')
    })
  })
})

describe('useColorHelpers', () => {
  it('should return isLightColor function', () => {
    const { isLightColor: fn } = useColorHelpers()

    expect(fn).toBeInstanceOf(Function)
    expect(fn('#FFFFFF')).toBe(true)
  })

  it('should return getContrastColor function', () => {
    const { getContrastColor: fn } = useColorHelpers()

    expect(fn).toBeInstanceOf(Function)
    expect(fn('primary')).toBe('on-primary')
  })
})
