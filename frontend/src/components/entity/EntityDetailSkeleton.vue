<template>
  <div
    class="entity-detail-skeleton"
    role="status"
    aria-busy="true"
    :aria-label="$t('entities.loadingDetail')"
  >
    <!-- Breadcrumbs -->
    <div class="mb-4">
      <v-skeleton-loader type="text" width="300px"></v-skeleton-loader>
    </div>

    <!-- Entity Header -->
    <v-card class="mb-6">
      <v-card-text>
        <div class="d-flex align-center gap-4">
          <v-skeleton-loader type="avatar" width="64px" height="64px"></v-skeleton-loader>
          <div class="flex-grow-1">
            <v-skeleton-loader type="heading" width="300px" class="mb-2"></v-skeleton-loader>
            <v-skeleton-loader type="text" width="200px" class="mb-2"></v-skeleton-loader>
            <div class="d-flex gap-2">
              <v-skeleton-loader type="chip" width="80px"></v-skeleton-loader>
              <v-skeleton-loader type="chip" width="100px"></v-skeleton-loader>
              <v-skeleton-loader type="chip" width="70px"></v-skeleton-loader>
            </div>
          </div>
          <div class="d-flex gap-2">
            <v-skeleton-loader type="button" width="40px"></v-skeleton-loader>
            <v-skeleton-loader type="button" width="40px"></v-skeleton-loader>
            <v-skeleton-loader type="button" width="100px"></v-skeleton-loader>
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- Tabs -->
    <div class="mb-4">
      <v-skeleton-loader type="chip, chip, chip, chip, chip, chip" class="d-flex gap-2"></v-skeleton-loader>
    </div>

    <!-- Tab Content -->
    <v-card>
      <v-card-text>
        <!-- Facets Grid Skeleton -->
        <v-row>
          <v-col v-for="i in 6" :key="i" cols="12" md="6" lg="4">
            <v-card variant="outlined" class="pa-4">
              <div class="d-flex align-center mb-3">
                <v-skeleton-loader type="avatar" width="32px" height="32px" class="mr-2"></v-skeleton-loader>
                <v-skeleton-loader type="text" width="120px"></v-skeleton-loader>
              </div>
              <v-skeleton-loader type="text" width="80%" class="mb-2"></v-skeleton-loader>
              <v-skeleton-loader type="text" width="60%"></v-skeleton-loader>
              <v-divider class="my-3"></v-divider>
              <v-skeleton-loader type="text" width="40%"></v-skeleton-loader>
            </v-card>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
/**
 * EntityDetailSkeleton - Loading skeleton for the Entity Detail view
 *
 * Displays a placeholder UI while entity details are being loaded,
 * providing better UX than a simple loading spinner.
 */
</script>

<style scoped>
.entity-detail-skeleton {
  min-height: 80vh;
}
</style>
