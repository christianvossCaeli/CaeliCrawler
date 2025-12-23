<template>
  <HelpCard section-id="api-templates" :title="t('help.apiTemplates.title')" icon="mdi-api" color="deep-purple">
    <p class="mb-4">{{ t('help.apiTemplates.description') }}</p>

    <v-alert type="info" variant="tonal" class="mb-4">
      <v-icon>mdi-lightbulb</v-icon>
      {{ t('help.apiTemplates.aiDiscoveryInfo') }}
    </v-alert>

    <h3 class="text-h6 mb-3">{{ t('help.apiTemplates.apiTypes.title') }}</h3>
    <v-row class="mb-4">
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="pa-3 text-center">
          <v-chip color="primary" size="small" label class="mb-2">REST</v-chip>
          <div class="text-caption">{{ t('help.apiTemplates.apiTypes.rest') }}</div>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="pa-3 text-center">
          <v-chip color="pink" size="small" label class="mb-2">GraphQL</v-chip>
          <div class="text-caption">{{ t('help.apiTemplates.apiTypes.graphql') }}</div>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="pa-3 text-center">
          <v-chip color="teal" size="small" label class="mb-2">SPARQL</v-chip>
          <div class="text-caption">{{ t('help.apiTemplates.apiTypes.sparql') }}</div>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card variant="outlined" class="pa-3 text-center">
          <v-chip color="indigo" size="small" label class="mb-2">OParl</v-chip>
          <div class="text-caption">{{ t('help.apiTemplates.apiTypes.oparl') }}</div>
        </v-card>
      </v-col>
    </v-row>

    <h3 class="text-h6 mb-3">{{ t('help.apiTemplates.status.title') }}</h3>
    <v-table density="compact" class="mb-4">
      <thead>
        <tr>
          <th>{{ t('help.apiTemplates.status.table.status') }}</th>
          <th>{{ t('help.apiTemplates.status.table.description') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>
            <v-chip color="warning" size="small">
              <v-icon start size="small">mdi-clock-outline</v-icon>
              PENDING
            </v-chip>
          </td>
          <td>{{ t('help.apiTemplates.status.pending') }}</td>
        </tr>
        <tr>
          <td>
            <v-chip color="success" size="small">
              <v-icon start size="small">mdi-check-circle</v-icon>
              ACTIVE
            </v-chip>
          </td>
          <td>{{ t('help.apiTemplates.status.active') }}</td>
        </tr>
        <tr>
          <td>
            <v-chip color="grey" size="small">
              <v-icon start size="small">mdi-pause-circle</v-icon>
              INACTIVE
            </v-chip>
          </td>
          <td>{{ t('help.apiTemplates.status.inactive') }}</td>
        </tr>
        <tr>
          <td>
            <v-chip color="error" size="small">
              <v-icon start size="small">mdi-alert-circle</v-icon>
              FAILED
            </v-chip>
          </td>
          <td>{{ t('help.apiTemplates.status.failed') }}</td>
        </tr>
      </tbody>
    </v-table>

    <h3 class="text-h6 mb-3">{{ t('help.apiTemplates.fields.title') }}</h3>
    <v-card variant="outlined" class="pa-3 mb-4">
      <v-list density="compact">
        <v-list-item prepend-icon="mdi-label">
          <v-list-item-title>{{ t('help.apiTemplates.fields.name') }}</v-list-item-title>
          <v-list-item-subtitle>{{ t('help.apiTemplates.fields.nameDesc') }}</v-list-item-subtitle>
        </v-list-item>
        <v-list-item prepend-icon="mdi-link">
          <v-list-item-title>{{ t('help.apiTemplates.fields.baseUrl') }}</v-list-item-title>
          <v-list-item-subtitle>{{ t('help.apiTemplates.fields.baseUrlDesc') }}</v-list-item-subtitle>
        </v-list-item>
        <v-list-item prepend-icon="mdi-api">
          <v-list-item-title>{{ t('help.apiTemplates.fields.endpoint') }}</v-list-item-title>
          <v-list-item-subtitle>{{ t('help.apiTemplates.fields.endpointDesc') }}</v-list-item-subtitle>
        </v-list-item>
        <v-list-item prepend-icon="mdi-tag-multiple">
          <v-list-item-title>{{ t('help.apiTemplates.fields.keywords') }}</v-list-item-title>
          <v-list-item-subtitle>{{ t('help.apiTemplates.fields.keywordsDesc') }}</v-list-item-subtitle>
        </v-list-item>
        <v-list-item prepend-icon="mdi-key">
          <v-list-item-title>{{ t('help.apiTemplates.fields.auth') }}</v-list-item-title>
          <v-list-item-subtitle>{{ t('help.apiTemplates.fields.authDesc') }}</v-list-item-subtitle>
        </v-list-item>
      </v-list>
    </v-card>

    <h3 class="text-h6 mb-3">{{ t('help.apiTemplates.actions.title') }}</h3>
    <v-chip-group class="mb-4">
      <v-chip color="success" variant="elevated">
        <v-icon start>mdi-play-circle</v-icon>
        {{ t('help.apiTemplates.actions.test') }}
      </v-chip>
      <v-chip color="primary" variant="elevated">
        <v-icon start>mdi-pencil</v-icon>
        {{ t('help.apiTemplates.actions.edit') }}
      </v-chip>
      <v-chip color="info" variant="elevated">
        <v-icon start>mdi-content-copy</v-icon>
        {{ t('help.apiTemplates.actions.duplicate') }}
      </v-chip>
      <v-chip color="error" variant="elevated">
        <v-icon start>mdi-delete</v-icon>
        {{ t('help.apiTemplates.actions.delete') }}
      </v-chip>
    </v-chip-group>

    <h3 class="text-h6 mb-3">{{ t('help.apiTemplates.testing.title') }}</h3>
    <v-alert type="success" variant="tonal" density="compact">
      <v-icon>mdi-test-tube</v-icon>
      {{ t('help.apiTemplates.testing.description') }}
    </v-alert>
  </HelpCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t } = useI18n()
</script>
