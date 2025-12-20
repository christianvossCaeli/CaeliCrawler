<template>
  <div class="password-strength-indicator">
    <!-- Strength Bar -->
    <div class="strength-bar-container mb-1">
      <div
        class="strength-bar"
        :style="{ width: `${strengthPercentage}%` }"
        :class="strengthClass"
      />
    </div>

    <!-- Strength Label -->
    <div class="d-flex justify-space-between align-center mb-2">
      <span class="text-caption" :class="`text-${strengthColor}`">
        {{ strengthLabel }}
      </span>
      <v-progress-circular
        v-if="loading"
        size="16"
        width="2"
        indeterminate
        color="grey"
      />
    </div>

    <!-- Requirements -->
    <div v-if="showRequirements && requirements.length > 0" class="requirements">
      <div
        v-for="(req, index) in requirements"
        :key="index"
        class="requirement text-caption d-flex align-center"
        :class="req.met ? 'text-success' : 'text-medium-emphasis'"
      >
        <v-icon size="14" class="mr-1">
          {{ req.met ? 'mdi-check' : 'mdi-circle-small' }}
        </v-icon>
        {{ req.text }}
      </div>
    </div>

    <!-- Errors -->
    <div v-if="errors.length > 0" class="mt-2">
      <div
        v-for="(error, index) in errors"
        :key="index"
        class="text-caption text-error d-flex align-center"
      >
        <v-icon size="14" class="mr-1" color="error">mdi-alert-circle</v-icon>
        {{ error }}
      </div>
    </div>

    <!-- Suggestions -->
    <div v-if="suggestions.length > 0" class="mt-2">
      <div
        v-for="(suggestion, index) in suggestions"
        :key="index"
        class="text-caption text-info d-flex align-center"
      >
        <v-icon size="14" class="mr-1" color="info">mdi-lightbulb-outline</v-icon>
        {{ suggestion }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { authApi } from '@/services/api'

const { t } = useI18n()

const props = withDefaults(
  defineProps<{
    password: string
    showRequirements?: boolean
    debounceMs?: number
  }>(),
  {
    showRequirements: true,
    debounceMs: 300,
  }
)

const emit = defineEmits<{
  (e: 'update:isValid', value: boolean): void
  (e: 'update:score', value: number): void
}>()

// State
const loading = ref(false)
const score = ref(0)
const isValid = ref(false)
const errors = ref<string[]>([])
const suggestions = ref<string[]>([])

// Local validation for immediate feedback
const localRequirements = computed(() => [
  { text: t('password.requirements.minLength'), met: props.password.length >= 8 },
  { text: t('password.requirements.uppercase'), met: /[A-Z]/.test(props.password) },
  { text: t('password.requirements.lowercase'), met: /[a-z]/.test(props.password) },
  { text: t('password.requirements.digit'), met: /[0-9]/.test(props.password) },
])

const requirements = computed(() => localRequirements.value)

// Calculate local score for immediate feedback
const localScore = computed(() => {
  if (!props.password) return 0
  const metCount = localRequirements.value.filter(r => r.met).length
  return (metCount / localRequirements.value.length) * 100
})

const strengthPercentage = computed(() => {
  // Use API score if available, otherwise use local score
  return score.value > 0 ? score.value : localScore.value
})

const strengthClass = computed(() => {
  const pct = strengthPercentage.value
  if (pct >= 80) return 'strength-strong'
  if (pct >= 60) return 'strength-good'
  if (pct >= 40) return 'strength-fair'
  return 'strength-weak'
})

const strengthColor = computed(() => {
  const pct = strengthPercentage.value
  if (pct >= 80) return 'success'
  if (pct >= 60) return 'info'
  if (pct >= 40) return 'warning'
  return 'error'
})

const strengthLabel = computed(() => {
  if (!props.password) return ''
  const pct = strengthPercentage.value
  if (pct >= 80) return t('password.strength.strong')
  if (pct >= 60) return t('password.strength.good')
  if (pct >= 40) return t('password.strength.fair')
  return t('password.strength.weak')
})

// Debounced API check
let debounceTimeout: ReturnType<typeof setTimeout>

async function checkPasswordStrength() {
  if (!props.password || props.password.length < 1) {
    score.value = 0
    isValid.value = false
    errors.value = []
    suggestions.value = []
    emit('update:isValid', false)
    emit('update:score', 0)
    return
  }

  loading.value = true
  try {
    const response = await authApi.checkPasswordStrength(props.password)
    score.value = response.data.score
    isValid.value = response.data.is_valid
    errors.value = response.data.errors || []
    suggestions.value = response.data.suggestions || []
    emit('update:isValid', response.data.is_valid)
    emit('update:score', response.data.score)
  } catch {
    // Fallback to local validation if API fails
    const allMet = localRequirements.value.every(r => r.met)
    isValid.value = allMet
    emit('update:isValid', allMet)
    emit('update:score', localScore.value)
  } finally {
    loading.value = false
  }
}

// Watch password changes with debounce
watch(
  () => props.password,
  () => {
    clearTimeout(debounceTimeout)
    // Immediate local validation
    const allMet = localRequirements.value.every(r => r.met)
    emit('update:isValid', allMet)

    // Debounced API check
    debounceTimeout = setTimeout(checkPasswordStrength, props.debounceMs)
  }
)
</script>

<style scoped>
.password-strength-indicator {
  width: 100%;
}

.strength-bar-container {
  height: 4px;
  background-color: rgba(var(--v-theme-on-surface), 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.strength-bar {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease, background-color 0.3s ease;
}

.strength-weak {
  background-color: rgb(var(--v-theme-error));
}

.strength-fair {
  background-color: rgb(var(--v-theme-warning));
}

.strength-good {
  background-color: rgb(var(--v-theme-info));
}

.strength-strong {
  background-color: rgb(var(--v-theme-success));
}

.requirements {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.requirement {
  line-height: 1.4;
}
</style>
