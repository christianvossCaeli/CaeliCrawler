<template>
  <HelpCard section-id="attachments" :title="t('help.attachments.title')" icon="mdi-paperclip" color="info">
    <v-alert type="info" variant="tonal" class="mb-4">
      {{ t('help.attachments.description') }}
    </v-alert>

    <h3 class="text-h6 mb-3">{{ t('help.attachments.supportedFormats.title') }}</h3>
    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="h-100">
          <v-card-title class="text-subtitle-1">
            <v-icon class="mr-2" color="primary">mdi-image</v-icon>
            {{ t('help.attachments.supportedFormats.images.title') }}
          </v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item>PNG, JPEG, GIF, WebP</v-list-item>
            </v-list>
            <p class="text-caption">{{ t('help.attachments.supportedFormats.images.description') }}</p>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="h-100">
          <v-card-title class="text-subtitle-1">
            <v-icon class="mr-2" color="error">mdi-file-pdf-box</v-icon>
            {{ t('help.attachments.supportedFormats.documents.title') }}
          </v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item>PDF</v-list-item>
            </v-list>
            <p class="text-caption">{{ t('help.attachments.supportedFormats.documents.description') }}</p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-alert type="warning" variant="tonal" class="mb-4">
      <strong>{{ t('help.attachments.maxSize.title') }}</strong>
      {{ t('help.attachments.maxSize.description') }}
    </v-alert>

    <h3 class="text-h6 mb-3">{{ t('help.attachments.upload.title') }}</h3>
    <v-expansion-panels variant="accordion" class="mb-4">
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2" color="primary">mdi-upload</v-icon>
          {{ t('help.attachments.upload.methods.title') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-list density="compact">
            <v-list-item prepend-icon="mdi-cursor-default-click">
              <v-list-item-title>{{ t('help.attachments.upload.methods.button') }}</v-list-item-title>
            </v-list-item>
            <v-list-item prepend-icon="mdi-drag">
              <v-list-item-title>{{ t('help.attachments.upload.methods.dragDrop') }}</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2" color="success">mdi-robot</v-icon>
          {{ t('help.attachments.aiAnalysis.title') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <p class="mb-2">{{ t('help.attachments.aiAnalysis.description') }}</p>
          <v-list density="compact">
            <v-list-item prepend-icon="mdi-text-recognition">
              <v-list-item-title>{{ t('help.attachments.aiAnalysis.textExtraction') }}</v-list-item-title>
            </v-list-item>
            <v-list-item prepend-icon="mdi-account-search">
              <v-list-item-title>{{ t('help.attachments.aiAnalysis.entityDetection') }}</v-list-item-title>
            </v-list-item>
            <v-list-item prepend-icon="mdi-tag-multiple">
              <v-list-item-title>{{ t('help.attachments.aiAnalysis.facetSuggestions') }}</v-list-item-title>
            </v-list-item>
          </v-list>
          <v-alert type="info" variant="tonal" density="compact" class="mt-2">
            {{ t('help.attachments.aiAnalysis.note') }}
          </v-alert>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <h3 class="text-h6 mb-3">{{ t('help.attachments.workflow.title') }}</h3>
    <v-timeline density="compact" side="end" class="mb-4">
      <v-timeline-item dot-color="primary" size="small">
        <v-card variant="outlined" class="pa-3">
          <strong>1.</strong> {{ t('help.attachments.workflow.step1') }}
        </v-card>
      </v-timeline-item>
      <v-timeline-item dot-color="primary" size="small">
        <v-card variant="outlined" class="pa-3">
          <strong>2.</strong> {{ t('help.attachments.workflow.step2') }}
        </v-card>
      </v-timeline-item>
      <v-timeline-item dot-color="primary" size="small">
        <v-card variant="outlined" class="pa-3">
          <strong>3.</strong> {{ t('help.attachments.workflow.step3') }}
        </v-card>
      </v-timeline-item>
      <v-timeline-item dot-color="success" size="small">
        <v-card variant="outlined" class="pa-3">
          <strong>4.</strong> {{ t('help.attachments.workflow.step4') }}
        </v-card>
      </v-timeline-item>
    </v-timeline>

    <h3 class="text-h6 mb-3">{{ t('help.attachments.status.title') }}</h3>
    <v-table density="compact" class="mb-4">
      <thead>
        <tr>
          <th>{{ t('help.attachments.status.statusColumn') }}</th>
          <th>{{ t('help.attachments.status.descriptionColumn') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><v-chip size="small" color="grey">{{ t('help.attachments.status.pending') }}</v-chip></td>
          <td>{{ t('help.attachments.status.pendingDesc') }}</td>
        </tr>
        <tr>
          <td><v-chip size="small" color="info">{{ t('help.attachments.status.analyzing') }}</v-chip></td>
          <td>{{ t('help.attachments.status.analyzingDesc') }}</td>
        </tr>
        <tr>
          <td><v-chip size="small" color="success">{{ t('help.attachments.status.completed') }}</v-chip></td>
          <td>{{ t('help.attachments.status.completedDesc') }}</td>
        </tr>
        <tr>
          <td><v-chip size="small" color="error">{{ t('help.attachments.status.failed') }}</v-chip></td>
          <td>{{ t('help.attachments.status.failedDesc') }}</td>
        </tr>
      </tbody>
    </v-table>

    <h3 class="text-h6 mb-3">{{ t('help.attachments.facetApplication.title') }}</h3>
    <p class="mb-3">{{ t('help.attachments.facetApplication.description') }}</p>
    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-eye">
        <v-list-item-title>{{ t('help.attachments.facetApplication.step1') }}</v-list-item-title>
      </v-list-item>
      <v-list-item prepend-icon="mdi-checkbox-marked">
        <v-list-item-title>{{ t('help.attachments.facetApplication.step2') }}</v-list-item-title>
      </v-list-item>
      <v-list-item prepend-icon="mdi-check-all">
        <v-list-item-title>{{ t('help.attachments.facetApplication.step3') }}</v-list-item-title>
      </v-list-item>
    </v-list>
  </HelpCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t } = useI18n()
</script>
