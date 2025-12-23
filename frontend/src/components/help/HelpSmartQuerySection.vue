<template>
  <v-card id="smart-query" class="mb-4">
    <v-card-title class="text-h5 bg-primary">
      <v-icon class="mr-2">mdi-brain</v-icon>
      {{ t('help.smartQuery.title') }}
    </v-card-title>
    <v-card-text class="pt-4">
      <v-alert type="info" variant="tonal" class="mb-4">
        <strong>{{ t('help.smartQuery.alert.title') }}</strong> {{ t('help.smartQuery.alert.description') }}
      </v-alert>

      <h3 class="text-h6 mb-3">{{ t('help.smartQuery.modes_title') }}</h3>
      <v-row class="mb-4">
        <v-col cols="12" md="6">
          <v-card variant="outlined" class="h-100">
            <v-card-title class="text-subtitle-1">
              <v-icon class="mr-2" color="info">mdi-magnify</v-icon>
              {{ t('help.smartQuery.read_mode.title') }}
            </v-card-title>
            <v-card-text>
              <p class="mb-2">{{ t('help.smartQuery.read_mode.description') }}</p>
              <v-list density="compact">
                <v-list-item prepend-icon="mdi-chat-question">
                  {{ t('help.smartQuery.read_mode.examples.1') }}
                </v-list-item>
                <v-list-item prepend-icon="mdi-chat-question">
                  {{ t('help.smartQuery.read_mode.examples.2') }}
                </v-list-item>
                <v-list-item prepend-icon="mdi-chat-question">
                  {{ t('help.smartQuery.read_mode.examples.3') }}
                </v-list-item>
              </v-list>
              <p class="text-caption mt-2">{{ t('help.smartQuery.read_mode.note') }}</p>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="6">
          <v-card variant="outlined" class="h-100" color="warning">
            <v-card-title class="text-subtitle-1">
              <v-icon class="mr-2" color="warning">mdi-pencil-plus</v-icon>
              {{ t('help.smartQuery.write_mode.title') }}
            </v-card-title>
            <v-card-text>
              <p class="mb-2">{{ t('help.smartQuery.write_mode.description') }}</p>
              <v-list density="compact">
                <v-list-item prepend-icon="mdi-creation">
                  {{ t('help.smartQuery.write_mode.examples.1') }}
                </v-list-item>
                <v-list-item prepend-icon="mdi-creation">
                  {{ t('help.smartQuery.write_mode.examples.2') }}
                </v-list-item>
              </v-list>
              <p class="text-caption mt-2">{{ t('help.smartQuery.write_mode.note') }}</p>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <h3 class="text-h6 mb-3">{{ t('help.smartQuery.speechRecognition.title') }}</h3>
      <v-card variant="outlined" class="mb-4" color="success">
        <v-card-title class="text-subtitle-1">
          <v-icon class="mr-2" color="success">mdi-microphone</v-icon>
          {{ t('help.smartQuery.speechRecognition.voiceInput') }}
        </v-card-title>
        <v-card-text>
          <p class="mb-3">{{ t('help.smartQuery.speechRecognition.description') }}</p>
          <v-list density="compact">
            <v-list-item prepend-icon="mdi-microphone">
              {{ t('help.smartQuery.speechRecognition.howTo') }}
            </v-list-item>
            <v-list-item prepend-icon="mdi-text">
              {{ t('help.smartQuery.speechRecognition.realtime') }}
            </v-list-item>
            <v-list-item prepend-icon="mdi-send">
              {{ t('help.smartQuery.speechRecognition.submit') }}
            </v-list-item>
          </v-list>
          <v-alert type="info" variant="tonal" density="compact" class="mt-3">
            <v-icon>mdi-information</v-icon>
            {{ t('help.smartQuery.speechRecognition.browserSupport') }}
          </v-alert>
        </v-card-text>
      </v-card>

      <h3 class="text-h6 mb-3">{{ t('help.smartQuery.category_setup_title') }}</h3>
      <p class="mb-3">
        {{ t('help.smartQuery.category_setup_description') }}
      </p>

      <v-stepper :model-value="1" alt-labels class="elevation-0 bg-transparent mb-4">
        <v-stepper-header>
          <v-stepper-item :title="t('help.smartQuery.setup_steps.step1.title')" :subtitle="t('help.smartQuery.setup_steps.step1.subtitle')" value="1" complete color="primary"></v-stepper-item>
          <v-divider></v-divider>
          <v-stepper-item :title="t('help.smartQuery.setup_steps.step2.title')" :subtitle="t('help.smartQuery.setup_steps.step2.subtitle')" value="2" complete color="blue"></v-stepper-item>
          <v-divider></v-divider>
          <v-stepper-item :title="t('help.smartQuery.setup_steps.step3.title')" :subtitle="t('help.smartQuery.setup_steps.step3.subtitle')" value="3" complete color="green"></v-stepper-item>
        </v-stepper-header>
      </v-stepper>

      <v-expansion-panels variant="accordion" class="mb-4">
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon class="mr-2" color="primary">mdi-cube</v-icon>
            {{ t('help.smartQuery.categorySetup.step1.heading') }}
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <p class="mb-2">{{ t('help.smartQuery.categorySetup.step1.description') }}</p>
            <v-list density="compact">
              <v-list-item v-for="(item, index) in (tm('help.smartQuery.categorySetup.step1.items') as string[])" :key="index">{{ item }}</v-list-item>
            </v-list>
          </v-expansion-panel-text>
        </v-expansion-panel>
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon class="mr-2" color="blue">mdi-folder-plus</v-icon>
            {{ t('help.smartQuery.categorySetup.step2.heading') }}
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <p class="mb-2">{{ t('help.smartQuery.categorySetup.step2.description') }}</p>
            <v-list density="compact">
              <v-list-item v-for="(item, index) in (tm('help.smartQuery.categorySetup.step2.items') as string[])" :key="index">{{ item }}</v-list-item>
            </v-list>
          </v-expansion-panel-text>
        </v-expansion-panel>
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon class="mr-2" color="green">mdi-web</v-icon>
            {{ t('help.smartQuery.categorySetup.step3.heading') }}
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <p class="mb-2">{{ t('help.smartQuery.categorySetup.step3.description') }}</p>
            <v-list density="compact">
              <v-list-item v-for="(item, index) in (tm('help.smartQuery.categorySetup.step3.items') as string[])" :key="index">{{ item }}</v-list-item>
            </v-list>
            <v-alert type="info" variant="tonal" density="compact" class="mt-2">
              {{ t('help.smartQuery.categorySetup.step3.important') }}
            </v-alert>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <h3 class="text-h6 mb-3">{{ t('help.smartQuery.write_mode_workflow.title') }}</h3>
      <v-timeline density="compact" side="end" class="mb-4">
        <v-timeline-item dot-color="primary" size="small">
          <template v-slot:opposite><strong>1</strong></template>
          <div>
            <strong>{{ t('help.smartQuery.write_mode_workflow.step1.title') }}</strong><br>
            {{ t('help.smartQuery.write_mode_workflow.step1.description') }}
          </div>
        </v-timeline-item>
        <v-timeline-item dot-color="warning" size="small">
          <template v-slot:opposite><strong>2</strong></template>
          <div>
            <strong>{{ t('help.smartQuery.write_mode_workflow.step2.title') }}</strong><br>
            {{ t('help.smartQuery.write_mode_workflow.step2.description') }}
          </div>
        </v-timeline-item>
        <v-timeline-item dot-color="info" size="small">
          <template v-slot:opposite><strong>3</strong></template>
          <div>
            <strong>{{ t('help.smartQuery.write_mode_workflow.step3.title') }}</strong><br>
            {{ t('help.smartQuery.write_mode_workflow.step3.description') }}
          </div>
        </v-timeline-item>
        <v-timeline-item dot-color="success" size="small">
          <template v-slot:opposite><strong>4</strong></template>
          <div>
            <strong>{{ t('help.smartQuery.write_mode_workflow.step4.title') }}</strong><br>
            {{ t('help.smartQuery.write_mode_workflow.step4.description') }}
          </div>
        </v-timeline-item>
        <v-timeline-item dot-color="primary" size="small">
          <template v-slot:opposite><strong>5</strong></template>
          <div>
            <strong>{{ t('help.smartQuery.write_mode_workflow.step5.title') }}</strong><br>
            {{ t('help.smartQuery.write_mode_workflow.step5.description') }}
          </div>
        </v-timeline-item>
      </v-timeline>

      <h3 class="text-h6 mb-3">{{ t('help.smartQuery.geographic_filters.title') }}</h3>
      <p class="mb-3">{{ t('help.smartQuery.geographic_filters.description') }}</p>
      <v-table density="compact" class="mb-4">
        <thead><tr><th>{{ t('help.smartQuery.geographic_filters.table.input') }}</th><th>{{ t('help.smartQuery.geographic_filters.table.recognized_as') }}</th></tr></thead>
        <tbody>
          <tr v-for="(example, index) in (tm('help.smartQuery.geographic_filters.examples') as any[])" :key="index">
            <td>{{ example.input }}</td>
            <td>{{ example.output }}</td>
          </tr>
        </tbody>
      </v-table>

      <h3 class="text-h6 mb-3">{{ t('help.smartQuery.example_queries.title') }}</h3>
      <v-table density="compact">
        <thead><tr><th>{{ t('help.smartQuery.example_queries.table.query') }}</th><th>{{ t('help.smartQuery.example_queries.table.mode') }}</th><th>{{ t('help.smartQuery.example_queries.table.result') }}</th></tr></thead>
        <tbody>
          <tr v-for="(example, index) in (tm('help.smartQuery.example_queries.examples') as any[])" :key="index">
            <td>"{{ example.query }}"</td>
            <td><v-chip size="x-small" :color="example.mode === 'read' ? 'info' : 'warning'">{{ example.mode === 'read' ? t('help.smartQuery.example_queries.read') : t('help.smartQuery.example_queries.write') }}</v-chip></td>
            <td>{{ example.result }}</td>
          </tr>
        </tbody>
      </v-table>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t, tm } = useI18n()
</script>
