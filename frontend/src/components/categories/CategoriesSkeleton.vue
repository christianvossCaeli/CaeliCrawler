<template>
  <div
    class="categories-skeleton"
    role="status"
    aria-busy="true"
    :aria-label="$t('categories.loading')"
  >
    <!-- Header -->
    <div class="d-flex align-center justify-space-between mb-6">
      <div>
        <v-skeleton-loader type="heading" width="180px" class="mb-2"></v-skeleton-loader>
        <v-skeleton-loader type="text" width="260px"></v-skeleton-loader>
      </div>
      <v-skeleton-loader type="button" width="140px"></v-skeleton-loader>
    </div>

    <!-- Filters Toolbar -->
    <v-card class="mb-4">
      <v-card-text class="py-3">
        <div class="d-flex gap-3 align-center flex-wrap">
          <v-skeleton-loader type="text" width="200px"></v-skeleton-loader>
          <v-skeleton-loader type="chip" width="100px"></v-skeleton-loader>
          <v-skeleton-loader type="chip" width="120px"></v-skeleton-loader>
          <v-skeleton-loader type="chip" width="90px"></v-skeleton-loader>
          <v-spacer></v-spacer>
          <v-skeleton-loader type="button" width="100px"></v-skeleton-loader>
        </div>
      </v-card-text>
    </v-card>

    <!-- Categories Tree/Table -->
    <v-card>
      <!-- Tree Header -->
      <v-card-text class="py-2 border-b">
        <div class="d-flex align-center gap-4">
          <v-skeleton-loader type="text" width="30%"></v-skeleton-loader>
          <v-skeleton-loader type="text" width="15%"></v-skeleton-loader>
          <v-skeleton-loader type="text" width="15%"></v-skeleton-loader>
          <v-skeleton-loader type="text" width="15%"></v-skeleton-loader>
          <v-spacer></v-spacer>
          <v-skeleton-loader type="text" width="100px"></v-skeleton-loader>
        </div>
      </v-card-text>

      <!-- Tree Rows -->
      <v-list>
        <v-list-item v-for="i in 8" :key="`cat-${i}`" class="py-3">
          <template #prepend>
            <v-skeleton-loader type="avatar" width="32px" class="mr-3"></v-skeleton-loader>
          </template>
          <div class="d-flex align-center w-100">
            <div class="flex-grow-1">
              <v-skeleton-loader type="text" :width="`${180 + (i % 3) * 40}px`" class="mb-1"></v-skeleton-loader>
              <v-skeleton-loader type="text" width="100px"></v-skeleton-loader>
            </div>
            <div class="d-flex gap-2 align-center">
              <v-skeleton-loader type="chip" width="60px"></v-skeleton-loader>
              <v-skeleton-loader type="chip" width="70px"></v-skeleton-loader>
              <v-skeleton-loader type="avatar" width="32px"></v-skeleton-loader>
              <v-skeleton-loader type="avatar" width="32px"></v-skeleton-loader>
              <v-skeleton-loader type="avatar" width="32px"></v-skeleton-loader>
            </div>
          </div>
        </v-list-item>
      </v-list>
    </v-card>
  </div>
</template>

<script setup lang="ts">
/**
 * CategoriesSkeleton - Loading skeleton for the Categories view
 *
 * Displays a placeholder UI while categories data is being loaded,
 * providing better UX than a simple loading spinner.
 */
</script>

<style scoped>
.categories-skeleton {
  min-height: 80vh;
}
</style>
