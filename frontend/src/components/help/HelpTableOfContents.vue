<template>
  <v-card class="position-sticky" style="top: 80px;">
    <v-card-title class="text-subtitle-1">Inhalt</v-card-title>
    <v-list density="compact" nav>
      <v-list-item
        v-for="section in sections"
        :key="section.id"
        :class="{ 'v-list-item--active': activeSection === section.id }"
        @click="$emit('navigate', section.id)"
      >
        <template v-slot:prepend>
          <v-icon size="small">{{ section.icon }}</v-icon>
        </template>
        <v-list-item-title class="text-body-2">{{ section.title }}</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-card>
</template>

<script setup lang="ts">
import type { HelpSection } from './helpSections'

defineProps<{
  sections: HelpSection[]
  activeSection: string
}>()

defineEmits<{
  (e: 'navigate', sectionId: string): void
}>()
</script>
