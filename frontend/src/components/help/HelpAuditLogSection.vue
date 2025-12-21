<template>
  <HelpCard section-id="audit-log" :title="t('help.auditLog.title')" icon="mdi-history" color="brown">
    <p class="mb-4">
      {{ t('help.auditLog.description') }}
    </p>

    <v-alert type="info" variant="tonal" class="mb-4">
      <v-icon class="mr-2">mdi-shield-account</v-icon>
      {{ t('help.auditLog.accessInfo') }}
    </v-alert>

    <h3 class="text-h6 mb-3">{{ t('help.auditLog.overview.title') }}</h3>
    <p class="mb-4">
      {{ t('help.auditLog.overview.description') }}
    </p>

    <v-card variant="outlined" class="mb-4">
      <v-card-subtitle>{{ t('help.auditLog.overview.recordedInfo.title') }}</v-card-subtitle>
      <v-card-text>
        <v-list density="compact">
          <v-list-item prepend-icon="mdi-account">
            <v-list-item-subtitle>{{ t('help.auditLog.overview.recordedInfo.who') }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item prepend-icon="mdi-clock">
            <v-list-item-subtitle>{{ t('help.auditLog.overview.recordedInfo.when') }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item prepend-icon="mdi-file-document">
            <v-list-item-subtitle>{{ t('help.auditLog.overview.recordedInfo.what') }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item prepend-icon="mdi-delta">
            <v-list-item-subtitle>{{ t('help.auditLog.overview.recordedInfo.changes') }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item prepend-icon="mdi-ip">
            <v-list-item-subtitle>{{ t('help.auditLog.overview.recordedInfo.ip') }}</v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.auditLog.actionTypes.title') }}</h3>
    <v-row>
      <v-col cols="12" md="4">
        <v-chip color="success" class="mb-2">
          <v-icon start>mdi-plus</v-icon>
          {{ t('help.auditLog.actionTypes.create') }}
        </v-chip>
        <p class="text-body-2">{{ t('help.auditLog.actionTypes.createDesc') }}</p>
      </v-col>
      <v-col cols="12" md="4">
        <v-chip color="warning" class="mb-2">
          <v-icon start>mdi-pencil</v-icon>
          {{ t('help.auditLog.actionTypes.update') }}
        </v-chip>
        <p class="text-body-2">{{ t('help.auditLog.actionTypes.updateDesc') }}</p>
      </v-col>
      <v-col cols="12" md="4">
        <v-chip color="error" class="mb-2">
          <v-icon start>mdi-delete</v-icon>
          {{ t('help.auditLog.actionTypes.delete') }}
        </v-chip>
        <p class="text-body-2">{{ t('help.auditLog.actionTypes.deleteDesc') }}</p>
      </v-col>
    </v-row>
    <v-row class="mt-2">
      <v-col cols="12" md="4">
        <v-chip color="info" class="mb-2">
          <v-icon start>mdi-login</v-icon>
          {{ t('help.auditLog.actionTypes.login') }}
        </v-chip>
        <p class="text-body-2">{{ t('help.auditLog.actionTypes.loginDesc') }}</p>
      </v-col>
      <v-col cols="12" md="4">
        <v-chip color="grey" class="mb-2">
          <v-icon start>mdi-logout</v-icon>
          {{ t('help.auditLog.actionTypes.logout') }}
        </v-chip>
        <p class="text-body-2">{{ t('help.auditLog.actionTypes.logoutDesc') }}</p>
      </v-col>
    </v-row>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.auditLog.filters.title') }}</h3>
    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-filter-variant">
        <v-list-item-subtitle>{{ t('help.auditLog.filters.action') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-shape">
        <v-list-item-subtitle>{{ t('help.auditLog.filters.entityType') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-identifier">
        <v-list-item-subtitle>{{ t('help.auditLog.filters.entityId') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-account">
        <v-list-item-subtitle>{{ t('help.auditLog.filters.userId') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-calendar-range">
        <v-list-item-subtitle>{{ t('help.auditLog.filters.dateRange') }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.auditLog.entityHistory.title') }}</h3>
    <p class="mb-4">{{ t('help.auditLog.entityHistory.description') }}</p>

    <v-list density="compact" class="mb-4">
      <v-list-item
        v-for="(feature, idx) in (t('help.auditLog.entityHistory.features', { returnObjects: true }) as unknown as string[])"
        :key="idx"
        prepend-icon="mdi-check"
      >
        <v-list-item-subtitle>{{ feature }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.auditLog.versioning.title') }}</h3>
    <p class="mb-4">{{ t('help.auditLog.versioning.description') }}</p>

    <v-row>
      <v-col cols="12" md="4">
        <v-card variant="outlined" class="h-100">
          <v-card-title class="text-subtitle-1">
            <v-icon class="mr-2">mdi-delta</v-icon>
            {{ t('help.auditLog.versioning.diffBased') }}
          </v-card-title>
          <v-card-text>{{ t('help.auditLog.versioning.diffBasedDesc') }}</v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card variant="outlined" class="h-100">
          <v-card-title class="text-subtitle-1">
            <v-icon class="mr-2">mdi-camera</v-icon>
            {{ t('help.auditLog.versioning.snapshots') }}
          </v-card-title>
          <v-card-text>{{ t('help.auditLog.versioning.snapshotsDesc') }}</v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card variant="outlined" class="h-100">
          <v-card-title class="text-subtitle-1">
            <v-icon class="mr-2">mdi-restore</v-icon>
            {{ t('help.auditLog.versioning.reconstruction') }}
          </v-card-title>
          <v-card-text>{{ t('help.auditLog.versioning.reconstructionDesc') }}</v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.auditLog.statistics.title') }}</h3>
    <p class="mb-4">{{ t('help.auditLog.statistics.description') }}</p>

    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-counter">
        <v-list-item-subtitle>{{ t('help.auditLog.statistics.totalEntries') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-calendar-today">
        <v-list-item-subtitle>{{ t('help.auditLog.statistics.entriesToday') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-chart-pie">
        <v-list-item-subtitle>{{ t('help.auditLog.statistics.actionsBreakdown') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-account-star">
        <v-list-item-subtitle>{{ t('help.auditLog.statistics.topUsers') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-format-list-numbered">
        <v-list-item-subtitle>{{ t('help.auditLog.statistics.topEntityTypes') }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>
  </HelpCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t } = useI18n()
</script>
