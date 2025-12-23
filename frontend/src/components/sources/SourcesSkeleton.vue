<template>
  <div
    class="sources-skeleton d-flex w-100"
    role="status"
    aria-busy="true"
    :aria-label="$t('sources.skeleton.loading')"
  >
    <!-- Sidebar Skeleton -->
    <div class="sidebar-skeleton pa-4">
      <v-skeleton-loader type="text" class="mb-4" width="60%"></v-skeleton-loader>
      <v-skeleton-loader
        v-for="i in 5"
        :key="i"
        type="list-item"
        class="mb-2"
      ></v-skeleton-loader>
      <v-divider class="my-4"></v-divider>
      <v-skeleton-loader type="text" class="mb-4" width="50%"></v-skeleton-loader>
      <v-skeleton-loader
        v-for="i in 4"
        :key="`type-${i}`"
        type="list-item"
        class="mb-2"
      ></v-skeleton-loader>
    </div>

    <!-- Main Content Skeleton -->
    <div class="main-skeleton flex-grow-1 pa-4">
      <!-- Header -->
      <div class="d-flex align-center justify-space-between mb-6">
        <div>
          <v-skeleton-loader type="heading" width="200px" class="mb-2"></v-skeleton-loader>
          <v-skeleton-loader type="text" width="300px"></v-skeleton-loader>
        </div>
        <div class="d-flex gap-2">
          <v-skeleton-loader type="button" width="120px"></v-skeleton-loader>
          <v-skeleton-loader type="button" width="100px"></v-skeleton-loader>
        </div>
      </div>

      <!-- Search Card -->
      <v-card class="mb-4">
        <v-card-text class="py-3">
          <v-skeleton-loader type="text@2" width="50%"></v-skeleton-loader>
        </v-card-text>
      </v-card>

      <!-- Table -->
      <v-card>
        <v-skeleton-loader type="table-heading"></v-skeleton-loader>
        <v-skeleton-loader
          v-for="i in 10"
          :key="`row-${i}`"
          type="table-row"
        ></v-skeleton-loader>
      </v-card>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * SourcesSkeleton - Loading skeleton for the Sources view
 *
 * Displays a placeholder UI while the sources data is being loaded,
 * providing better UX than a simple loading spinner.
 */
</script>

<style scoped>
.sources-skeleton {
  min-height: 100vh;
}

.sidebar-skeleton {
  width: 280px;
  background: rgb(var(--v-theme-surface));
  border-right: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.main-skeleton {
  background: rgb(var(--v-theme-background));
}
</style>
