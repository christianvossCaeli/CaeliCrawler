/**
 * Tests for useSnackbar composable
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useSnackbar } from './useSnackbar'

describe('useSnackbar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset the global state between tests
    const { snackbar } = useSnackbar()
    snackbar.value = false
  })

  describe('State Management', () => {
    it('should expose all state refs', () => {
      const { snackbar, snackbarText, snackbarColor, snackbarTimeout } = useSnackbar()

      expect(snackbar.value).toBe(false)
      expect(snackbarText.value).toBeDefined()
      expect(snackbarColor.value).toBeDefined()
      expect(snackbarTimeout.value).toBeDefined()
    })

    it('should use shared global state', () => {
      const instance1 = useSnackbar()
      const instance2 = useSnackbar()

      instance1.showSuccess('Test')

      // Both instances should see the same state
      expect(instance1.snackbar.value).toBe(true)
      expect(instance2.snackbar.value).toBe(true)
      expect(instance2.snackbarText.value).toBe('Test')
    })
  })

  describe('showMessage', () => {
    it('should show message with default success color', () => {
      const { showMessage, snackbar, snackbarText, snackbarColor, snackbarTimeout } = useSnackbar()

      showMessage('Test message')

      expect(snackbar.value).toBe(true)
      expect(snackbarText.value).toBe('Test message')
      expect(snackbarColor.value).toBe('success')
      expect(snackbarTimeout.value).toBe(3000)
    })

    it('should show message with custom color', () => {
      const { showMessage, snackbarColor } = useSnackbar()

      showMessage('Error message', 'error')

      expect(snackbarColor.value).toBe('error')
    })

    it('should show message with custom timeout', () => {
      const { showMessage, snackbarTimeout } = useSnackbar()

      showMessage('Quick message', 'info', 1500)

      expect(snackbarTimeout.value).toBe(1500)
    })

    it('should accept all valid color types', () => {
      const { showMessage, snackbarColor } = useSnackbar()

      showMessage('Success', 'success')
      expect(snackbarColor.value).toBe('success')

      showMessage('Error', 'error')
      expect(snackbarColor.value).toBe('error')

      showMessage('Warning', 'warning')
      expect(snackbarColor.value).toBe('warning')

      showMessage('Info', 'info')
      expect(snackbarColor.value).toBe('info')
    })
  })

  describe('showSuccess', () => {
    it('should show success message with correct color', () => {
      const { showSuccess, snackbar, snackbarText, snackbarColor, snackbarTimeout } = useSnackbar()

      showSuccess('Operation successful')

      expect(snackbar.value).toBe(true)
      expect(snackbarText.value).toBe('Operation successful')
      expect(snackbarColor.value).toBe('success')
      expect(snackbarTimeout.value).toBe(3000)
    })

    it('should use default timeout', () => {
      const { showSuccess, snackbarTimeout } = useSnackbar()

      showSuccess('Success')

      expect(snackbarTimeout.value).toBe(3000)
    })
  })

  describe('showError', () => {
    it('should show error message with correct color', () => {
      const { showError, snackbar, snackbarText, snackbarColor, snackbarTimeout } = useSnackbar()

      showError('Operation failed')

      expect(snackbar.value).toBe(true)
      expect(snackbarText.value).toBe('Operation failed')
      expect(snackbarColor.value).toBe('error')
      expect(snackbarTimeout.value).toBe(5000)
    })

    it('should use longer timeout for errors', () => {
      const { showError, snackbarTimeout } = useSnackbar()

      showError('Error')

      expect(snackbarTimeout.value).toBe(5000)
    })
  })

  describe('showWarning', () => {
    it('should show warning message with correct color', () => {
      const { showWarning, snackbar, snackbarText, snackbarColor, snackbarTimeout } = useSnackbar()

      showWarning('Be careful')

      expect(snackbar.value).toBe(true)
      expect(snackbarText.value).toBe('Be careful')
      expect(snackbarColor.value).toBe('warning')
      expect(snackbarTimeout.value).toBe(4000)
    })

    it('should use medium timeout for warnings', () => {
      const { showWarning, snackbarTimeout } = useSnackbar()

      showWarning('Warning')

      expect(snackbarTimeout.value).toBe(4000)
    })
  })

  describe('showInfo', () => {
    it('should show info message with correct color', () => {
      const { showInfo, snackbar, snackbarText, snackbarColor, snackbarTimeout } = useSnackbar()

      showInfo('Information')

      expect(snackbar.value).toBe(true)
      expect(snackbarText.value).toBe('Information')
      expect(snackbarColor.value).toBe('info')
      expect(snackbarTimeout.value).toBe(3000)
    })

    it('should use default timeout', () => {
      const { showInfo, snackbarTimeout } = useSnackbar()

      showInfo('Info')

      expect(snackbarTimeout.value).toBe(3000)
    })
  })

  describe('Edge Cases', () => {
    it('should handle empty string messages', () => {
      const { showSuccess, snackbar, snackbarText } = useSnackbar()

      showSuccess('')

      expect(snackbar.value).toBe(true)
      expect(snackbarText.value).toBe('')
    })

    it('should handle very long messages', () => {
      const { showSuccess, snackbarText } = useSnackbar()
      const longMessage = 'a'.repeat(1000)

      showSuccess(longMessage)

      expect(snackbarText.value).toBe(longMessage)
    })

    it('should handle messages with special characters', () => {
      const { showSuccess, snackbarText } = useSnackbar()
      const specialMessage = 'Test <>&"\'\\n\\t'

      showSuccess(specialMessage)

      expect(snackbarText.value).toBe(specialMessage)
    })

    it('should handle zero timeout', () => {
      const { showMessage, snackbarTimeout } = useSnackbar()

      showMessage('Test', 'success', 0)

      expect(snackbarTimeout.value).toBe(0)
    })

    it('should handle very large timeout', () => {
      const { showMessage, snackbarTimeout } = useSnackbar()

      showMessage('Test', 'success', 999999)

      expect(snackbarTimeout.value).toBe(999999)
    })

    it('should overwrite previous message when called multiple times', () => {
      const { showSuccess, snackbarText } = useSnackbar()

      showSuccess('First message')
      expect(snackbarText.value).toBe('First message')

      showSuccess('Second message')
      expect(snackbarText.value).toBe('Second message')
    })

    it('should update all parameters when changing message type', () => {
      const { showSuccess, showError, snackbarColor, snackbarTimeout } = useSnackbar()

      showSuccess('Success')
      expect(snackbarColor.value).toBe('success')
      expect(snackbarTimeout.value).toBe(3000)

      showError('Error')
      expect(snackbarColor.value).toBe('error')
      expect(snackbarTimeout.value).toBe(5000)
    })
  })

  describe('Message Chaining', () => {
    it('should support rapid successive calls', () => {
      const { showSuccess, showError, showWarning, snackbar } = useSnackbar()

      showSuccess('1')
      showError('2')
      showWarning('3')

      expect(snackbar.value).toBe(true)
    })

    it('should preserve last message when called rapidly', () => {
      const { showSuccess, snackbarText } = useSnackbar()

      for (let i = 0; i < 10; i++) {
        showSuccess(`Message ${i}`)
      }

      expect(snackbarText.value).toBe('Message 9')
    })
  })

  describe('State Persistence', () => {
    it('should maintain state when snackbar is closed', () => {
      const { showSuccess, snackbar, snackbarText, snackbarColor } = useSnackbar()

      showSuccess('Test')
      expect(snackbar.value).toBe(true)

      // Simulate closing the snackbar
      snackbar.value = false

      // Text and color should still be available
      expect(snackbarText.value).toBe('Test')
      expect(snackbarColor.value).toBe('success')
    })

    it('should allow manual snackbar control', () => {
      const { showSuccess, snackbar } = useSnackbar()

      showSuccess('Test')
      expect(snackbar.value).toBe(true)

      // Manually close
      snackbar.value = false
      expect(snackbar.value).toBe(false)

      // Manually open again
      snackbar.value = true
      expect(snackbar.value).toBe(true)
    })
  })
})
