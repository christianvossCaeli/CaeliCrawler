<template>
  <div
    class="documents-skeleton"
    role="status"
    aria-busy="true"
    :aria-label="$t('documents.messages.loadingDocuments')"
  >
    <!-- Header -->
    <div class="d-flex align-center justify-space-between mb-6">
      <div>
        <v-skeleton-loader type="heading" width="220px" class="mb-2"></v-skeleton-loader>
        <v-skeleton-loader type="text" width="300px"></v-skeleton-loader>
      </div>
      <div class="d-flex gap-2">
        <v-skeleton-loader type="button" width="120px"></v-skeleton-loader>
        <v-skeleton-loader type="button" width="140px"></v-skeleton-loader>
      </div>
    </div>

    <!-- Statistics Bar -->
    <v-row class="mb-4">
      <v-col v-for="i in 6" :key="`stat-${i}`" cols="6" sm="4" md="2">
        <v-card variant="outlined">
          <v-card-text class="text-center py-3">
            <v-skeleton-loader type="text" width="40px" class="mx-auto mb-1"></v-skeleton-loader>
            <v-skeleton-loader type="text" width="60px" class="mx-auto"></v-skeleton-loader>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Filter Card -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row align="center">
          <v-col cols="12" md="3">
            <v-skeleton-loader type="text" width="100%"></v-skeleton-loader>
          </v-col>
          <v-col cols="6" md="2">
            <v-skeleton-loader type="text" width="100%"></v-skeleton-loader>
          </v-col>
          <v-col cols="6" md="2">
            <v-skeleton-loader type="text" width="100%"></v-skeleton-loader>
          </v-col>
          <v-col cols="6" md="2">
            <v-skeleton-loader type="text" width="100%"></v-skeleton-loader>
          </v-col>
          <v-col cols="6" md="3">
            <div class="d-flex gap-2 align-center">
              <v-skeleton-loader type="text" width="45%"></v-skeleton-loader>
              <v-skeleton-loader type="text" width="45%"></v-skeleton-loader>
            </div>
          </v-col>
        </v-row>
        <div class="d-flex justify-end gap-2 mt-3">
          <v-skeleton-loader type="button" width="100px"></v-skeleton-loader>
          <v-skeleton-loader type="button" width="120px"></v-skeleton-loader>
        </div>
      </v-card-text>
    </v-card>

    <!-- Data Table -->
    <v-card>
      <v-skeleton-loader type="table-heading"></v-skeleton-loader>
      <v-skeleton-loader
        v-for="i in 10"
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
 * DocumentsSkeleton - Loading skeleton for the Documents view
 *
 * Displays a placeholder UI while document data is being loaded,
 * providing better UX than a simple loading spinner.
 */
</script>

<style scoped>
.documents-skeleton {
  min-height: 80vh;
}
</style>
