<template>
  <v-card :id="sectionId" class="mb-4">
    <v-card-title :class="`text-h5 bg-${color}`">
      <v-icon class="mr-2">{{ icon }}</v-icon>
      {{ title }}
    </v-card-title>
    <v-card-text class="pt-4">
      <slot></slot>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
defineProps<{
  sectionId: string
  title: string
  icon: string
  color?: string
}>()
</script>
