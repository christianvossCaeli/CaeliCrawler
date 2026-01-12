<template>
  <div class="page-info-box">
    <Transition name="info-box">
      <v-alert
        v-if="!isHidden"
        :id="contentId"
        type="info"
        variant="tonal"
        density="compact"
        class="mb-4"
        closable
        role="complementary"
        :aria-label="title"
        @click:close="hide"
      >
        <template #prepend>
          <v-icon :aria-hidden="true">{{ icon }}</v-icon>
        </template>
        <div>
          <strong v-if="title">{{ title }}</strong>
          <div :class="['text-caption', { 'mt-1': title }]">
            <slot />
          </div>
        </div>
      </v-alert>
    </Transition>
    <v-btn
      v-if="isHidden"
      variant="text"
      size="x-small"
      color="info"
      class="mb-2"
      prepend-icon="mdi-information-outline"
      :aria-expanded="false"
      :aria-controls="contentId"
      @click="show"
    >
      {{ $t('common.infoBox.showInfo') }}
    </v-btn>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import type { InfoBoxStorageKey } from '@/config/infoBox'

/**
 * PageInfoBox - Dismissible info box for page-level guidance
 *
 * Provides contextual help that users can dismiss.
 * Dismissal state is persisted in localStorage.
 */
interface Props {
  /** LocalStorage key for persisting hidden state */
  storageKey: InfoBoxStorageKey
  /** Title displayed in bold */
  title: string
  /** MDI icon name (default: mdi-information-outline) */
  icon?: string
}

const props = withDefaults(defineProps<Props>(), {
  icon: 'mdi-information-outline',
})

const isHidden = ref(false)

// Generate unique ID for accessibility
const contentId = computed(() => `info-box-${props.storageKey.replace(/\./g, '-')}`)

onMounted(() => {
  try {
    isHidden.value = localStorage.getItem(props.storageKey) === 'true'
  } catch {
    // localStorage not available (e.g., private browsing)
    isHidden.value = false
  }
})

function hide() {
  isHidden.value = true
  try {
    localStorage.setItem(props.storageKey, 'true')
  } catch {
    // Ignore storage errors
  }
}

function show() {
  isHidden.value = false
  try {
    localStorage.removeItem(props.storageKey)
  } catch {
    // Ignore storage errors
  }
}
</script>

<style scoped>
/* Transition animations */
.info-box-enter-active,
.info-box-leave-active {
  transition: all 0.2s ease-out;
}

.info-box-enter-from,
.info-box-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
