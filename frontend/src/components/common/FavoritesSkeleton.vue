<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-skeleton-loader type="text" width="150" />
      <v-spacer />
      <v-skeleton-loader type="chip" width="80" />
    </v-card-title>

    <v-card-text class="pa-0">
      <!-- Table Header Skeleton -->
      <div class="d-flex align-center px-4 py-3 bg-grey-lighten-4">
        <v-skeleton-loader type="text" width="200" class="flex-grow-1" />
        <v-skeleton-loader type="text" width="100" class="mx-4" />
        <v-skeleton-loader type="text" width="120" class="mx-4" />
        <v-skeleton-loader type="text" width="80" />
      </div>

      <v-divider />

      <!-- Table Rows Skeleton -->
      <div
        v-for="i in rowCount"
        :key="i"
        class="d-flex align-center px-4 py-3"
        :class="{ 'border-b': i < rowCount }"
      >
        <!-- Entity Column with Avatar -->
        <div class="d-flex align-center flex-grow-1">
          <v-skeleton-loader type="avatar" class="mr-3" />
          <div>
            <v-skeleton-loader type="text" :width="120 + (i % 3) * 40" class="mb-1" />
            <v-skeleton-loader type="text" width="80" />
          </div>
        </div>

        <!-- Type Column -->
        <v-skeleton-loader type="chip" width="90" class="mx-4" />

        <!-- Date Column -->
        <v-skeleton-loader type="text" width="110" class="mx-4" />

        <!-- Actions Column -->
        <div class="d-flex ga-1">
          <v-skeleton-loader type="button" width="32" height="32" />
          <v-skeleton-loader type="button" width="32" height="32" />
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  /**
   * Number of skeleton rows to display
   * @default 5
   */
  rowCount?: number
}>(), {
  rowCount: 5,
})
</script>

<style scoped>
.border-b {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
