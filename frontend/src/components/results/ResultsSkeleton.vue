<template>
  <div
    class="results-skeleton"
    role="status"
    aria-busy="true"
    :aria-label="$t('results.loading.title')"
  >
    <!-- Header -->
    <div class="d-flex align-center justify-space-between mb-6">
      <div>
        <v-skeleton-loader type="heading" width="200px" class="mb-2"></v-skeleton-loader>
        <v-skeleton-loader type="text" width="280px"></v-skeleton-loader>
      </div>
      <div class="d-flex gap-2">
        <v-skeleton-loader type="button" width="130px"></v-skeleton-loader>
        <v-skeleton-loader type="button" width="110px"></v-skeleton-loader>
        <v-skeleton-loader type="button" width="100px"></v-skeleton-loader>
      </div>
    </div>

    <!-- Statistics Bar -->
    <v-row class="mb-4">
      <v-col v-for="i in 4" :key="`stat-${i}`" cols="6" sm="3">
        <v-card variant="outlined">
          <v-card-text class="text-center py-3">
            <v-skeleton-loader type="text" width="50px" class="mx-auto mb-1"></v-skeleton-loader>
            <v-skeleton-loader type="text" width="70px" class="mx-auto"></v-skeleton-loader>
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
            <v-skeleton-loader type="text" width="100%"></v-skeleton-loader>
          </v-col>
        </v-row>
        <v-row align="center" class="mt-2">
          <v-col cols="12" md="3">
            <v-skeleton-loader type="text" width="100%"></v-skeleton-loader>
          </v-col>
          <v-col cols="6" md="2">
            <v-skeleton-loader type="text" width="100%"></v-skeleton-loader>
          </v-col>
          <v-col cols="auto">
            <v-skeleton-loader type="chip" width="80px"></v-skeleton-loader>
          </v-col>
          <v-spacer></v-spacer>
          <v-col cols="auto">
            <v-skeleton-loader type="button" width="100px"></v-skeleton-loader>
          </v-col>
        </v-row>
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
 * ResultsSkeleton - Loading skeleton for the Results view
 *
 * Displays a placeholder UI while results data is being loaded,
 * providing better UX than a simple loading spinner.
 */
</script>

<style scoped>
.results-skeleton {
  min-height: 80vh;
}
</style>
