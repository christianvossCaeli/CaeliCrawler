<template>
  <div class="spinner-container" :style="containerStyle" role="status" aria-live="polite" aria-label="Loading">
    <!-- Glow effect -->
    <div v-if="showGlow" class="spinner-glow" :style="glowStyle"></div>

    <!-- Glass background circle -->
    <div v-if="showGlassBackground" class="glass-circle" :style="glassStyle"></div>

    <!-- Animated SVG Spinner -->
    <svg
      class="caeli-spinner"
      :class="{ 'animate-rotate': animationStyle === 'rotating' || animationStyle === 'combined' }"
      :style="spinnerStyle"
      :width="size"
      :height="size"
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <!-- Top vertical bar -->
      <path
        class="spinner-ray"
        :style="{ animationDelay: '0s' }"
        d="M17.3103 0.134766H14.7295V12.8374H17.3103V0.134766Z"
        :fill="currentColor(0)"
      />
      <!-- Bottom vertical bar -->
      <path
        class="spinner-ray"
        :style="{ animationDelay: '0.1s' }"
        d="M17.3103 26.3135H14.7295V31.5564H17.3103V26.3135Z"
        :fill="currentColor(1)"
      />
      <!-- Left horizontal bar -->
      <path
        class="spinner-ray"
        :style="{ animationDelay: '0.2s' }"
        d="M5.43872 14.5615H0.134766V17.1126H5.43872V14.5615Z"
        :fill="currentColor(2)"
      />
      <!-- Right horizontal bar -->
      <path
        class="spinner-ray"
        :style="{ animationDelay: '0.3s' }"
        d="M31.9221 14.5615H26.6182V17.1126H31.9221V14.5615Z"
        :fill="currentColor(3)"
      />
      <!-- Diagonal rays -->
      <path
        class="spinner-ray"
        :style="{ animationDelay: '0.4s' }"
        d="M29.1461 6.86976L24.5527 9.49121L25.8431 11.7005L30.4365 9.07906L29.1461 6.86976Z"
        :fill="currentColor(4)"
      />
      <path
        class="spinner-ray"
        :style="{ animationDelay: '0.5s' }"
        d="M22.4313 24.2625L20.1963 25.5381L22.8483 30.0786L25.0833 28.803L22.4313 24.2625Z"
        :fill="currentColor(5)"
      />
      <path
        class="spinner-ray"
        :style="{ animationDelay: '0.6s' }"
        d="M9.20085 1.61118L6.96582 2.88672L9.6178 7.42721L11.8528 6.15167L9.20085 1.61118Z"
        :fill="currentColor(6)"
      />
      <path
        class="spinner-ray"
        :style="{ animationDelay: '0.7s' }"
        d="M22.8512 1.58744L20.1992 6.12793L22.4342 7.40347L25.0862 2.86298L22.8512 1.58744Z"
        :fill="currentColor(7)"
      />
      <path
        class="spinner-ray"
        :style="{ animationDelay: '0.8s' }"
        d="M9.61389 24.2632L6.96191 28.8037L9.19694 30.0793L11.8489 25.5388L9.61389 24.2632Z"
        :fill="currentColor(8)"
      />
      <path
        class="spinner-ray"
        :style="{ animationDelay: '0.9s' }"
        d="M2.9027 6.87566L1.6123 9.08496L6.20567 11.7064L7.49606 9.49712L2.9027 6.87566Z"
        :fill="currentColor(9)"
      />
      <!-- Large diagonal rays -->
      <path
        class="spinner-ray"
        :style="{ animationDelay: '1s' }"
        d="M19.2854 16.2334L18.0039 18.4502L24.5538 22.1801L29.128 24.8015L30.4273 22.5847L19.2854 16.2334Z"
        :fill="currentColor(10)"
      />
      <path
        class="spinner-ray"
        :style="{ animationDelay: '1.1s' }"
        d="M6.20432 19.9808L1.6123 22.5847L2.9116 24.8015L14.0357 18.4502L12.7364 16.2334L6.20432 19.9808Z"
        :fill="currentColor(11)"
      />
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  size?: number
  primaryColor?: string
  secondaryColor?: string
  animationStyle?: 'rotating' | 'pulsing' | 'breathing' | 'combined'
  showGlow?: boolean
  showGlassBackground?: boolean
  glowIntensity?: number
}

const props = withDefaults(defineProps<Props>(), {
  size: 60,
  primaryColor: '#deeec6',
  secondaryColor: '#92a0ff',
  animationStyle: 'combined',
  showGlow: true,
  showGlassBackground: true,
  glowIntensity: 0.5
})

const containerStyle = computed(() => ({
  width: `${props.size * 1.8}px`,
  height: `${props.size * 1.8}px`
}))

const glowStyle = computed(() => ({
  width: `${props.size * 1.6}px`,
  height: `${props.size * 1.6}px`,
  background: `radial-gradient(circle, ${props.primaryColor}${Math.round(props.glowIntensity * 80).toString(16).padStart(2, '0')} 0%, transparent 70%)`,
  filter: 'blur(15px)'
}))

const glassStyle = computed(() => ({
  width: `${props.size * 1.4}px`,
  height: `${props.size * 1.4}px`
}))

const spinnerStyle = computed(() => ({
  '--breathing-scale': props.animationStyle === 'breathing' || props.animationStyle === 'combined' ? '1.05' : '1'
}))

// Create gradient colors between primary and secondary
function currentColor(index: number): string {
  const t = index / 12
  // Simple linear interpolation between colors
  const primary = hexToRgb(props.primaryColor)
  const secondary = hexToRgb(props.secondaryColor)

  if (!primary || !secondary) return props.primaryColor

  const r = Math.round(primary.r + (secondary.r - primary.r) * t)
  const g = Math.round(primary.g + (secondary.g - primary.g) * t)
  const b = Math.round(primary.b + (secondary.b - primary.b) * t)

  return `rgb(${r}, ${g}, ${b})`
}

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  return result
    ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
      }
    : null
}
</script>

<style scoped>
.spinner-container {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.spinner-glow {
  position: absolute;
  border-radius: 50%;
  animation: pulse-glow 2s ease-in-out infinite;
}

.glass-circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.caeli-spinner {
  position: relative;
  z-index: 1;
  animation: breathing 2s ease-in-out infinite;
}

.animate-rotate {
  animation: rotate 8s linear infinite, breathing 2s ease-in-out infinite;
}

.spinner-ray {
  transform-origin: center;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes breathing {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(var(--breathing-scale, 1.05));
  }
}

@keyframes pulse-glow {
  0%,
  100% {
    opacity: 0.5;
    transform: scale(1);
  }
  50% {
    opacity: 1;
    transform: scale(1.1);
  }
}

/* Respect prefers-reduced-motion */
@media (prefers-reduced-motion: reduce) {
  .caeli-spinner,
  .animate-rotate,
  .spinner-glow {
    animation: none !important;
  }

  .caeli-spinner {
    opacity: 0.8;
  }

  .spinner-glow {
    opacity: 0.3;
    transform: scale(1);
  }
}
</style>
