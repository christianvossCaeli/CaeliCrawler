<script setup lang="ts">
/**
 * ARIA Live Region Component
 *
 * Provides hidden live regions for screen reader announcements.
 * Should be placed once in the app (typically in App.vue).
 *
 * Usage:
 *   <!-- In App.vue -->
 *   <template>
 *     <AriaLiveRegion />
 *     <router-view />
 *   </template>
 *
 * Then use the useAnnouncer composable anywhere:
 *   const { announcePolite } = useAnnouncer()
 *   announcePolite('Data loaded successfully')
 */

import { useAnnouncer } from '@/composables/useAnnouncer'

const { state } = useAnnouncer()
</script>

<template>
  <!--
    These are visually hidden but accessible to screen readers.
    The aria-live attribute ensures changes are announced.
  -->

  <!-- Polite live region - won't interrupt current speech -->
  <div
    id="aria-live-polite"
    role="status"
    aria-live="polite"
    aria-atomic="true"
    class="sr-only"
  >
    {{ state.politeMessage }}
  </div>

  <!-- Assertive live region - interrupts current speech -->
  <div
    id="aria-live-assertive"
    role="alert"
    aria-live="assertive"
    aria-atomic="true"
    class="sr-only"
  >
    {{ state.assertiveMessage }}
  </div>
</template>

<style scoped>
/*
 * Screen-reader-only class.
 * Visually hidden but accessible to assistive technologies.
 */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
