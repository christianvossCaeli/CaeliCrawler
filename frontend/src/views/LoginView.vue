<template>
  <LoginLayout
    app-title="CAELI"
    app-subtitle="CRAWLER"
    :app-description="t('auth.login.subtitle')"
  >
    <v-form ref="formRef" @submit.prevent="handleLogin">
      <!-- Email Field -->
      <div class="input-group">
        <label for="email-input" class="input-label">{{ t('auth.login.email') }}</label>
        <div class="input-wrapper">
          <v-icon class="input-icon" size="18" aria-hidden="true">mdi-email-outline</v-icon>
          <input
            id="email-input"
            v-model="email"
            type="email"
            class="custom-input"
            data-testid="email-input"
            :placeholder="t('auth.login.emailPlaceholder')"
            :disabled="isLoading"
            :aria-busy="isLoading"
            :aria-invalid="!!errorMessage"
            :aria-describedby="errorMessage ? 'login-error' : undefined"
            autocomplete="email"
            @keyup.enter="handleLogin"
          />
        </div>
      </div>

      <!-- Password Field -->
      <div class="input-group">
        <label for="password-input" class="input-label">{{ t('auth.login.password') }}</label>
        <div class="input-wrapper">
          <v-icon class="input-icon" size="18" aria-hidden="true">mdi-lock-outline</v-icon>
          <input
            id="password-input"
            v-model="password"
            :type="showPassword ? 'text' : 'password'"
            class="custom-input"
            data-testid="password-input"
            :placeholder="t('auth.login.passwordPlaceholder')"
            :disabled="isLoading"
            :aria-busy="isLoading"
            :aria-invalid="!!errorMessage"
            :aria-describedby="errorMessage ? 'login-error' : undefined"
            autocomplete="current-password"
            @keyup.enter="handleLogin"
          />
          <button
            type="button"
            class="password-toggle"
            :aria-label="showPassword ? t('auth.hidePassword') : t('auth.showPassword')"
            :aria-pressed="showPassword"
            @click="showPassword = !showPassword"
          >
            <v-icon size="18" aria-hidden="true">
              {{ showPassword ? 'mdi-eye-off' : 'mdi-eye' }}
            </v-icon>
          </button>
        </div>
      </div>

      <!-- Error Alert -->
      <Transition name="fade">
        <div v-if="errorMessage" id="login-error" class="error-alert" role="alert" aria-live="polite">
          <v-icon size="16" class="mr-2" aria-hidden="true">mdi-alert-circle</v-icon>
          {{ errorMessage }}
          <button type="button" class="error-close" :aria-label="t('common.close')" @click="errorMessage = null">
            <v-icon size="14" aria-hidden="true">mdi-close</v-icon>
          </button>
        </div>
      </Transition>

      <!-- Login Button -->
      <button
        type="submit"
        class="login-button"
        data-testid="login-button"
        :class="{ loading: isLoading }"
        :disabled="!isFormValid || isLoading"
        :aria-busy="isLoading"
      >
        <span v-if="!isLoading" class="button-content">
          {{ t('auth.login.submit') }}
        </span>
        <span v-else class="button-loading" aria-live="polite">
          <div class="spinner" role="status" :aria-label="t('common.loading')"></div>
        </span>
      </button>
    </v-form>
  </LoginLayout>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { LoginLayout } from '@christianvosscaeli/login-vue'
import '@christianvosscaeli/login-styles'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const { t } = useI18n()

// Form state
const email = ref('')
const password = ref('')
const showPassword = ref(false)
const isLoading = ref(false)
const errorMessage = ref<string | null>(null)

// Email validation regex
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const isEmailValid = computed(() => emailRegex.test(email.value))

const isFormValid = computed(() => {
  return isEmailValid.value && password.value.length > 0
})

// Login handler
async function handleLogin() {
  if (!isFormValid.value) return

  isLoading.value = true
  errorMessage.value = null

  try {
    const success = await auth.login(email.value, password.value)

    if (success) {
      const redirectPath = (route.query.redirect as string) || '/'
      await router.push(redirectPath)
    } else {
      errorMessage.value = auth.error || t('auth.errors.invalidCredentials')
    }
  } catch (err) {
    console.error('Login error:', err)
    errorMessage.value = t('auth.errors.invalidCredentials')
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
/* Input Styles */
.input-group {
  margin-bottom: 20px;
}

.input-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.8);
  margin-bottom: 8px;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: 16px;
  color: rgba(255, 255, 255, 0.5);
  pointer-events: none;
}

.custom-input {
  width: 100%;
  height: 48px;
  padding: 0 48px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 24px;
  color: white;
  font-size: 14px;
  outline: none;
  transition: all 0.3s ease;
}

.custom-input::placeholder {
  color: rgba(255, 255, 255, 0.4);
}

.custom-input:focus {
  border-color: rgba(222, 238, 198, 0.5);
  background: rgba(255, 255, 255, 0.08);
  box-shadow: 0 0 0 3px rgba(222, 238, 198, 0.1);
}

.custom-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.password-toggle {
  position: absolute;
  right: 12px;
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  transition: all 0.2s ease;
}

.password-toggle:hover {
  color: rgba(255, 255, 255, 0.8);
  background: rgba(255, 255, 255, 0.1);
}

/* Error Alert */
.error-alert {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: rgba(220, 53, 69, 0.2);
  border: 1px solid rgba(220, 53, 69, 0.3);
  border-radius: 12px;
  color: #ff6b7a;
  font-size: 13px;
  margin-bottom: 20px;
}

.error-close {
  margin-left: auto;
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 4px;
  border-radius: 50%;
  transition: background 0.2s ease;
}

.error-close:hover {
  background: rgba(255, 255, 255, 0.1);
}

/* Login Button */
.login-button {
  width: 100%;
  height: 52px;
  background: linear-gradient(135deg, #92a0ff 0%, #7986cb 100%);
  border: none;
  border-radius: 26px;
  color: white;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.login-button:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(146, 160, 255, 0.4);
}

.login-button:not(:disabled):active {
  transform: translateY(0);
}

.login-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.button-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.button-loading {
  display: flex;
  align-items: center;
  justify-content: center;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: all 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
