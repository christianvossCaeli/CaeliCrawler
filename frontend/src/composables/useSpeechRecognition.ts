import { ref, onMounted, onUnmounted } from 'vue'

// TypeScript declarations for Web Speech API
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList
  resultIndex: number
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string
  message?: string
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean
  interimResults: boolean
  lang: string
  start(): void
  stop(): void
  abort(): void
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null
  onend: (() => void) | null
  onstart: (() => void) | null
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognition
    webkitSpeechRecognition: new () => SpeechRecognition
  }
}

export function useSpeechRecognition() {
  const isListening = ref(false)
  const isSupported = ref(false)
  const hasMicrophone = ref(false)
  const transcript = ref('')
  const interimTranscript = ref('')
  const error = ref<string | null>(null)

  let recognition: SpeechRecognition | null = null

  // Check if Speech Recognition is supported
  const checkSupport = (): boolean => {
    return !!(window.SpeechRecognition || window.webkitSpeechRecognition)
  }

  // Check if microphone is available
  const checkMicrophoneAvailability = async (): Promise<boolean> => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return false
    }

    try {
      // Check if any audio input devices exist
      const devices = await navigator.mediaDevices.enumerateDevices()
      const hasAudioInput = devices.some(device => device.kind === 'audioinput')

      if (!hasAudioInput) {
        return false
      }

      // Try to get permission (this will prompt user if not already granted)
      // We immediately stop the stream since we just want to check availability
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      stream.getTracks().forEach(track => track.stop())

      return true
    } catch {
      // Permission denied or no microphone
      return false
    }
  }

  // Initialize Speech Recognition
  const initRecognition = () => {
    if (!checkSupport()) {
      isSupported.value = false
      return
    }

    isSupported.value = true
    const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition
    recognition = new SpeechRecognitionAPI()

    // Configuration
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'de-DE'

    // Event handlers
    recognition.onstart = () => {
      isListening.value = true
      error.value = null
    }

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let finalTranscript = ''
      let interim = ''

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        if (result.isFinal) {
          finalTranscript += result[0].transcript
        } else {
          interim += result[0].transcript
        }
      }

      if (finalTranscript) {
        transcript.value = (transcript.value + ' ' + finalTranscript).trim()
      }
      interimTranscript.value = interim
    }

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      switch (event.error) {
        case 'no-speech':
          error.value = 'Keine Sprache erkannt. Bitte erneut versuchen.'
          break
        case 'audio-capture':
          error.value = 'Mikrofon nicht verfügbar.'
          hasMicrophone.value = false
          break
        case 'not-allowed':
          error.value = 'Mikrofon-Zugriff wurde verweigert.'
          hasMicrophone.value = false
          break
        case 'network':
          error.value = 'Netzwerkfehler bei der Spracherkennung.'
          break
        case 'aborted':
          // User aborted, no error message needed
          break
        default:
          error.value = 'Fehler bei der Spracherkennung.'
      }
      isListening.value = false
    }

    recognition.onend = () => {
      isListening.value = false
      interimTranscript.value = ''
    }
  }

  // Start listening
  const startListening = () => {
    if (!recognition || !isSupported.value) {
      error.value = 'Spracherkennung wird nicht unterstützt.'
      return
    }

    if (isListening.value) {
      return
    }

    // Clear previous transcript when starting new session
    transcript.value = ''
    interimTranscript.value = ''
    error.value = null

    try {
      recognition.start()
    } catch (e) {
      // Recognition might already be running
      error.value = 'Spracherkennung konnte nicht gestartet werden.'
    }
  }

  // Stop listening
  const stopListening = () => {
    if (!recognition) return

    try {
      recognition.stop()
    } catch {
      // Ignore errors when stopping
    }
    isListening.value = false
  }

  // Toggle listening
  const toggleListening = () => {
    if (isListening.value) {
      stopListening()
    } else {
      startListening()
    }
  }

  // Clear transcript
  const clearTranscript = () => {
    transcript.value = ''
    interimTranscript.value = ''
  }

  // Initialize on mount
  onMounted(async () => {
    initRecognition()

    if (isSupported.value) {
      // Check microphone availability without prompting initially
      // Just check if devices exist
      if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
        try {
          const devices = await navigator.mediaDevices.enumerateDevices()
          const hasAudioInput = devices.some(device => device.kind === 'audioinput')
          hasMicrophone.value = hasAudioInput && isSupported.value
        } catch {
          hasMicrophone.value = false
        }
      }
    }
  })

  // Cleanup on unmount
  onUnmounted(() => {
    if (recognition && isListening.value) {
      recognition.abort()
    }
  })

  return {
    // State
    isListening,
    isSupported,
    hasMicrophone,
    transcript,
    interimTranscript,
    error,
    // Methods
    startListening,
    stopListening,
    toggleListening,
    clearTranscript,
    checkMicrophoneAvailability,
  }
}
