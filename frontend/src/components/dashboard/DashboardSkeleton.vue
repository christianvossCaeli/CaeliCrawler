<template>
  <div
    class="dashboard-skeleton"
    role="status"
    aria-busy="true"
    :aria-label="$t('dashboard.loading')"
  >
    <!-- Header -->
    <div class="d-flex align-center justify-space-between mb-6">
      <div>
        <v-skeleton-loader type="heading" width="200px" class="mb-2"></v-skeleton-loader>
        <v-skeleton-loader type="text" width="300px"></v-skeleton-loader>
      </div>
      <v-skeleton-loader type="button" width="120px"></v-skeleton-loader>
    </div>

    <!-- Stats Cards Row -->
    <v-row class="mb-6">
      <v-col v-for="i in 4" :key="`stat-${i}`" cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="pa-4">
            <div class="d-flex align-center">
              <v-skeleton-loader type="avatar" width="48px" height="48px" class="mr-3"></v-skeleton-loader>
              <div class="flex-grow-1">
                <v-skeleton-loader type="text" width="60px" class="mb-1"></v-skeleton-loader>
                <v-skeleton-loader type="heading" width="80px"></v-skeleton-loader>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Charts Row -->
    <v-row class="mb-6">
      <v-col cols="12" md="8">
        <v-card>
          <v-card-title>
            <v-skeleton-loader type="text" width="150px"></v-skeleton-loader>
          </v-card-title>
          <v-card-text>
            <v-skeleton-loader type="image" height="300px"></v-skeleton-loader>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>
            <v-skeleton-loader type="text" width="120px"></v-skeleton-loader>
          </v-card-title>
          <v-card-text>
            <v-skeleton-loader type="image" height="300px"></v-skeleton-loader>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Activity & Quick Actions Row -->
    <v-row>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-skeleton-loader type="text" width="140px"></v-skeleton-loader>
          </v-card-title>
          <v-card-text>
            <v-skeleton-loader
              v-for="i in 5"
              :key="`activity-${i}`"
              type="list-item-two-line"
              class="mb-2"
            ></v-skeleton-loader>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-skeleton-loader type="text" width="130px"></v-skeleton-loader>
          </v-card-title>
          <v-card-text>
            <v-row>
              <v-col v-for="i in 4" :key="`action-${i}`" cols="6">
                <v-skeleton-loader type="button" height="80px"></v-skeleton-loader>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
/**
 * DashboardSkeleton - Loading skeleton for the Dashboard view
 *
 * Displays a placeholder UI while dashboard data is being loaded,
 * providing better UX than a simple loading spinner.
 */
</script>

<style scoped>
.dashboard-skeleton {
  min-height: 80vh;
}
</style>
