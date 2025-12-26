<template>
  <HelpCard section-id="ai-assistant" :title="t('help.aiAssistant.title')" icon="mdi-robot-happy" color="pink">
    <p class="mb-4">
      {{ t('help.aiAssistant.description') }}
    </p>

    <h3 class="text-h6 mb-3">{{ t('help.aiAssistant.overview.title') }}</h3>
    <p class="mb-4">
      {{ t('help.aiAssistant.overview.description') }}
    </p>

    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-message-text">
        <v-list-item-title><strong>{{ t('help.aiAssistant.overview.naturalLanguage') }}</strong></v-list-item-title>
        <v-list-item-subtitle>{{ t('help.aiAssistant.overview.naturalLanguageDesc') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-target">
        <v-list-item-title><strong>{{ t('help.aiAssistant.overview.contextAware') }}</strong></v-list-item-title>
        <v-list-item-subtitle>{{ t('help.aiAssistant.overview.contextAwareDesc') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-slash-forward">
        <v-list-item-title><strong>{{ t('help.aiAssistant.overview.slashCommands') }}</strong></v-list-item-title>
        <v-list-item-subtitle>{{ t('help.aiAssistant.overview.slashCommandsDesc') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-image">
        <v-list-item-title><strong>{{ t('help.aiAssistant.overview.imageAnalysis') }}</strong></v-list-item-title>
        <v-list-item-subtitle>{{ t('help.aiAssistant.overview.imageAnalysisDesc') }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.aiAssistant.imageUpload.title') }}</h3>
    <p class="mb-4">{{ t('help.aiAssistant.imageUpload.description') }}</p>

    <v-card variant="outlined" class="mb-4">
      <v-card-subtitle>{{ t('help.aiAssistant.imageUpload.uploadMethods.title') }}</v-card-subtitle>
      <v-card-text>
        <v-list density="compact">
          <v-list-item prepend-icon="mdi-paperclip">
            <v-list-item-subtitle>{{ t('help.aiAssistant.imageUpload.uploadMethods.button') }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item prepend-icon="mdi-content-paste">
            <v-list-item-subtitle>{{ t('help.aiAssistant.imageUpload.uploadMethods.paste') }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item prepend-icon="mdi-drag">
            <v-list-item-subtitle>{{ t('help.aiAssistant.imageUpload.uploadMethods.drag') }}</v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>

    <v-alert type="info" variant="tonal" class="mb-4">
      {{ t('help.aiAssistant.imageUpload.supportedFormats.formats') }}
    </v-alert>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.aiAssistant.modes.title') }}</h3>
    <v-row>
      <v-col cols="12" md="4">
        <v-card variant="outlined">
          <v-card-title class="text-subtitle-1">
            <v-icon color="success" class="mr-2">mdi-magnify</v-icon>
            {{ t('help.aiAssistant.modes.readMode') }}
          </v-card-title>
          <v-card-text>{{ t('help.aiAssistant.modes.readModeDesc') }}</v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card variant="outlined">
          <v-card-title class="text-subtitle-1">
            <v-icon color="warning" class="mr-2">mdi-pencil</v-icon>
            {{ t('help.aiAssistant.modes.writeMode') }}
          </v-card-title>
          <v-card-text>{{ t('help.aiAssistant.modes.writeModeDesc') }}</v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card variant="outlined">
          <v-card-title class="text-subtitle-1">
            <v-icon color="info" class="mr-2">mdi-lightbulb-on</v-icon>
            {{ t('help.aiAssistant.modes.planMode') }}
          </v-card-title>
          <v-card-text>{{ t('help.aiAssistant.modes.planModeDesc') }}</v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.aiAssistant.quickActions.title') }}</h3>
    <p class="mb-3">{{ t('help.aiAssistant.quickActions.description') }}</p>
    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-chevron-down">
        <v-list-item-subtitle>{{ t('help.aiAssistant.quickActions.expand') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-map-marker">
        <v-list-item-subtitle>{{ t('help.aiAssistant.quickActions.contextual') }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.aiAssistant.slashCommands.title') }}</h3>
    <v-table density="compact" class="mb-4">
      <thead>
        <tr>
          <th>{{ t('common.command') }}</th>
          <th>{{ t('common.description') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><code>{{ t('help.aiAssistant.slashCommands.help') }}</code></td>
          <td>{{ t('help.aiAssistant.slashCommands.helpDesc') }}</td>
        </tr>
        <tr>
          <td><code>{{ t('help.aiAssistant.slashCommands.search') }}</code></td>
          <td>{{ t('help.aiAssistant.slashCommands.searchDesc') }}</td>
        </tr>
        <tr>
          <td><code>{{ t('help.aiAssistant.slashCommands.create') }}</code></td>
          <td>{{ t('help.aiAssistant.slashCommands.createDesc') }}</td>
        </tr>
        <tr>
          <td><code>{{ t('help.aiAssistant.slashCommands.summary') }}</code></td>
          <td>{{ t('help.aiAssistant.slashCommands.summaryDesc') }}</td>
        </tr>
        <tr>
          <td><code>{{ t('help.aiAssistant.slashCommands.navigate') }}</code></td>
          <td>{{ t('help.aiAssistant.slashCommands.navigateDesc') }}</td>
        </tr>
      </tbody>
    </v-table>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.aiAssistant.exampleQueries.title') }}</h3>
    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-lightbulb">
        <v-list-item-subtitle>{{ t('help.aiAssistant.exampleQueries.examples.painPoints') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-lightbulb">
        <v-list-item-subtitle>{{ t('help.aiAssistant.exampleQueries.examples.decisionMakers') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-lightbulb">
        <v-list-item-subtitle>{{ t('help.aiAssistant.exampleQueries.examples.events') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-lightbulb">
        <v-list-item-subtitle>{{ t('help.aiAssistant.exampleQueries.examples.summary') }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.aiAssistant.contextActions.title') }}</h3>
    <p class="mb-4">{{ t('help.aiAssistant.contextActions.description') }}</p>

    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-cog-sync">
        <v-list-item-title><strong>{{ t('help.aiAssistant.contextActions.capabilities.analyzePysis') }}</strong></v-list-item-title>
        <v-list-item-subtitle>{{ t('help.aiAssistant.contextActions.capabilities.analyzePysisDesc') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-auto-fix">
        <v-list-item-title><strong>{{ t('help.aiAssistant.contextActions.capabilities.enrichFacets') }}</strong></v-list-item-title>
        <v-list-item-subtitle>{{ t('help.aiAssistant.contextActions.capabilities.enrichFacetsDesc') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-information">
        <v-list-item-title><strong>{{ t('help.aiAssistant.contextActions.capabilities.showStatus') }}</strong></v-list-item-title>
        <v-list-item-subtitle>{{ t('help.aiAssistant.contextActions.capabilities.showStatusDesc') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-spider-web">
        <v-list-item-title><strong>{{ t('help.aiAssistant.contextActions.capabilities.startCrawl') }}</strong></v-list-item-title>
        <v-list-item-subtitle>{{ t('help.aiAssistant.contextActions.capabilities.startCrawlDesc') }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.aiAssistant.batchOperations.title') }}</h3>
    <p class="mb-4">{{ t('help.aiAssistant.batchOperations.description') }}</p>

    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-plus-box-multiple">
        <v-list-item-title><strong>{{ t('help.aiAssistant.batchOperations.capabilities.addFacet') }}</strong></v-list-item-title>
        <v-list-item-subtitle>{{ t('help.aiAssistant.batchOperations.capabilities.addFacetDesc') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-pencil-box-multiple">
        <v-list-item-title><strong>{{ t('help.aiAssistant.batchOperations.capabilities.updateField') }}</strong></v-list-item-title>
        <v-list-item-subtitle>{{ t('help.aiAssistant.batchOperations.capabilities.updateFieldDesc') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-minus-box-multiple">
        <v-list-item-title><strong>{{ t('help.aiAssistant.batchOperations.capabilities.removeFacet') }}</strong></v-list-item-title>
        <v-list-item-subtitle>{{ t('help.aiAssistant.batchOperations.capabilities.removeFacetDesc') }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <v-alert type="warning" variant="tonal" class="mb-4">
      {{ t('help.aiAssistant.batchOperations.safetyNote') }}
    </v-alert>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.aiAssistant.tips.title') }}</h3>
    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-check">
        <v-list-item-subtitle>{{ t('help.aiAssistant.tips.beSpecific') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-check">
        <v-list-item-subtitle>{{ t('help.aiAssistant.tips.useContext') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-check">
        <v-list-item-subtitle>{{ t('help.aiAssistant.tips.slashShortcuts') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-check">
        <v-list-item-subtitle>{{ t('help.aiAssistant.tips.confirmWrite') }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>
  </HelpCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t } = useI18n()
</script>
