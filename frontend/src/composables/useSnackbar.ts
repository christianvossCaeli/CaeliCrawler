import { ref } from 'vue'

// Global state for snackbar
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')
const snackbarTimeout = ref(3000)

export function useSnackbar() {
  const showMessage = (text: string, color: 'success' | 'error' | 'warning' | 'info' = 'success', timeout = 3000) => {
    snackbarText.value = text
    snackbarColor.value = color
    snackbarTimeout.value = timeout
    snackbar.value = true
  }

  const showSuccess = (text: string) => showMessage(text, 'success')
  const showError = (text: string) => showMessage(text, 'error', 5000)
  const showWarning = (text: string) => showMessage(text, 'warning', 4000)
  const showInfo = (text: string) => showMessage(text, 'info')

  return {
    // State (for v-model binding)
    snackbar,
    snackbarText,
    snackbarColor,
    snackbarTimeout,
    // Methods
    showMessage,
    showSuccess,
    showError,
    showWarning,
    showInfo,
  }
}
