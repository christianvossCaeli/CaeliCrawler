<template>
  <div class="login-container">
    <!-- Animated Background -->
    <div class="background-layer">
      <div class="gradient-bg"></div>
      <div class="gradient-overlay"></div>

      <!-- Floating Particles -->
      <div class="particles">
        <div
          v-for="i in 20"
          :key="i"
          class="particle"
          :style="getParticleStyle(i)"
        ></div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="content-layer">
      <div class="login-wrapper">
        <!-- Logo Section -->
        <div class="logo-section" :class="{ 'animate-in': isLoaded }">
          <!-- Outer glow rings -->
          <div class="glow-rings">
            <div class="glow-ring ring-1"></div>
            <div class="glow-ring ring-2"></div>
            <div class="glow-ring ring-3"></div>
          </div>

          <!-- Animated Spinner -->
          <AnimatedCaeliSpinner
            :size="70"
            primary-color="#deeec6"
            secondary-color="#92a0ff"
            animation-style="combined"
            :show-glow="true"
            :show-glass-background="true"
          />
        </div>

        <!-- Title Section -->
        <div class="title-section" :class="{ 'animate-in': isLoaded }">
          <h1 class="app-title">CAELI</h1>
          <span class="app-subtitle">CRAWLER</span>
          <p class="app-description">{{ $t('auth.loginSubtitle') }}</p>
        </div>

        <!-- Login Card -->
        <div class="login-card" :class="{ 'animate-in': isLoaded }">
          <v-form @submit.prevent="handleLogin" ref="formRef">
            <!-- Email Field -->
            <div class="input-group">
              <label class="input-label">{{ $t('auth.email') }}</label>
              <div class="input-wrapper">
                <v-icon class="input-icon" size="18">mdi-email-outline</v-icon>
                <input
                  v-model="email"
                  type="email"
                  class="custom-input"
                  data-testid="email-input"
                  :placeholder="$t('auth.enterEmail') || 'E-Mail eingeben'"
                  :disabled="isLoading"
                  autocomplete="email"
                  @keyup.enter="handleLogin"
                />
              </div>
            </div>

            <!-- Password Field -->
            <div class="input-group">
              <label class="input-label">{{ $t('auth.password') }}</label>
              <div class="input-wrapper">
                <v-icon class="input-icon" size="18">mdi-lock-outline</v-icon>
                <input
                  v-model="password"
                  :type="showPassword ? 'text' : 'password'"
                  class="custom-input"
                  data-testid="password-input"
                  :placeholder="$t('auth.enterPassword') || 'Passwort eingeben'"
                  :disabled="isLoading"
                  autocomplete="current-password"
                  @keyup.enter="handleLogin"
                />
                <button
                  type="button"
                  class="password-toggle"
                  @click="showPassword = !showPassword"
                >
                  <v-icon size="18">
                    {{ showPassword ? 'mdi-eye-off' : 'mdi-eye' }}
                  </v-icon>
                </button>
              </div>
            </div>

            <!-- Error Alert -->
            <Transition name="fade">
              <div v-if="errorMessage" class="error-alert">
                <v-icon size="16" class="mr-2">mdi-alert-circle</v-icon>
                {{ errorMessage }}
                <button type="button" class="error-close" @click="errorMessage = null">
                  <v-icon size="14">mdi-close</v-icon>
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
            >
              <span v-if="!isLoading" class="button-content">
                {{ $t('auth.login') }}
              </span>
              <span v-else class="button-loading">
                <div class="spinner"></div>
              </span>
            </button>
          </v-form>
        </div>

        <!-- Footer -->
        <div class="footer" :class="{ 'animate-in': isLoaded }">
          <span>&copy; {{ currentYear }} Caeli Wind</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import AnimatedCaeliSpinner from '@/components/AnimatedCaeliSpinner.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const { t } = useI18n()

// Animation state
const isLoaded = ref(false)

// Form state
const email = ref('')
const password = ref('')
const showPassword = ref(false)
const isLoading = ref(false)
const errorMessage = ref<string | null>(null)

// Computed
const currentYear = computed(() => new Date().getFullYear())

const isFormValid = computed(() => {
  return email.value.length > 0 && password.value.length > 0
})

// Particle style generator
function getParticleStyle(index: number) {
  const size = 2 + Math.random() * 4
  const left = Math.random() * 100
  const delay = Math.random() * 5
  const duration = 5 + Math.random() * 5

  return {
    width: `${size}px`,
    height: `${size}px`,
    left: `${left}%`,
    animationDelay: `${delay}s`,
    animationDuration: `${duration}s`
  }
}

// Login handler
async function handleLogin() {
  if (!isFormValid.value) return

  isLoading.value = true
  errorMessage.value = null

  const success = await auth.login(email.value, password.value)

  if (success) {
    const redirectPath = (route.query.redirect as string) || '/'
    await router.push(redirectPath)
  } else {
    errorMessage.value = auth.error || t('auth.loginFailed')
  }

  isLoading.value = false
}

// Trigger animations on mount
onMounted(() => {
  setTimeout(() => {
    isLoaded.value = true
  }, 100)
})
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  width: 100%;
  position: relative;
  overflow: hidden;
}

/* Background Styles */
.background-layer {
  position: fixed;
  inset: 0;
  z-index: 0;
}

.gradient-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #0a1f1e 0%, #113634 50%, #0d1f1e 100%);
  animation: gradient-shift 8s ease-in-out infinite alternate;
}

.gradient-overlay {
  position: absolute;
  inset: 0;
  background: radial-gradient(
    ellipse at center,
    rgba(146, 160, 255, 0.1) 0%,
    transparent 60%
  );
}

@keyframes gradient-shift {
  0% {
    background: linear-gradient(135deg, #0a1f1e 0%, #113634 50%, #0d1f1e 100%);
  }
  100% {
    background: linear-gradient(225deg, #0a1f1e 0%, #0d2928 50%, #113634 100%);
  }
}

/* Particles */
.particles {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.particle {
  position: absolute;
  bottom: -10px;
  background: radial-gradient(circle, rgba(222, 238, 198, 0.6) 0%, transparent 70%);
  border-radius: 50%;
  animation: float-up linear infinite;
  opacity: 0;
}

@keyframes float-up {
  0% {
    transform: translateY(0) scale(1);
    opacity: 0;
  }
  10% {
    opacity: 0.6;
  }
  90% {
    opacity: 0.3;
  }
  100% {
    transform: translateY(-100vh) scale(0.5);
    opacity: 0;
  }
}

/* Content Layer */
.content-layer {
  position: relative;
  z-index: 1;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.login-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
  max-width: 400px;
  width: 100%;
}

/* Logo Section */
.logo-section {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transform: translateY(-20px) scale(0.9);
  transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.logo-section.animate-in {
  opacity: 1;
  transform: translateY(0) scale(1);
}

/* Glow Rings */
.glow-rings {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.glow-ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid;
  animation: ring-pulse 3s ease-in-out infinite;
}

.ring-1 {
  width: 140px;
  height: 140px;
  border-color: rgba(222, 238, 198, 0.3);
  animation-delay: 0s;
}

.ring-2 {
  width: 170px;
  height: 170px;
  border-color: rgba(222, 238, 198, 0.2);
  animation-delay: 0.3s;
}

.ring-3 {
  width: 200px;
  height: 200px;
  border-color: rgba(146, 160, 255, 0.15);
  animation-delay: 0.6s;
}

@keyframes ring-pulse {
  0%,
  100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.05);
    opacity: 0.7;
  }
}

/* Title Section */
.title-section {
  text-align: center;
  opacity: 0;
  transform: translateY(20px);
  transition: all 0.6s ease-out 0.2s;
}

.title-section.animate-in {
  opacity: 1;
  transform: translateY(0);
}

.app-title {
  font-size: 40px;
  font-weight: 700;
  letter-spacing: 10px;
  margin: 0;
  background: linear-gradient(90deg, #deeec6 0%, #92a0ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.app-subtitle {
  display: block;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 6px;
  color: rgba(255, 255, 255, 0.7);
  margin-top: 4px;
}

.app-description {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 12px;
}

/* Login Card */
.login-card {
  width: 100%;
  padding: 32px;
  background: rgba(20, 41, 40, 0.8);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  opacity: 0;
  transform: translateY(30px);
  transition: all 0.6s ease-out 0.4s;
}

.login-card.animate-in {
  opacity: 1;
  transform: translateY(0);
}

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

/* Footer */
.footer {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  opacity: 0;
  transform: translateY(10px);
  transition: all 0.6s ease-out 0.6s;
}

.footer.animate-in {
  opacity: 1;
  transform: translateY(0);
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

/* Responsive */
@media (max-width: 480px) {
  .login-card {
    padding: 24px;
    border-radius: 20px;
  }

  .app-title {
    font-size: 32px;
    letter-spacing: 8px;
  }

  .app-subtitle {
    font-size: 12px;
    letter-spacing: 5px;
  }
}
</style>
