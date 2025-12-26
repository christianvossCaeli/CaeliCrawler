<template>
  <div
    class="entities-skeleton"
    role="status"
    aria-busy="true"
    :aria-label="$t('entities.loading')"
  >
    <!-- Header -->
    <div class="d-flex align-center justify-space-between mb-6">
      <div>
        <v-skeleton-loader type="heading" width="250px" class="mb-2"></v-skeleton-loader>
        <v-skeleton-loader type="text" width="350px"></v-skeleton-loader>
      </div>
      <div class="d-flex gap-2">
        <v-skeleton-loader type="button" width="140px"></v-skeleton-loader>
        <v-skeleton-loader type="button" width="100px"></v-skeleton-loader>
      </div>
    </div>

    <!-- Filter Bar -->
    <v-card class="mb-4">
      <v-card-text class="py-3">
        <div class="d-flex gap-3 align-center">
          <v-skeleton-loader type="text" width="200px"></v-skeleton-loader>
          <v-skeleton-loader type="chip" width="80px"></v-skeleton-loader>
          <v-skeleton-loader type="chip" width="100px"></v-skeleton-loader>
          <v-skeleton-loader type="chip" width="90px"></v-skeleton-loader>
          <v-spacer></v-spacer>
          <v-skeleton-loader type="button" width="40px"></v-skeleton-loader>
          <v-skeleton-loader type="button" width="40px"></v-skeleton-loader>
        </div>
      </v-card-text>
    </v-card>

    <!-- Entity Type Tabs -->
    <div class="mb-4">
      <v-skeleton-loader type="chip, chip, chip, chip" class="d-flex gap-2"></v-skeleton-loader>
    </div>

    <!-- Table/Grid -->
    <v-card>
      <v-skeleton-loader type="table-heading"></v-skeleton-loader>
      <v-skeleton-loader
        v-for="i in 12"
        :key="`row-${i}`"
        type="table-row"
      ></v-skeleton-loader>
    </v-card>

    <!-- Pagination -->
    <div class="d-flex justify-center mt-4">
      <v-skeleton-loader type="button, button, button, button, button" width="300px"></v-skeleton-loader>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * EntitiesSkeleton - Loading skeleton for the Entities view
 *
 * Displays a placeholder UI while entity data is being loaded,
 * providing better UX than a simple loading spinner.
 */
</script>

<style scoped>
.entities-skeleton {
  min-height: 80vh;
}
</style>
