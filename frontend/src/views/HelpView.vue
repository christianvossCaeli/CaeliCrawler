<template>
  <div>
    <h1 class="text-h4 mb-6">
      <v-icon class="mr-2">mdi-help-circle</v-icon>
      {{ t('help.title') }}
    </h1>

    <!-- Quick Navigation -->
    <v-card class="mb-6">
      <v-card-text>
        <div class="d-flex flex-wrap ga-2">
          <v-chip
            v-for="section in sections"
            :key="section.id"
            :color="activeSection === section.id ? 'primary' : 'default'"
            variant="outlined"
            @click="scrollTo(section.id)"
          >
            <v-icon start size="small">{{ section.icon }}</v-icon>
            {{ section.title }}
          </v-chip>
        </div>
      </v-card-text>
    </v-card>

    <!-- Content -->
    <v-row>
      <v-col cols="12" lg="9">
        <!-- Einführung -->
        <v-card id="intro" class="mb-4">
          <v-card-title class="text-h5 bg-primary">
            <v-icon class="mr-2">mdi-information</v-icon>
            {{ t('help.intro.title') }}
          </v-card-title>
          <v-card-text class="pt-4">
            <h3 class="text-h6 mb-3">{{ t('help.intro.what_is_title') }}</h3>
            <p class="mb-4">
              {{ t('help.intro.what_is_description') }}
            </p>

            <h3 class="text-h6 mb-3">{{ t('help.intro.main_functions_title') }}</h3>
            <v-table density="compact" class="mb-4">
              <thead>
                <tr><th>{{ t('help.intro.table.function') }}</th><th>{{ t('help.intro.table.description') }}</th></tr>
              </thead>
              <tbody>
                <tr><td><strong>{{ t('help.intro.functions.web_crawling.title') }}</strong></td><td>{{ t('help.intro.functions.web_crawling.description') }}</td></tr>
                <tr><td><strong>{{ t('help.intro.functions.document_processing.title') }}</strong></td><td>{{ t('help.intro.functions.document_processing.description') }}</td></tr>
                <tr><td><strong>{{ t('help.intro.functions.ai_analysis.title') }}</strong></td><td>{{ t('help.intro.functions.ai_analysis.description') }}</td></tr>
                <tr><td><strong>{{ t('help.intro.functions.relevance_filtering.title') }}</strong></td><td>{{ t('help.intro.functions.relevance_filtering.description') }}</td></tr>
                <tr><td><strong>{{ t('help.intro.functions.structured_results.title') }}</strong></td><td>{{ t('help.intro.functions.structured_results.description') }}</td></tr>
              </tbody>
            </v-table>

            <h3 class="text-h6 mb-3">{{ t('help.intro.workflow_title') }}</h3>
            <v-stepper :model-value="1" alt-labels class="elevation-0 bg-transparent">
              <v-stepper-header>
                <v-stepper-item :title="t('help.intro.workflow.step1.title')" :subtitle="t('help.intro.workflow.step1.subtitle')" value="1" complete></v-stepper-item>
                <v-divider></v-divider>
                <v-stepper-item :title="t('help.intro.workflow.step2.title')" :subtitle="t('help.intro.workflow.step2.subtitle')" value="2" complete></v-stepper-item>
                <v-divider></v-divider>
                <v-stepper-item :title="t('help.intro.workflow.step3.title')" :subtitle="t('help.intro.workflow.step3.subtitle')" value="3" complete></v-stepper-item>
                <v-divider></v-divider>
                <v-stepper-item :title="t('help.intro.workflow.step4.title')" :subtitle="t('help.intro.workflow.step4.subtitle')" value="4" complete></v-stepper-item>
                <v-divider></v-divider>
                <v-stepper-item :title="t('help.intro.workflow.step5.title')" :subtitle="t('help.intro.workflow.step5.subtitle')" value="5" complete></v-stepper-item>
                <v-divider></v-divider>
                <v-stepper-item :title="t('help.intro.workflow.step6.title')" :subtitle="t('help.intro.workflow.step6.subtitle')" value="6" complete></v-stepper-item>
              </v-stepper-header>
            </v-stepper>
          </v-card-text>
        </v-card>

        <!-- Schnellstart -->
        <v-card id="quickstart" class="mb-4">
          <v-card-title class="text-h5 bg-success">
            <v-icon class="mr-2">mdi-rocket-launch</v-icon>
            {{ t('help.quickstart.title') }}
          </v-card-title>
          <v-card-text class="pt-4">
            <h3 class="text-h6 mb-3">{{ t('help.quickstart.subtitle') }}</h3>

            <v-timeline density="compact" side="end">
              <v-timeline-item dot-color="primary" size="small">
                <template v-slot:opposite><strong>{{ t('help.quickstart.step1.label') }}</strong></template>
                <v-card variant="outlined">
                  <v-card-title class="text-subtitle-1">{{ t('help.quickstart.step1.title') }}</v-card-title>
                  <v-card-text>
                    <ol class="pl-4">
                      <li>{{ t('help.quickstart.step1.instructions.1') }}</li>
                      <li>{{ t('help.quickstart.step1.instructions.2') }}</li>
                      <li>{{ t('help.quickstart.step1.instructions.3') }}</li>
                      <li>{{ t('help.quickstart.step1.instructions.4') }}</li>
                      <li>{{ t('help.quickstart.step1.instructions.5') }}</li>
                    </ol>
                  </v-card-text>
                </v-card>
              </v-timeline-item>

              <v-timeline-item dot-color="success" size="small">
                <template v-slot:opposite><strong>{{ t('help.quickstart.step2.label') }}</strong></template>
                <v-card variant="outlined">
                  <v-card-title class="text-subtitle-1">{{ t('help.quickstart.step2.title') }}</v-card-title>
                  <v-card-text>
                    <ol class="pl-4">
                      <li>{{ t('help.quickstart.step2.instructions.1') }}</li>
                      <li>{{ t('help.quickstart.step2.instructions.2') }}</li>
                      <li>{{ t('help.quickstart.step2.instructions.3') }}</li>
                      <li>{{ t('help.quickstart.step2.instructions.4') }}</li>
                      <li>{{ t('help.quickstart.step2.instructions.5') }}</li>
                    </ol>
                  </v-card-text>
                </v-card>
              </v-timeline-item>

              <v-timeline-item dot-color="warning" size="small">
                <template v-slot:opposite><strong>{{ t('help.quickstart.step3.label') }}</strong></template>
                <v-card variant="outlined">
                  <v-card-title class="text-subtitle-1">{{ t('help.quickstart.step3.title') }}</v-card-title>
                  <v-card-text>
                    <ol class="pl-4">
                      <li>{{ t('help.quickstart.step3.instructions.1') }}</li>
                      <li>{{ t('help.quickstart.step3.instructions.2') }}</li>
                      <li>{{ t('help.quickstart.step3.instructions.3') }}</li>
                    </ol>
                  </v-card-text>
                </v-card>
              </v-timeline-item>

              <v-timeline-item dot-color="info" size="small">
                <template v-slot:opposite><strong>{{ t('help.quickstart.step4.label') }}</strong></template>
                <v-card variant="outlined">
                  <v-card-title class="text-subtitle-1">{{ t('help.quickstart.step4.title') }}</v-card-title>
                  <v-card-text>
                    <ol class="pl-4">
                      <li>{{ t('help.quickstart.step4.instructions.1') }}</li>
                      <li>{{ t('help.quickstart.step4.instructions.2') }}</li>
                      <li>{{ t('help.quickstart.step4.instructions.3') }}</li>
                    </ol>
                  </v-card-text>
                </v-card>
              </v-timeline-item>
            </v-timeline>
          </v-card-text>
        </v-card>

        <!-- Dashboard -->
        <v-card id="dashboard" class="mb-4">
          <v-card-title class="text-h5 bg-info">
            <v-icon class="mr-2">mdi-view-dashboard</v-icon>
            {{ t('help.dashboard.title') }}
          </v-card-title>
          <v-card-text class="pt-4">
            <p class="mb-4">{{ t('help.dashboard.description') }}</p>

            <h3 class="text-h6 mb-3">{{ t('help.dashboard.stats_cards_title') }}</h3>
            <v-row class="mb-4">
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-3">
                  <v-icon color="primary" size="32">mdi-folder-multiple</v-icon>
                  <div class="text-h6">{{ t('help.dashboard.cards.categories.title') }}</div>
                  <div class="text-caption">{{ t('help.dashboard.cards.categories.description') }}</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-3">
                  <v-icon color="success" size="32">mdi-web</v-icon>
                  <div class="text-h6">{{ t('help.dashboard.cards.sources.title') }}</div>
                  <div class="text-caption">{{ t('help.dashboard.cards.sources.description') }}</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-3">
                  <v-icon color="info" size="32">mdi-file-document-multiple</v-icon>
                  <div class="text-h6">{{ t('help.dashboard.cards.documents.title') }}</div>
                  <div class="text-caption">{{ t('help.dashboard.cards.documents.description') }}</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-3">
                  <v-icon color="warning" size="32">mdi-robot</v-icon>
                  <div class="text-h6">{{ t('help.dashboard.cards.active_crawlers.title') }}</div>
                  <div class="text-caption">{{ t('help.dashboard.cards.active_crawlers.description') }}</div>
                </v-card>
              </v-col>
            </v-row>

            <h3 class="text-h6 mb-3">{{ t('help.dashboard.live_updates_title') }}</h3>
            <v-alert type="info" variant="tonal" class="mb-4">
              {{ t('help.dashboard.live_updates_description') }}
              <v-list density="compact" class="bg-transparent">
                <v-list-item prepend-icon="mdi-file-document">{{ t('help.dashboard.live_updates.documents') }}</v-list-item>
                <v-list-item prepend-icon="mdi-clock">{{ t('help.dashboard.live_updates.runtime') }}</v-list-item>
                <v-list-item prepend-icon="mdi-alert">{{ t('help.dashboard.live_updates.errors') }}</v-list-item>
              </v-list>
            </v-alert>

            <h3 class="text-h6 mb-3">{{ t('help.dashboard.status_jobs_title') }}</h3>
            <v-row class="mb-4">
              <v-col cols="12" md="6">
                <v-card variant="outlined" class="pa-3">
                  <div class="text-subtitle-1 mb-2"><v-icon class="mr-1">mdi-robot</v-icon> {{ t('help.dashboard.status_section.title') }}</div>
                  <v-list density="compact">
                    <v-list-item><v-icon color="success" class="mr-2">mdi-circle</v-icon> {{ t('help.dashboard.status_section.active_workers') }}</v-list-item>
                    <v-list-item><v-icon color="info" class="mr-2">mdi-run</v-icon> {{ t('help.dashboard.status_section.running_jobs') }}</v-list-item>
                    <v-list-item><v-icon color="warning" class="mr-2">mdi-clock-outline</v-icon> {{ t('help.dashboard.status_section.waiting_jobs') }}</v-list-item>
                  </v-list>
                </v-card>
              </v-col>
              <v-col cols="12" md="6">
                <v-card variant="outlined" class="pa-3">
                  <div class="text-subtitle-1 mb-2"><v-icon class="mr-1">mdi-history</v-icon> {{ t('help.dashboard.recent_jobs.title') }}</div>
                  <div class="text-body-2">{{ t('help.dashboard.recent_jobs.description') }}</div>
                </v-card>
              </v-col>
            </v-row>

            <h3 class="text-h6 mb-3">{{ t('help.dashboard.quick_actions_title') }}</h3>
            <v-chip-group class="mb-4">
              <v-chip color="primary" variant="elevated"><v-icon start>mdi-plus</v-icon> {{ t('help.dashboard.quick_actions.new_category') }}</v-chip>
              <v-chip color="success" variant="elevated"><v-icon start>mdi-web-plus</v-icon> {{ t('help.dashboard.quick_actions.new_source') }}</v-chip>
              <v-chip color="warning" variant="elevated"><v-icon start>mdi-play</v-icon> {{ t('help.dashboard.quick_actions.start_crawler') }}</v-chip>
              <v-chip color="info" variant="elevated"><v-icon start>mdi-export</v-icon> {{ t('help.dashboard.quick_actions.export_data') }}</v-chip>
            </v-chip-group>

            <h3 class="text-h6 mb-3">{{ t('help.dashboard.crawler_dialog_title') }}</h3>
            <v-table density="compact">
              <thead><tr><th>{{ t('help.dashboard.crawler_dialog.table.filter') }}</th><th>{{ t('help.dashboard.crawler_dialog.table.description') }}</th></tr></thead>
              <tbody>
                <tr><td><strong>{{ t('help.dashboard.crawler_dialog.filters.category.name') }}</strong></td><td>{{ t('help.dashboard.crawler_dialog.filters.category.description') }}</td></tr>
                <tr><td><strong>{{ t('help.dashboard.crawler_dialog.filters.country.name') }}</strong></td><td>{{ t('help.dashboard.crawler_dialog.filters.country.description') }}</td></tr>
                <tr><td><strong>{{ t('help.dashboard.crawler_dialog.filters.search.name') }}</strong></td><td>{{ t('help.dashboard.crawler_dialog.filters.search.description') }}</td></tr>
                <tr><td><strong>{{ t('help.dashboard.crawler_dialog.filters.max_count.name') }}</strong></td><td>{{ t('help.dashboard.crawler_dialog.filters.max_count.description') }}</td></tr>
                <tr><td><strong>{{ t('help.dashboard.crawler_dialog.filters.status.name') }}</strong></td><td>{{ t('help.dashboard.crawler_dialog.filters.status.description') }}</td></tr>
                <tr><td><strong>{{ t('help.dashboard.crawler_dialog.filters.source_type.name') }}</strong></td><td>{{ t('help.dashboard.crawler_dialog.filters.source_type.description') }}</td></tr>
              </tbody>
            </v-table>
            <v-alert type="warning" variant="tonal" density="compact" class="mt-3">
              <v-icon>mdi-alert</v-icon> {{ t('help.dashboard.crawler_dialog.warning') }}
            </v-alert>
          </v-card-text>
        </v-card>

        <!-- Smart Query -->
        <v-card id="smart-query" class="mb-4">
          <v-card-title class="text-h5 bg-gradient" style="background: linear-gradient(135deg, #7c3aed 0%, #2563eb 100%);">
            <v-icon class="mr-2">mdi-brain</v-icon>
            {{ t('help.smart_query.title') }}
          </v-card-title>
          <v-card-text class="pt-4">
            <v-alert type="info" variant="tonal" class="mb-4">
              <strong>{{ t('help.smart_query.alert.title') }}</strong> {{ t('help.smart_query.alert.description') }}
            </v-alert>

            <h3 class="text-h6 mb-3">{{ t('help.smart_query.modes_title') }}</h3>
            <v-row class="mb-4">
              <v-col cols="12" md="6">
                <v-card variant="outlined" class="h-100">
                  <v-card-title class="text-subtitle-1">
                    <v-icon class="mr-2" color="info">mdi-magnify</v-icon>
                    {{ t('help.smart_query.read_mode.title') }}
                  </v-card-title>
                  <v-card-text>
                    <p class="mb-2">{{ t('help.smart_query.read_mode.description') }}</p>
                    <v-list density="compact">
                      <v-list-item prepend-icon="mdi-chat-question">
                        {{ t('help.smart_query.read_mode.examples.1') }}
                      </v-list-item>
                      <v-list-item prepend-icon="mdi-chat-question">
                        {{ t('help.smart_query.read_mode.examples.2') }}
                      </v-list-item>
                      <v-list-item prepend-icon="mdi-chat-question">
                        {{ t('help.smart_query.read_mode.examples.3') }}
                      </v-list-item>
                    </v-list>
                    <p class="text-caption mt-2">{{ t('help.smart_query.read_mode.note') }}</p>
                  </v-card-text>
                </v-card>
              </v-col>
              <v-col cols="12" md="6">
                <v-card variant="outlined" class="h-100" color="warning">
                  <v-card-title class="text-subtitle-1">
                    <v-icon class="mr-2" color="warning">mdi-pencil-plus</v-icon>
                    {{ t('help.smart_query.write_mode.title') }}
                  </v-card-title>
                  <v-card-text>
                    <p class="mb-2">{{ t('help.smart_query.write_mode.description') }}</p>
                    <v-list density="compact">
                      <v-list-item prepend-icon="mdi-creation">
                        {{ t('help.smart_query.write_mode.examples.1') }}
                      </v-list-item>
                      <v-list-item prepend-icon="mdi-creation">
                        {{ t('help.smart_query.write_mode.examples.2') }}
                      </v-list-item>
                    </v-list>
                    <p class="text-caption mt-2">{{ t('help.smart_query.write_mode.note') }}</p>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>

            <h3 class="text-h6 mb-3">{{ t('help.smart_query.category_setup_title') }}</h3>
            <p class="mb-3">
              {{ t('help.smart_query.category_setup_description') }}
            </p>

            <v-stepper :model-value="1" alt-labels class="elevation-0 bg-transparent mb-4">
              <v-stepper-header>
                <v-stepper-item :title="t('help.smart_query.setup_steps.step1.title')" :subtitle="t('help.smart_query.setup_steps.step1.subtitle')" value="1" complete color="purple"></v-stepper-item>
                <v-divider></v-divider>
                <v-stepper-item :title="t('help.smart_query.setup_steps.step2.title')" :subtitle="t('help.smart_query.setup_steps.step2.subtitle')" value="2" complete color="blue"></v-stepper-item>
                <v-divider></v-divider>
                <v-stepper-item :title="t('help.smart_query.setup_steps.step3.title')" :subtitle="t('help.smart_query.setup_steps.step3.subtitle')" value="3" complete color="green"></v-stepper-item>
              </v-stepper-header>
            </v-stepper>

            <v-expansion-panels variant="accordion" class="mb-4">
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2" color="purple">mdi-cube</v-icon>
                  {{ t('help.smart_query.categorySetup.step1.heading') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <p class="mb-2">{{ t('help.smart_query.categorySetup.step1.description') }}</p>
                  <v-list density="compact">
                    <v-list-item v-for="(item, index) in (t('help.smart_query.categorySetup.step1.items') as string[])" :key="index">{{ item }}</v-list-item>
                  </v-list>
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2" color="blue">mdi-folder-plus</v-icon>
                  {{ t('help.smart_query.categorySetup.step2.heading') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <p class="mb-2">{{ t('help.smart_query.categorySetup.step2.description') }}</p>
                  <v-list density="compact">
                    <v-list-item v-for="(item, index) in (t('help.smart_query.categorySetup.step2.items') as string[])" :key="index">{{ item }}</v-list-item>
                  </v-list>
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2" color="green">mdi-web</v-icon>
                  {{ t('help.smart_query.categorySetup.step3.heading') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <p class="mb-2">{{ t('help.smart_query.categorySetup.step3.description') }}</p>
                  <v-list density="compact">
                    <v-list-item v-for="(item, index) in (t('help.smart_query.categorySetup.step3.items') as string[])" :key="index">{{ item }}</v-list-item>
                  </v-list>
                  <v-alert type="info" variant="tonal" density="compact" class="mt-2">
                    {{ t('help.smart_query.categorySetup.step3.important') }}
                  </v-alert>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>

            <h3 class="text-h6 mb-3">{{ t('help.smart_query.write_mode_workflow.title') }}</h3>
            <v-timeline density="compact" side="end" class="mb-4">
              <v-timeline-item dot-color="primary" size="small">
                <template v-slot:opposite><strong>1</strong></template>
                <div>
                  <strong>{{ t('help.smart_query.write_mode_workflow.step1.title') }}</strong><br>
                  {{ t('help.smart_query.write_mode_workflow.step1.description') }}
                </div>
              </v-timeline-item>
              <v-timeline-item dot-color="warning" size="small">
                <template v-slot:opposite><strong>2</strong></template>
                <div>
                  <strong>{{ t('help.smart_query.write_mode_workflow.step2.title') }}</strong><br>
                  {{ t('help.smart_query.write_mode_workflow.step2.description') }}
                </div>
              </v-timeline-item>
              <v-timeline-item dot-color="info" size="small">
                <template v-slot:opposite><strong>3</strong></template>
                <div>
                  <strong>{{ t('help.smart_query.write_mode_workflow.step3.title') }}</strong><br>
                  {{ t('help.smart_query.write_mode_workflow.step3.description') }}
                </div>
              </v-timeline-item>
              <v-timeline-item dot-color="success" size="small">
                <template v-slot:opposite><strong>4</strong></template>
                <div>
                  <strong>{{ t('help.smart_query.write_mode_workflow.step4.title') }}</strong><br>
                  {{ t('help.smart_query.write_mode_workflow.step4.description') }}
                </div>
              </v-timeline-item>
              <v-timeline-item dot-color="purple" size="small">
                <template v-slot:opposite><strong>5</strong></template>
                <div>
                  <strong>{{ t('help.smart_query.write_mode_workflow.step5.title') }}</strong><br>
                  {{ t('help.smart_query.write_mode_workflow.step5.description') }}
                </div>
              </v-timeline-item>
            </v-timeline>

            <h3 class="text-h6 mb-3">{{ t('help.smart_query.geographic_filters.title') }}</h3>
            <p class="mb-3">{{ t('help.smart_query.geographic_filters.description') }}</p>
            <v-table density="compact" class="mb-4">
              <thead><tr><th>{{ t('help.smart_query.geographic_filters.table.input') }}</th><th>{{ t('help.smart_query.geographic_filters.table.recognized_as') }}</th></tr></thead>
              <tbody>
                <tr v-for="(example, index) in (t('help.smart_query.geographic_filters.examples') as any[])" :key="index">
                  <td>{{ example.input }}</td>
                  <td>{{ example.output }}</td>
                </tr>
              </tbody>
            </v-table>

            <h3 class="text-h6 mb-3">{{ t('help.smart_query.example_queries.title') }}</h3>
            <v-table density="compact">
              <thead><tr><th>{{ t('help.smart_query.example_queries.table.query') }}</th><th>{{ t('help.smart_query.example_queries.table.mode') }}</th><th>{{ t('help.smart_query.example_queries.table.result') }}</th></tr></thead>
              <tbody>
                <tr v-for="(example, index) in (t('help.smart_query.example_queries.examples') as any[])" :key="index">
                  <td>"{{ example.query }}"</td>
                  <td><v-chip size="x-small" :color="example.mode === 'read' ? 'info' : 'warning'">{{ example.mode === 'read' ? t('help.smart_query.example_queries.read') : t('help.smart_query.example_queries.write') }}</v-chip></td>
                  <td>{{ example.result }}</td>
                </tr>
              </tbody>
            </v-table>
          </v-card-text>
        </v-card>

        <!-- Kategorien -->
        <v-card id="categories" class="mb-4">
          <v-card-title class="text-h5 bg-purple">
            <v-icon class="mr-2">mdi-folder-multiple</v-icon>
            {{ t('help.categories.title') }}
          </v-card-title>
          <v-card-text class="pt-4">
            <p class="mb-4">{{ t('help.categories.description') }}</p>

            <v-expansion-panels variant="accordion">
              <v-expansion-panel :title="t('help.categories.basicSettings.title')">
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <thead><tr><th>{{ t('common.field') }}</th><th>{{ t('common.description') }}</th><th>{{ t('common.example') }}</th></tr></thead>
                    <tbody>
                      <tr><td><strong>{{ t('help.categories.basicSettings.name') }}</strong></td><td>{{ t('help.categories.basicSettings.nameDesc') }}</td><td>{{ t('help.categories.basicSettings.nameExample') }}</td></tr>
                      <tr><td><strong>{{ t('help.categories.basicSettings.description') }}</strong></td><td>{{ t('help.categories.basicSettings.descriptionDesc') }}</td><td>{{ t('help.categories.basicSettings.descriptionExample') }}</td></tr>
                      <tr><td><strong>{{ t('help.categories.basicSettings.purpose') }}</strong></td><td>{{ t('help.categories.basicSettings.purposeDesc') }}</td><td>{{ t('help.categories.basicSettings.purposeExample') }}</td></tr>
                      <tr><td><strong>{{ t('help.categories.basicSettings.status') }}</strong></td><td>{{ t('help.categories.basicSettings.statusDesc') }}</td><td>{{ t('common.active') }}</td></tr>
                      <tr><td><strong>{{ t('help.categories.basicSettings.documentTypes') }}</strong></td><td>{{ t('help.categories.basicSettings.documentTypesDesc') }}</td><td>{{ t('help.categories.basicSettings.documentTypesExample') }}</td></tr>
                      <tr><td><strong>{{ t('help.categories.basicSettings.schedule') }}</strong></td><td>{{ t('help.categories.basicSettings.scheduleDesc') }}</td><td>{{ t('help.categories.basicSettings.scheduleExample') }}</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel :title="t('help.categories.searchTerms.title')">
                <v-expansion-panel-text>
                  <p class="mb-2">{{ t('help.categories.searchTerms.description') }}</p>
                  <v-chip-group>
                    <v-chip size="small">windkraft</v-chip>
                    <v-chip size="small">windenergie</v-chip>
                    <v-chip size="small">windpark</v-chip>
                    <v-chip size="small">repowering</v-chip>
                    <v-chip size="small">flächennutzungsplan</v-chip>
                    <v-chip size="small">bebauungsplan</v-chip>
                  </v-chip-group>
                  <v-alert type="info" variant="tonal" density="compact" class="mt-3">
                    {{ t('help.categories.searchTerms.info') }}
                  </v-alert>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel :title="t('help.categories.urlFilters.title')">
                <v-expansion-panel-text>
                  <v-alert type="info" variant="tonal" density="compact" class="mb-3" :text="t('help.categories.urlFilters.info')" />

                  <h4 class="mb-2"><v-icon color="error" size="small">mdi-close</v-icon> {{ t('help.categories.urlFilters.excludeTitle') }}</h4>
                  <p class="text-body-2 mb-2">{{ t('help.categories.urlFilters.excludeDesc') }}</p>
                  <v-chip-group class="mb-3">
                    <v-chip size="small" color="error" variant="outlined">/impressum</v-chip>
                    <v-chip size="small" color="error" variant="outlined">/datenschutz</v-chip>
                    <v-chip size="small" color="error" variant="outlined">/login</v-chip>
                    <v-chip size="small" color="error" variant="outlined">/archiv</v-chip>
                    <v-chip size="small" color="error" variant="outlined">/suche</v-chip>
                  </v-chip-group>

                  <h4 class="mb-2"><v-icon color="success" size="small">mdi-check</v-icon> {{ t('help.categories.urlFilters.includeTitle') }}</h4>
                  <p class="text-body-2 mb-2">{{ t('help.categories.urlFilters.includeDesc') }}</p>
                  <v-chip-group>
                    <v-chip size="small" color="grey" variant="outlined">/ratsinformation/</v-chip>
                    <v-chip size="small" color="grey" variant="outlined">/beschluesse/</v-chip>
                  </v-chip-group>

                  <v-alert type="warning" variant="tonal" density="compact" class="mt-3" :text="t('help.categories.urlFilters.recommendation')" />
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel :title="t('help.categories.aiPrompt.title')">
                <v-expansion-panel-text>
                  <p class="mb-2">{{ t('help.categories.aiPrompt.description') }}</p>
                  <v-code class="pa-3 d-block text-caption" style="white-space: pre-wrap;">Analysiere das Dokument und extrahiere:
{
  "topic": "Hauptthema",
  "summary": "Zusammenfassung",
  "is_relevant": true/false,
  "municipality": "Gemeinde",
  "pain_points": ["Kritische Punkte"],
  "positive_signals": ["Positive Signale/Chancen"],
  "decision_makers": [{"person": "Name", "role": "Position"}],
  "sentiment": "positiv/neutral/negativ"
}</v-code>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>

            <h3 class="text-h6 mt-4 mb-3">{{ t('help.categories.actions.title') }}</h3>
            <v-table density="compact">
              <thead><tr><th>{{ t('common.actions') }}</th><th>{{ t('common.icon') }}</th><th>{{ t('common.description') }}</th></tr></thead>
              <tbody>
                <tr><td>{{ t('help.categories.actions.edit') }}</td><td><v-icon size="small">mdi-pencil</v-icon></td><td>{{ t('help.categories.actions.editDesc') }}</td></tr>
                <tr><td>{{ t('help.categories.actions.crawl') }}</td><td><v-icon size="small" color="success">mdi-play</v-icon></td><td>{{ t('help.categories.actions.crawlDesc') }}</td></tr>
                <tr><td>{{ t('help.categories.actions.reanalyze') }}</td><td><v-icon size="small" color="warning">mdi-refresh</v-icon></td><td>{{ t('help.categories.actions.reanalyzeDesc') }}</td></tr>
                <tr><td>{{ t('help.categories.actions.delete') }}</td><td><v-icon size="small" color="error">mdi-delete</v-icon></td><td>{{ t('help.categories.actions.deleteDesc') }}</td></tr>
              </tbody>
            </v-table>
          </v-card-text>
        </v-card>

        <!-- Datenquellen -->
        <v-card id="sources" class="mb-4">
          <v-card-title class="text-h5 bg-teal">
            <v-icon class="mr-2">mdi-web</v-icon>
            {{ t('help.sources.title') }}
          </v-card-title>
          <v-card-text class="pt-4">
            <p class="mb-4">{{ t('help.sources.description') }}</p>

            <h3 class="text-h6 mb-3">{{ t('help.sources.categoryAssignment.title') }}</h3>
            <v-alert type="info" variant="tonal" class="mb-3" :text="t('help.sources.categoryAssignment.info')" />
            <v-list density="compact" class="mb-4">
              <v-list-item prepend-icon="mdi-link-variant">
                <v-list-item-title>{{ t('help.sources.categoryAssignment.multipleAssignment') }}</v-list-item-title>
                <v-list-item-subtitle>{{ t('help.sources.categoryAssignment.multipleAssignmentDesc') }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-play-circle">
                <v-list-item-title>{{ t('help.sources.categoryAssignment.crawlContext') }}</v-list-item-title>
                <v-list-item-subtitle>{{ t('help.sources.categoryAssignment.crawlContextDesc') }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-brain">
                <v-list-item-title>{{ t('help.sources.categoryAssignment.smartQueryIntegration') }}</v-list-item-title>
                <v-list-item-subtitle>{{ t('help.sources.categoryAssignment.smartQueryIntegrationDesc') }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>

            <h3 class="text-h6 mb-3">{{ t('help.sources.sourceTypes.title') }}</h3>
            <v-row class="mb-4">
              <v-col cols="12" md="4">
                <v-card variant="outlined" class="pa-3">
                  <v-chip color="primary" class="mb-2">{{ t('help.sources.sourceTypes.website') }}</v-chip>
                  <div class="text-body-2">{{ t('help.sources.sourceTypes.websiteDesc') }}</div>
                </v-card>
              </v-col>
              <v-col cols="12" md="4">
                <v-card variant="outlined" class="pa-3">
                  <v-chip color="success" class="mb-2">{{ t('help.sources.sourceTypes.oparlApi') }}</v-chip>
                  <div class="text-body-2">{{ t('help.sources.sourceTypes.oparlApiDesc') }}</div>
                </v-card>
              </v-col>
              <v-col cols="12" md="4">
                <v-card variant="outlined" class="pa-3">
                  <v-chip color="warning" class="mb-2">{{ t('help.sources.sourceTypes.rss') }}</v-chip>
                  <div class="text-body-2">{{ t('help.sources.sourceTypes.rssDesc') }}</div>
                </v-card>
              </v-col>
            </v-row>

            <h3 class="text-h6 mb-3">{{ t('help.sources.availableFilters') }}</h3>
            <p class="mb-3">{{ t('help.sources.filterDescription', 'Land, Gemeinde, Kategorie, Status, Suche') }}</p>

            <h3 class="text-h6 mb-3">{{ t('help.sources.actions.title') }}</h3>
            <v-table density="compact" class="mb-4">
              <thead><tr><th>{{ t('common.button') }}</th><th>{{ t('common.description') }}</th></tr></thead>
              <tbody>
                <tr><td><v-chip size="small" color="secondary">{{ t('help.sources.actions.bulkImport') }}</v-chip></td><td>{{ t('help.sources.actions.bulkImportDesc') }}</td></tr>
                <tr><td><v-chip size="small" color="primary">{{ t('help.sources.actions.newSource') }}</v-chip></td><td>{{ t('help.sources.actions.newSourceDesc') }}</td></tr>
                <tr><td><v-icon size="small">mdi-pencil</v-icon> {{ t('help.sources.actions.edit') }}</td><td>{{ t('help.sources.actions.editDesc') }}</td></tr>
                <tr><td><v-icon size="small" color="success">mdi-play</v-icon> {{ t('help.sources.actions.crawl') }}</td><td>{{ t('help.sources.actions.crawlDesc') }}</td></tr>
                <tr><td><v-icon size="small" color="warning">mdi-refresh</v-icon> {{ t('help.sources.actions.reset') }}</td><td>{{ t('help.sources.actions.resetDesc') }}</td></tr>
                <tr><td><v-icon size="small" color="error">mdi-delete</v-icon> {{ t('help.sources.actions.delete') }}</td><td>{{ t('help.sources.actions.deleteDesc') }}</td></tr>
              </tbody>
            </v-table>

            <h3 class="text-h6 mb-3">{{ t('help.sources.formFields.title') }}</h3>
            <v-table density="compact" class="mb-4">
              <thead><tr><th>{{ t('common.field') }}</th><th>{{ t('common.description') }}</th><th>{{ t('common.required') }}</th></tr></thead>
              <tbody>
                <tr><td><strong>{{ t('help.sources.formFields.category') }}</strong></td><td>{{ t('help.sources.formFields.categoryDesc') }}</td><td>{{ t('help.sources.formFields.required') }}</td></tr>
                <tr><td><strong>{{ t('help.sources.formFields.name') }}</strong></td><td>{{ t('help.sources.formFields.nameDesc') }}</td><td>{{ t('help.sources.formFields.required') }}</td></tr>
                <tr><td><strong>{{ t('help.sources.formFields.sourceType') }}</strong></td><td>{{ t('help.sources.formFields.sourceTypeDesc') }}</td><td>{{ t('help.sources.formFields.required') }}</td></tr>
                <tr><td><strong>{{ t('help.sources.formFields.baseUrl') }}</strong></td><td>{{ t('help.sources.formFields.baseUrlDesc') }}</td><td>{{ t('help.sources.formFields.required') }}</td></tr>
                <tr><td><strong>{{ t('help.sources.formFields.apiEndpoint') }}</strong></td><td>{{ t('help.sources.formFields.apiEndpointDesc') }}</td><td>{{ t('help.sources.formFields.optional') }}</td></tr>
                <tr><td><strong>{{ t('help.sources.formFields.country') }}</strong></td><td>{{ t('help.sources.formFields.countryDesc') }}</td><td>{{ t('help.sources.formFields.optional') }}</td></tr>
                <tr><td><strong>{{ t('help.sources.formFields.location') }}</strong></td><td>{{ t('help.sources.formFields.locationDesc') }}</td><td>{{ t('help.sources.formFields.optional') }}</td></tr>
              </tbody>
            </v-table>

            <h3 class="text-h6 mb-3">{{ t('help.sources.bulkImport.title') }}</h3>
            <v-alert type="info" variant="tonal" class="mb-4">
              {{ t('help.sources.bulkImport.info') }}
              <ol class="mt-2 pl-4">
                <li>{{ t('help.sources.bulkImport.step1') }}</li>
                <li>{{ t('help.sources.bulkImport.step2') }}</li>
              </ol>
              <v-code class="mt-2 pa-2 d-block text-caption">[
  {"name": "Stadt X", "base_url": "https://...", "location_name": "Stadt X"},
  {"name": "Stadt Y", "base_url": "https://...", "location_name": "Stadt Y"}
]</v-code>
            </v-alert>

            <h3 class="text-h6 mb-3">{{ t('help.sources.crawlConfig.title') }}</h3>
            <v-table density="compact" class="mb-4">
              <thead><tr><th>{{ t('common.setting') }}</th><th>{{ t('common.description') }}</th><th>{{ t('common.default') }}</th></tr></thead>
              <tbody>
                <tr><td><strong>{{ t('help.sources.crawlConfig.maxDepth') }}</strong></td><td>{{ t('help.sources.crawlConfig.maxDepthDesc') }}</td><td>{{ t('help.sources.crawlConfig.maxDepthDefault') }}</td></tr>
                <tr><td><strong>{{ t('help.sources.crawlConfig.maxPages') }}</strong></td><td>{{ t('help.sources.crawlConfig.maxPagesDesc') }}</td><td>{{ t('help.sources.crawlConfig.maxPagesDefault') }}</td></tr>
                <tr><td><strong>{{ t('help.sources.crawlConfig.externalLinks') }}</strong></td><td>{{ t('help.sources.crawlConfig.externalLinksDesc') }}</td><td>{{ t('help.sources.crawlConfig.externalLinksDefault') }}</td></tr>
                <tr><td><strong>{{ t('help.sources.crawlConfig.renderJs') }}</strong></td><td>{{ t('help.sources.crawlConfig.renderJsDesc') }}</td><td>{{ t('help.sources.crawlConfig.renderJsDefault') }}</td></tr>
                <tr><td><strong>{{ t('help.sources.crawlConfig.htmlCapture') }}</strong></td><td>{{ t('help.sources.crawlConfig.htmlCaptureDesc') }}</td><td>{{ t('help.sources.crawlConfig.htmlCaptureDefault') }}</td></tr>
              </tbody>
            </v-table>

            <h3 class="text-h6 mb-3">{{ t('help.sources.urlFiltersAdvanced.title') }}</h3>
            <v-alert type="info" variant="tonal" class="mb-3">
              {{ t('help.sources.urlFiltersAdvanced.info') }}
            </v-alert>
            <v-row class="mb-4">
              <v-col cols="12" md="6">
                <v-card variant="outlined" class="pa-3" color="error">
                  <div class="text-subtitle-2 mb-2"><v-icon color="error">mdi-close</v-icon> {{ t('help.sources.urlFiltersAdvanced.excludeTitle') }}</div>
                  <div class="text-body-2">{{ t('help.sources.urlFiltersAdvanced.excludeDesc') }}</div>
                  <v-chip-group class="mt-2">
                    <v-chip size="small">/impressum</v-chip>
                    <v-chip size="small">/datenschutz</v-chip>
                    <v-chip size="small">/login</v-chip>
                    <v-chip size="small">/archiv</v-chip>
                  </v-chip-group>
                </v-card>
              </v-col>
              <v-col cols="12" md="6">
                <v-card variant="outlined" class="pa-3" color="grey">
                  <div class="text-subtitle-2 mb-2"><v-icon color="grey">mdi-check</v-icon> {{ t('help.sources.urlFiltersAdvanced.includeTitle') }}</div>
                  <div class="text-body-2">{{ t('help.sources.urlFiltersAdvanced.includeDesc') }}</div>
                  <v-chip-group class="mt-2">
                    <v-chip size="small" variant="outlined">/dokumente/</v-chip>
                    <v-chip size="small" variant="outlined">/beschluesse/</v-chip>
                  </v-chip-group>
                </v-card>
              </v-col>
            </v-row>

            <h3 class="text-h6 mb-3">{{ t('help.sources.statusMeaning.title') }}</h3>
            <v-table density="compact">
              <thead><tr><th>{{ t('common.status') }}</th><th>{{ t('common.meaning') }}</th></tr></thead>
              <tbody>
                <tr><td><v-chip size="small" color="grey">{{ t('help.sources.statusMeaning.pending') }}</v-chip></td><td>{{ t('help.sources.statusMeaning.pendingDesc') }}</td></tr>
                <tr><td><v-chip size="small" color="info">{{ t('help.sources.statusMeaning.crawling') }}</v-chip></td><td>{{ t('help.sources.statusMeaning.crawlingDesc') }}</td></tr>
                <tr><td><v-chip size="small" color="success">{{ t('help.sources.statusMeaning.active') }}</v-chip></td><td>{{ t('help.sources.statusMeaning.activeDesc') }}</td></tr>
                <tr><td><v-chip size="small" color="error">{{ t('help.sources.statusMeaning.error') }}</v-chip></td><td>{{ t('help.sources.statusMeaning.errorDesc') }}</td></tr>
              </tbody>
            </v-table>
          </v-card-text>
        </v-card>

        <!-- Crawler -->
        <v-card id="crawler" class="mb-4">
          <v-card-title class="text-h5 bg-cyan">
            <v-icon class="mr-2">mdi-robot</v-icon>
            {{ t('help.crawler.title') }}
          </v-card-title>
          <v-card-text class="pt-4">
            <p class="mb-4">{{ t('help.crawler.description') }}</p>

            <h3 class="text-h6 mb-3">{{ t('help.crawler.statusCards') }}</h3>
            <v-row class="mb-4">
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-3">
                  <v-icon color="success" size="32">mdi-account-hard-hat</v-icon>
                  <div class="text-subtitle-1">{{ t('help.crawler.cards.activeWorkers') }}</div>
                  <div class="text-caption">{{ t('help.crawler.cards.activeWorkersDesc') }}</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-3">
                  <v-icon color="info" size="32">mdi-run</v-icon>
                  <div class="text-subtitle-1">{{ t('help.crawler.cards.runningJobs') }}</div>
                  <div class="text-caption">{{ t('help.crawler.cards.runningJobsDesc') }}</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-3">
                  <v-icon color="warning" size="32">mdi-clock-outline</v-icon>
                  <div class="text-subtitle-1">{{ t('help.crawler.cards.pendingJobs') }}</div>
                  <div class="text-caption">{{ t('help.crawler.cards.pendingJobsDesc') }}</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-3">
                  <v-icon color="primary" size="32">mdi-file-document-multiple</v-icon>
                  <div class="text-subtitle-1">{{ t('help.crawler.cards.documents') }}</div>
                  <div class="text-caption">{{ t('help.crawler.cards.documentsDesc') }}</div>
                </v-card>
              </v-col>
            </v-row>

            <h3 class="text-h6 mb-3">{{ t('help.crawler.aiTasks.title') }}</h3>
            <v-alert type="info" variant="tonal" class="mb-3">
              {{ t('help.crawler.aiTasks.info') }}
              <v-list density="compact" class="bg-transparent">
                <v-list-item prepend-icon="mdi-brain">{{ t('help.crawler.aiTasks.items[0]') }}</v-list-item>
                <v-list-item prepend-icon="mdi-progress-check">{{ t('help.crawler.aiTasks.items[1]') }}</v-list-item>
                <v-list-item prepend-icon="mdi-stop"><v-chip size="x-small" color="error">{{ t('help.crawler.stopButton') }}</v-chip> {{ t('help.crawler.aiTasks.items[2]') }}</v-list-item>
              </v-list>
            </v-alert>

            <h3 class="text-h6 mb-3">{{ t('help.crawler.activeCrawlers.title') }}</h3>
            <p class="mb-2">{{ t('help.crawler.activeCrawlers.description') }}</p>
            <v-list density="compact" class="mb-4">
              <v-list-item prepend-icon="mdi-web">
                <v-list-item-title>{{ t('help.crawler.activeCrawlers.items[0]') }}</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-file-document">
                <v-list-item-title>{{ t('help.crawler.activeCrawlers.items[1]') }}</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-alert">
                <v-list-item-title>{{ t('help.crawler.activeCrawlers.items[2]') }}</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-stop">
                <v-list-item-title><v-chip size="x-small" color="error">{{ t('help.crawler.stopButton') }}</v-chip> {{ t('help.crawler.activeCrawlers.items[3]') }}</v-list-item-title>
              </v-list-item>
            </v-list>

            <h4 class="text-subtitle-1 mb-2">{{ t('help.crawler.activeCrawlers.liveLog') }}</h4>
            <v-alert type="info" variant="tonal" density="compact" class="mb-4">
              {{ t('help.crawler.activeCrawlers.liveLogDesc') }}
            </v-alert>

            <h3 class="text-h6 mb-3">{{ t('help.crawler.jobTable.title') }}</h3>
            <v-table density="compact" class="mb-4">
              <thead><tr><th>{{ t('help.crawler.jobTable.columnHeader') }}</th><th>{{ t('help.crawler.jobTable.descriptionHeader') }}</th></tr></thead>
              <tbody>
                <tr><td><strong>{{ t('help.crawler.jobTable.source') }}</strong></td><td>{{ t('help.crawler.jobTable.sourceDesc') }}</td></tr>
                <tr><td><strong>{{ t('help.crawler.jobTable.status') }}</strong></td><td>{{ t('help.crawler.jobTable.statusDesc') }}</td></tr>
                <tr><td><strong>{{ t('help.crawler.jobTable.started') }}</strong></td><td>{{ t('help.crawler.jobTable.startedDesc') }}</td></tr>
                <tr><td><strong>{{ t('help.crawler.jobTable.duration') }}</strong></td><td>{{ t('help.crawler.jobTable.durationDesc') }}</td></tr>
                <tr><td><strong>{{ t('help.crawler.jobTable.progress') }}</strong></td><td>{{ t('help.crawler.jobTable.progressDesc') }}</td></tr>
                <tr><td><strong>{{ t('help.crawler.jobTable.actions') }}</strong></td><td>{{ t('help.crawler.jobTable.actionsDesc') }}</td></tr>
              </tbody>
            </v-table>

            <h3 class="text-h6 mb-3">{{ t('help.crawler.jobDetails.title') }}</h3>
            <p class="mb-2">{{ t('help.crawler.jobDetails.description') }}</p>
            <v-row class="mb-3">
              <v-col cols="12" md="6">
                <v-list density="compact">
                  <v-list-item prepend-icon="mdi-web"><v-list-item-title>{{ t('help.crawler.jobDetails.info[0]') }}</v-list-item-title></v-list-item>
                  <v-list-item prepend-icon="mdi-check-circle"><v-list-item-title>{{ t('help.crawler.jobDetails.info[1]') }}</v-list-item-title></v-list-item>
                  <v-list-item prepend-icon="mdi-clock"><v-list-item-title>{{ t('help.crawler.jobDetails.info[2]') }}</v-list-item-title></v-list-item>
                </v-list>
              </v-col>
              <v-col cols="12" md="6">
                <v-card variant="outlined" class="pa-2">
                  <div class="text-subtitle-2 mb-2">{{ t('help.crawler.jobDetails.statistics') }}</div>
                  <v-chip size="small" class="mr-1">{{ t('help.crawler.jobDetails.stats[0]') }}</v-chip>
                  <v-chip size="small" class="mr-1" color="success">{{ t('help.crawler.jobDetails.stats[1]') }}</v-chip>
                  <v-chip size="small" color="info">{{ t('help.crawler.jobDetails.stats[2]') }}</v-chip>
                </v-card>
              </v-col>
            </v-row>
            <v-alert type="warning" variant="tonal" density="compact" class="mb-4">
              {{ t('help.crawler.jobDetails.errorLog') }}
            </v-alert>

            <h3 class="text-h6 mt-4 mb-3">{{ t('help.crawler.statusFilter') }}</h3>
            <v-btn-toggle class="mb-2" density="compact" variant="outlined">
              <v-btn size="small">{{ t('help.crawler.filterButtons.all') }}</v-btn>
              <v-btn size="small" color="info">{{ t('help.crawler.filterButtons.running') }}</v-btn>
              <v-btn size="small" color="success">{{ t('help.crawler.filterButtons.completed') }}</v-btn>
              <v-btn size="small" color="error">{{ t('help.crawler.filterButtons.failed') }}</v-btn>
            </v-btn-toggle>
          </v-card-text>
        </v-card>

        <!-- Dokumente -->
        <v-card id="documents" class="mb-4">
          <v-card-title class="text-h5 bg-blue-grey">
            <v-icon class="mr-2">mdi-file-document-multiple</v-icon>
            {{ t('help.documents.title') }}
          </v-card-title>
          <v-card-text class="pt-4">
            <p class="mb-4">{{ t('help.documents.description') }}</p>

            <h3 class="text-h6 mb-3">{{ t('help.documents.statusOverview') }}</h3>
            <div class="d-flex flex-wrap ga-2 mb-4">
              <v-chip color="warning" variant="tonal">
                <v-icon start size="small">mdi-clock-outline</v-icon>
                {{ t('help.documents.statuses.pending') }}
              </v-chip>
              <v-chip color="info" variant="tonal">
                <v-icon start size="small">mdi-cog-sync</v-icon>
                {{ t('help.documents.statuses.processing') }}
              </v-chip>
              <v-chip color="success" variant="tonal">
                <v-icon start size="small">mdi-check-circle</v-icon>
                {{ t('help.documents.statuses.completed') }}
              </v-chip>
              <v-chip color="grey" variant="tonal">
                <v-icon start size="small">mdi-filter-remove</v-icon>
                {{ t('help.documents.statuses.filtered') }}
              </v-chip>
              <v-chip color="error" variant="tonal">
                <v-icon start size="small">mdi-alert-circle</v-icon>
                {{ t('help.documents.statuses.failed') }}
              </v-chip>
            </div>

            <h3 class="text-h6 mb-3">{{ t('help.documents.actionButtons.title') }}</h3>
            <v-table density="compact">
              <thead><tr><th>{{ t('common.button') }}</th><th>{{ t('common.description') }}</th></tr></thead>
              <tbody>
                <tr><td><v-chip size="small" color="primary">{{ t('help.documents.actionButtons.processPending') }}</v-chip></td><td>{{ t('help.documents.actionButtons.processPendingDesc') }}</td></tr>
                <tr><td><v-chip size="small" color="warning">{{ t('help.documents.actionButtons.analyzeFiltered') }}</v-chip></td><td>{{ t('help.documents.actionButtons.analyzeFilteredDesc') }}</td></tr>
                <tr><td><v-chip size="small" color="error">{{ t('help.documents.actionButtons.stopProcessing') }}</v-chip></td><td>{{ t('help.documents.actionButtons.stopProcessingDesc') }}</td></tr>
              </tbody>
            </v-table>

            <h3 class="text-h6 mt-4 mb-3">{{ t('help.documents.availableFilters') }}</h3>
            <v-chip-group>
              <v-chip size="small" variant="outlined" v-for="(filter, index) in t('help.documents.filters')" :key="index">
                {{ filter }}
              </v-chip>
            </v-chip-group>

            <h3 class="text-h6 mt-4 mb-3">{{ t('help.documents.documentDetails.title') }}</h3>
            <v-expansion-panels variant="accordion">
              <v-expansion-panel :title="t('help.documents.documentDetails.tabInfo')">
                <v-expansion-panel-text>
                  <ul class="pl-4">
                    <li v-for="(item, index) in t('help.documents.documentDetails.tabInfoItems')" :key="index">
                      {{ item }}
                    </li>
                  </ul>
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel :title="t('help.documents.documentDetails.tabText')">
                <v-expansion-panel-text>
                  {{ t('help.documents.documentDetails.tabTextDesc') }}
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel :title="t('help.documents.documentDetails.tabExtracted')">
                <v-expansion-panel-text>
                  <ul class="pl-4">
                    <li v-for="(item, index) in t('help.documents.documentDetails.tabExtractedItems')" :key="index">
                      {{ item }}
                    </li>
                  </ul>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </v-card-text>
        </v-card>

        <!-- Gemeinden -->
        <v-card id="municipalities" class="mb-4">
          <v-card-title class="text-h5 bg-indigo">
            <v-icon class="mr-2">mdi-city</v-icon>
            {{ t('help.municipalities.title') }}
          </v-card-title>
          <v-card-text class="pt-4">
            <p class="mb-4">{{ t('help.municipalities.description') }}</p>

            <h3 class="text-h6 mb-3">{{ t('help.municipalities.statisticsCards') }}</h3>
            <v-row class="mb-4">
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-2">
                  <div class="text-subtitle-1">{{ t('help.municipalities.cards.municipalities') }}</div>
                  <div class="text-caption">{{ t('help.municipalities.cards.municipalitiesDesc') }}</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-2" color="primary">
                  <div class="text-subtitle-1">{{ t('help.municipalities.cards.documents') }}</div>
                  <div class="text-caption">{{ t('help.municipalities.cards.documentsDesc') }}</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-2" color="success">
                  <div class="text-subtitle-1">{{ t('help.municipalities.cards.relevant') }}</div>
                  <div class="text-caption">{{ t('help.municipalities.cards.relevantDesc') }}</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-2" color="warning">
                  <div class="text-subtitle-1">{{ t('help.municipalities.cards.highPriority') }}</div>
                  <div class="text-caption">{{ t('help.municipalities.cards.highPriorityDesc') }}</div>
                </v-card>
              </v-col>
            </v-row>

            <h3 class="text-h6 mb-3">{{ t('help.municipalities.tableColumns.title') }}</h3>
            <v-table density="compact" class="mb-4">
              <thead><tr><th>{{ t('help.municipalities.tableColumns.columnHeader') }}</th><th>{{ t('help.municipalities.tableColumns.descriptionHeader') }}</th></tr></thead>
              <tbody>
                <tr><td><v-icon size="small">mdi-city</v-icon> <strong>{{ t('help.municipalities.tableColumns.name') }}</strong></td><td>{{ t('help.municipalities.tableColumns.nameDesc') }}</td></tr>
                <tr><td><strong>{{ t('help.municipalities.tableColumns.adminLevels') }}</strong></td><td>{{ t('help.municipalities.tableColumns.adminLevelsDesc') }}</td></tr>
                <tr><td><v-chip size="x-small" color="info">{{ t('help.municipalities.tableColumns.sources') }}</v-chip></td><td>{{ t('help.municipalities.tableColumns.sourcesDesc') }}</td></tr>
                <tr><td><strong>{{ t('help.municipalities.tableColumns.documents') }}</strong></td><td>{{ t('help.municipalities.tableColumns.documentsDesc') }}</td></tr>
                <tr><td><strong>{{ t('help.municipalities.tableColumns.confidence') }}</strong></td><td>{{ t('help.municipalities.tableColumns.confidenceDesc') }}</td></tr>
                <tr><td><v-chip size="x-small" color="info">{{ t('help.municipalities.tableColumns.decisionMakers') }}</v-chip></td><td>{{ t('help.municipalities.tableColumns.decisionMakersDesc') }}</td></tr>
              </tbody>
            </v-table>

            <h3 class="text-h6 mb-3">{{ t('help.municipalities.filters') }}</h3>
            <v-chip-group class="mb-4">
              <v-chip size="small" variant="outlined">{{ t('help.municipalities.filterList[0]') }}</v-chip>
              <v-chip size="small" variant="outlined">{{ t('help.municipalities.filterList[1]') }}</v-chip>
              <v-chip size="small" variant="outlined">{{ t('help.municipalities.filterList[2]') }}</v-chip>
              <v-chip size="small" variant="outlined">{{ t('help.municipalities.filterList[3]') }}</v-chip>
              <v-chip size="small" variant="outlined">{{ t('help.municipalities.filterList[4]') }}</v-chip>
              <v-chip size="small" variant="outlined">{{ t('help.municipalities.filterList[5]') }}</v-chip>
            </v-chip-group>

            <h3 class="text-h6 mb-3">{{ t('help.municipalities.municipalityReport.title') }}</h3>
            <p class="mb-2">{{ t('help.municipalities.municipalityReport.description') }}</p>

            <v-alert type="info" variant="tonal" class="mb-3">
              <strong>{{ t('help.municipalities.municipalityReport.reportHeader') }}</strong>
            </v-alert>

            <h4 class="text-subtitle-1 mb-2">{{ t('help.municipalities.municipalityReport.overviewCards') }}</h4>
            <v-row class="mb-3">
              <v-col cols="3"><v-chip size="small" variant="outlined">{{ t('help.municipalities.municipalityReport.overviewCardLabels.documents') }}</v-chip></v-col>
              <v-col cols="3"><v-chip size="small" variant="outlined" color="success">{{ t('help.municipalities.municipalityReport.overviewCardLabels.relevant') }}</v-chip></v-col>
              <v-col cols="3"><v-chip size="small" variant="outlined">{{ t('help.municipalities.municipalityReport.overviewCardLabels.confidence') }}</v-chip></v-col>
              <v-col cols="3"><v-chip size="small" variant="outlined" color="warning">{{ t('help.municipalities.municipalityReport.overviewCardLabels.priority') }}</v-chip></v-col>
            </v-row>

            <h4 class="text-subtitle-1 mb-2">{{ t('help.municipalities.municipalityReport.reportTabs') }}</h4>
            <v-expansion-panels variant="accordion" class="mb-4">
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2">mdi-account-group</v-icon> {{ t('help.municipalities.municipalityReport.tabs.decisionMakers') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  {{ t('help.municipalities.municipalityReport.tabs.decisionMakersDesc') }}
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2" color="error">mdi-alert</v-icon> {{ t('help.municipalities.municipalityReport.tabs.painPoints') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  {{ t('help.municipalities.municipalityReport.tabs.painPointsDesc') }}
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2" color="success">mdi-thumb-up</v-icon> {{ t('help.municipalities.municipalityReport.tabs.positiveSignals') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  {{ t('help.municipalities.municipalityReport.tabs.positiveSignalsDesc') }}
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2">mdi-text</v-icon> {{ t('help.municipalities.municipalityReport.tabs.summaries') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  {{ t('help.municipalities.municipalityReport.tabs.summariesDesc') }}
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2">mdi-web</v-icon> {{ t('help.municipalities.municipalityReport.tabs.dataSources') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  {{ t('help.municipalities.municipalityReport.tabs.dataSourcesDesc') }}
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2">mdi-database-sync</v-icon> {{ t('help.municipalities.municipalityReport.tabs.pysis') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  {{ t('help.municipalities.municipalityReport.tabs.pysisDesc') }}
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>

            <h3 class="text-h6 mt-4 mb-3">{{ t('help.municipalities.locationManagement.title') }}</h3>
            <v-table density="compact">
              <thead><tr><th>{{ t('help.municipalities.locationManagement.functionColumn') }}</th><th>{{ t('help.municipalities.locationManagement.descriptionColumn') }}</th></tr></thead>
              <tbody>
                <tr><td><v-chip size="small" color="primary">{{ t('help.municipalities.locationManagement.newLocation') }}</v-chip></td><td>{{ t('help.municipalities.locationManagement.newLocationDesc') }}</td></tr>
                <tr><td><v-icon size="small">mdi-pencil</v-icon> {{ t('help.municipalities.locationManagement.edit') }}</td><td>{{ t('help.municipalities.locationManagement.editDesc') }}</td></tr>
                <tr><td><v-icon size="small">mdi-eye</v-icon> {{ t('help.municipalities.locationManagement.showReport') }}</td><td>{{ t('help.municipalities.locationManagement.showReportDesc') }}</td></tr>
                <tr><td><v-icon size="small">mdi-file-document-multiple</v-icon> {{ t('help.municipalities.locationManagement.documents') }}</td><td>{{ t('help.municipalities.locationManagement.documentsDesc') }}</td></tr>
                <tr><td><strong>{{ t('help.municipalities.locationManagement.linkSources') }}</strong></td><td>{{ t('help.municipalities.locationManagement.linkSourcesDesc') }}</td></tr>
                <tr><td><strong>{{ t('help.municipalities.locationManagement.enrichAdminLevels') }}</strong></td><td>{{ t('help.municipalities.locationManagement.enrichAdminLevelsDesc') }}</td></tr>
              </tbody>
            </v-table>
          </v-card-text>
        </v-card>

        <!-- {{ t('help.entityFacet.title') }} -->
        <v-card id="entity-facet" class="mb-4">
          <v-card-title class="text-h5 bg-deep-purple">
            <v-icon class="mr-2">mdi-database</v-icon>
            {{ t('help.entityFacet.title') }}
          </v-card-title>
          <v-card-text class="pt-4">
            <v-alert type="info" variant="tonal" class="mb-4">
              {{ t('help.entityFacet.newInfo') }}
            </v-alert>

            <h3 class="text-h6 mb-3">{{ t('help.entityFacet.concept.title') }}</h3>
            <p class="mb-4">
              {{ t('help.entityFacet.concept.description') }}
            </p>

            <v-row class="mb-4">
              <v-col cols="12" md="6">
                <v-card variant="outlined" class="h-100">
                  <v-card-title class="text-subtitle-1">
                    <v-icon class="mr-2" color="primary">mdi-cube</v-icon>
                    {{ t('help.entityFacet.concept.entities.title') }}
                  </v-card-title>
                  <v-card-text>
                    <p class="mb-2">{{ t('help.entityFacet.concept.entities.description') }}</p>
                    <v-list density="compact">
                      <v-list-item prepend-icon="mdi-city">
                        <v-list-item-title><strong>Municipality</strong> - {{ t('help.entityFacet.concept.entities.municipality') }}</v-list-item-title>
                      </v-list-item>
                      <v-list-item prepend-icon="mdi-account">
                        <v-list-item-title><strong>Person</strong> - {{ t('help.entityFacet.concept.entities.person') }}</v-list-item-title>
                      </v-list-item>
                      <v-list-item prepend-icon="mdi-domain">
                        <v-list-item-title><strong>Organization</strong> - {{ t('help.entityFacet.concept.entities.organization') }}</v-list-item-title>
                      </v-list-item>
                      <v-list-item prepend-icon="mdi-calendar">
                        <v-list-item-title><strong>Event</strong> - {{ t('help.entityFacet.concept.entities.event') }}</v-list-item-title>
                      </v-list-item>
                    </v-list>
                    <p class="text-caption mt-2">{{ t('help.entityFacet.concept.entities.note') }}</p>
                  </v-card-text>
                </v-card>
              </v-col>
              <v-col cols="12" md="6">
                <v-card variant="outlined" class="h-100">
                  <v-card-title class="text-subtitle-1">
                    <v-icon class="mr-2" color="success">mdi-tag-multiple</v-icon>
                    {{ t('help.entityFacet.concept.facets.title') }}
                  </v-card-title>
                  <v-card-text>
                    <p class="mb-2">{{ t('help.entityFacet.concept.facets.description') }}</p>
                    <v-list density="compact">
                      <v-list-item prepend-icon="mdi-alert-circle" color="error">
                        <v-list-item-title><strong>Pain Point</strong> - {{ t('help.entityFacet.concept.facets.painPoint') }}</v-list-item-title>
                      </v-list-item>
                      <v-list-item prepend-icon="mdi-thumb-up" color="success">
                        <v-list-item-title><strong>Positive Signal</strong> - {{ t('help.entityFacet.concept.facets.positiveSignal') }}</v-list-item-title>
                      </v-list-item>
                      <v-list-item prepend-icon="mdi-card-account-details">
                        <v-list-item-title><strong>Contact</strong> - {{ t('help.entityFacet.concept.facets.contact') }}</v-list-item-title>
                      </v-list-item>
                      <v-list-item prepend-icon="mdi-calendar-check">
                        <v-list-item-title><strong>Event Attendance</strong> - {{ t('help.entityFacet.concept.facets.eventAttendance') }}</v-list-item-title>
                      </v-list-item>
                    </v-list>
                    <p class="text-caption mt-2">{{ t('help.entityFacet.concept.facets.note') }}</p>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>

            <h3 class="text-h6 mb-3">{{ t('help.entityFacet.relations.title') }}</h3>
            <p class="mb-3">{{ t('help.entityFacet.relations.description') }}</p>
            <v-table density="compact" class="mb-4">
              <thead><tr><th>{{ t('help.entityFacet.relations.tableHeaders.relationType') }}</th><th>{{ t('help.entityFacet.relations.tableHeaders.description') }}</th><th>{{ t('help.entityFacet.relations.tableHeaders.example') }}</th></tr></thead>
              <tbody>
                <tr>
                  <td><strong>{{ t('help.entityFacet.relations.types.worksFor') }}</strong></td>
                  <td>{{ t('help.entityFacet.relations.types.worksForDesc') }}</td>
                  <td>{{ t('help.entityFacet.relations.types.worksForExample') }}</td>
                </tr>
                <tr>
                  <td><strong>{{ t('help.entityFacet.relations.types.memberOf') }}</strong></td>
                  <td>{{ t('help.entityFacet.relations.types.memberOfDesc') }}</td>
                  <td>{{ t('help.entityFacet.relations.types.memberOfExample') }}</td>
                </tr>
                <tr>
                  <td><strong>{{ t('help.entityFacet.relations.types.attends') }}</strong></td>
                  <td>{{ t('help.entityFacet.relations.types.attendsDesc') }}</td>
                  <td>{{ t('help.entityFacet.relations.types.attendsExample') }}</td>
                </tr>
                <tr>
                  <td><strong>{{ t('help.entityFacet.relations.types.organizes') }}</strong></td>
                  <td>{{ t('help.entityFacet.relations.types.organizesDesc') }}</td>
                  <td>{{ t('help.entityFacet.relations.types.organizesExample') }}</td>
                </tr>
              </tbody>
            </v-table>

            <h3 class="text-h6 mb-3">{{ t('help.entityFacet.timeBased.title') }}</h3>
            <v-alert type="warning" variant="tonal" class="mb-4">
              {{ t('help.entityFacet.timeBased.info') }}
              <v-list density="compact" class="bg-transparent">
                <v-list-item prepend-icon="mdi-calendar-arrow-right">
                  <v-list-item-title>{{ t('help.entityFacet.timeBased.futureOnly') }}</v-list-item-title>
                </v-list-item>
                <v-list-item prepend-icon="mdi-calendar-arrow-left">
                  <v-list-item-title>{{ t('help.entityFacet.timeBased.pastOnly') }}</v-list-item-title>
                </v-list-item>
                <v-list-item prepend-icon="mdi-calendar-range">
                  <v-list-item-title>{{ t('help.entityFacet.timeBased.all') }}</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-alert>

            <h3 class="text-h6 mb-3">{{ t('help.entityFacet.analysisTemplates.title') }}</h3>
            <p class="mb-3">
              {{ t('help.entityFacet.analysisTemplates.description') }}
            </p>
            <v-expansion-panels variant="accordion" class="mb-4">
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2">mdi-chart-timeline-variant</v-icon>
                  {{ t('help.entityFacet.analysisTemplates.painPoint.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <p>{{ t('help.entityFacet.analysisTemplates.painPoint.description') }}</p>
                  <v-list density="compact">
                    <v-list-item>Primary Entity Type: <strong>Municipality</strong></v-list-item>
                    <v-list-item>Aktive Facets: Pain Point, Positive Signal</v-list-item>
                    <v-list-item>Gruppierung: Nach Gemeinde</v-list-item>
                    <v-list-item>Sortierung: Nach Opportunity Score</v-list-item>
                  </v-list>
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2">mdi-calendar-multiple</v-icon>
                  {{ t('help.entityFacet.analysisTemplates.eventTracking.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <p>{{ t('help.entityFacet.analysisTemplates.eventTracking.description') }}</p>
                  <v-list density="compact">
                    <v-list-item>Primary Entity Type: <strong>Event</strong></v-list-item>
                    <v-list-item>Aktive Facets: Event Attendance</v-list-item>
                    <v-list-item>Zeitfilter: future_only (nur anstehende Events)</v-list-item>
                    <v-list-item>Verknuepfungen: Person attends Event</v-list-item>
                  </v-list>
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2">mdi-account-network</v-icon>
                  {{ t('help.entityFacet.analysisTemplates.decisionMakerProfile.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <p>{{ t('help.entityFacet.analysisTemplates.decisionMakerProfile.description') }}</p>
                  <v-list density="compact">
                    <v-list-item>Primary Entity Type: <strong>Person</strong></v-list-item>
                    <v-list-item>Aktive Facets: Contact, Event Attendance</v-list-item>
                    <v-list-item>Verknuepfungen: works_for Municipality, member_of Organization</v-list-item>
                  </v-list>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>

            <h3 class="text-h6 mb-3">{{ t('help.entityFacet.entitiesView.title') }}</h3>
            <p class="mb-3">{{ t('help.entityFacet.entitiesView.description') }}</p>
            <v-table density="compact" class="mb-4">
              <thead><tr><th>{{ t('help.entityFacet.entitiesView.tableHeaders.function') }}</th><th>{{ t('help.entityFacet.entitiesView.tableHeaders.description') }}</th></tr></thead>
              <tbody>
                <tr><td><strong>{{ t('help.entityFacet.entitiesView.functions.entityTypeTabs') }}</strong></td><td>{{ t('help.entityFacet.entitiesView.functions.entityTypeTabsDesc') }}</td></tr>
                <tr><td><strong>{{ t('help.entityFacet.entitiesView.functions.tableCardView') }}</strong></td><td>{{ t('help.entityFacet.entitiesView.functions.tableCardViewDesc') }}</td></tr>
                <tr><td><strong>{{ t('help.entityFacet.entitiesView.functions.filter') }}</strong></td><td>{{ t('help.entityFacet.entitiesView.functions.filterDesc') }}</td></tr>
                <tr><td><strong>{{ t('help.entityFacet.entitiesView.functions.facetOverview') }}</strong></td><td>{{ t('help.entityFacet.entitiesView.functions.facetOverviewDesc') }}</td></tr>
              </tbody>
            </v-table>

            <h3 class="text-h6 mb-3">{{ t('help.entityFacet.entityDetailView.title') }}</h3>
            <p class="mb-3">{{ t('help.entityFacet.entityDetailView.description') }}</p>
            <v-row class="mb-4">
              <v-col cols="12" md="6">
                <v-card variant="outlined">
                  <v-card-title class="text-subtitle-1">{{ t('help.entityFacet.entityDetailView.tabsTitle') }}</v-card-title>
                  <v-card-text>
                    <v-list density="compact">
                      <v-list-item prepend-icon="mdi-tag-multiple">{{ t('help.entityFacet.entityDetailView.tabs.facets') }}</v-list-item>
                      <v-list-item prepend-icon="mdi-link">{{ t('help.entityFacet.entityDetailView.tabs.relations') }}</v-list-item>
                      <v-list-item prepend-icon="mdi-web">{{ t('help.entityFacet.entityDetailView.tabs.dataSources') }}</v-list-item>
                      <v-list-item prepend-icon="mdi-file-document-multiple">{{ t('help.entityFacet.entityDetailView.tabs.documents') }}</v-list-item>
                      <v-list-item prepend-icon="mdi-database-sync">{{ t('help.entityFacet.entityDetailView.tabs.pysis') }}</v-list-item>
                    </v-list>
                  </v-card-text>
                </v-card>
              </v-col>
              <v-col cols="12" md="6">
                <v-card variant="outlined">
                  <v-card-title class="text-subtitle-1">{{ t('help.entityFacet.entityDetailView.actionsTitle') }}</v-card-title>
                  <v-card-text>
                    <v-list density="compact">
                      <v-list-item prepend-icon="mdi-plus">{{ t('help.entityFacet.entityDetailView.actions.addFacet') }}</v-list-item>
                      <v-list-item prepend-icon="mdi-check">{{ t('help.entityFacet.entityDetailView.actions.verify') }}</v-list-item>
                      <v-list-item prepend-icon="mdi-pencil">{{ t('help.entityFacet.entityDetailView.actions.edit') }}</v-list-item>
                      <v-list-item prepend-icon="mdi-play">{{ t('help.entityFacet.entityDetailView.actions.startCrawl') }}</v-list-item>
                    </v-list>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>

            <h3 class="text-h6 mb-3">{{ t('help.entityFacet.aiIntegration.title') }}</h3>
            <p class="mb-3">
              {{ t('help.entityFacet.aiIntegration.description') }}
            </p>
            <v-list density="compact" class="mb-4">
              <v-list-item prepend-icon="mdi-robot">
                <v-list-item-title><strong>{{ t('help.entityFacet.aiIntegration.automaticExtraction.title') }}</strong></v-list-item-title>
                <v-list-item-subtitle>{{ t('help.entityFacet.aiIntegration.automaticExtraction.description') }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-text-box-search">
                <v-list-item-title><strong>{{ t('help.entityFacet.aiIntegration.facetPrompts.title') }}</strong></v-list-item-title>
                <v-list-item-subtitle>{{ t('help.entityFacet.aiIntegration.facetPrompts.description') }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-percent">
                <v-list-item-title><strong>{{ t('help.entityFacet.aiIntegration.confidenceRating.title') }}</strong></v-list-item-title>
                <v-list-item-subtitle>{{ t('help.entityFacet.aiIntegration.confidenceRating.description') }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-check-decagram">
                <v-list-item-title><strong>{{ t('help.entityFacet.aiIntegration.humanInLoop.title') }}</strong></v-list-item-title>
                <v-list-item-subtitle>{{ t('help.entityFacet.aiIntegration.humanInLoop.description') }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>

            <h3 class="text-h6 mb-3">{{ t('help.entityFacet.bestPractices.title') }}</h3>
            <v-alert type="success" variant="tonal">
              <v-list density="compact" class="bg-transparent">
                <v-list-item prepend-icon="mdi-lightbulb">
                  <v-list-item-title>{{ t('help.entityFacet.bestPractices.items.predefinedTypes') }}</v-list-item-title>
                </v-list-item>
                <v-list-item prepend-icon="mdi-lightbulb">
                  <v-list-item-title>{{ t('help.entityFacet.bestPractices.items.useTemplates') }}</v-list-item-title>
                </v-list-item>
                <v-list-item prepend-icon="mdi-lightbulb">
                  <v-list-item-title>{{ t('help.entityFacet.bestPractices.items.verifyResults') }}</v-list-item-title>
                </v-list-item>
                <v-list-item prepend-icon="mdi-lightbulb">
                  <v-list-item-title>{{ t('help.entityFacet.bestPractices.items.timeFilters') }}</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-alert>
          </v-card-text>
        </v-card>

        <!-- Facet-Typ Verwaltung -->
        <v-card id="facet-type-admin" class="mb-4">
          <v-card-title class="text-h5 bg-teal">
            <v-icon class="mr-2">mdi-tag-multiple</v-icon>
            {{ t('help.facetTypeAdmin.title') }}
          </v-card-title>
          <v-card-text class="pt-4">
            <v-alert type="info" variant="tonal" class="mb-4">
              {{ t('help.facetTypeAdmin.accessInfo') }}
            </v-alert>

            <p class="mb-4">{{ t('help.facetTypeAdmin.description') }}</p>

            <h3 class="text-h6 mb-3">{{ t('help.facetTypeAdmin.overview.title') }}</h3>
            <p class="mb-2">{{ t('help.facetTypeAdmin.overview.description') }}</p>
            <v-list density="compact" class="mb-4">
              <v-list-item prepend-icon="mdi-format-list-bulleted">
                <v-list-item-title>{{ t('help.facetTypeAdmin.overview.features.list') }}</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-plus">
                <v-list-item-title>{{ t('help.facetTypeAdmin.overview.features.create') }}</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-pencil">
                <v-list-item-title>{{ t('help.facetTypeAdmin.overview.features.edit') }}</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-link-variant">
                <v-list-item-title>{{ t('help.facetTypeAdmin.overview.features.assign') }}</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-robot">
                <v-list-item-title>{{ t('help.facetTypeAdmin.overview.features.aiExtraction') }}</v-list-item-title>
              </v-list-item>
            </v-list>

            <h3 class="text-h6 mb-3">{{ t('help.facetTypeAdmin.concept.title') }}</h3>
            <p class="mb-3">{{ t('help.facetTypeAdmin.concept.description') }}</p>
            <v-row class="mb-4">
              <v-col cols="12" md="4">
                <v-card variant="outlined" class="pa-3 text-center h-100">
                  <v-icon color="success" size="32">mdi-source-branch</v-icon>
                  <div class="text-subtitle-1 mt-2">{{ t('help.facetTypeAdmin.concept.inheritance') }}</div>
                  <div class="text-caption">{{ t('help.facetTypeAdmin.concept.inheritanceDesc') }}</div>
                </v-card>
              </v-col>
              <v-col cols="12" md="4">
                <v-card variant="outlined" class="pa-3 text-center h-100">
                  <v-icon color="primary" size="32">mdi-checkbox-multiple-marked</v-icon>
                  <div class="text-subtitle-1 mt-2">{{ t('help.facetTypeAdmin.concept.consistency') }}</div>
                  <div class="text-caption">{{ t('help.facetTypeAdmin.concept.consistencyDesc') }}</div>
                </v-card>
              </v-col>
              <v-col cols="12" md="4">
                <v-card variant="outlined" class="pa-3 text-center h-100">
                  <v-icon color="warning" size="32">mdi-lightning-bolt</v-icon>
                  <div class="text-subtitle-1 mt-2">{{ t('help.facetTypeAdmin.concept.efficiency') }}</div>
                  <div class="text-caption">{{ t('help.facetTypeAdmin.concept.efficiencyDesc') }}</div>
                </v-card>
              </v-col>
            </v-row>

            <h3 class="text-h6 mb-3">{{ t('help.facetTypeAdmin.createFacetType.title') }}</h3>
            <v-expansion-panels variant="accordion" class="mb-4">
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2">mdi-form-textbox</v-icon>
                  {{ t('help.facetTypeAdmin.createFacetType.basicSettings.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <thead><tr><th>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.name') }}</th><th>{{ t('help.dashboard.crawler_dialog.table.description') }}</th></tr></thead>
                    <tbody>
                      <tr><td><strong>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.name') }}</strong></td><td>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.nameDesc') }}</td></tr>
                      <tr><td><strong>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.namePlural') }}</strong></td><td>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.namePluralDesc') }}</td></tr>
                      <tr><td><strong>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.slug') }}</strong></td><td>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.slugDesc') }}</td></tr>
                      <tr><td><strong>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.description') }}</strong></td><td>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.descriptionDesc') }}</td></tr>
                      <tr><td><strong>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.icon') }}</strong></td><td>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.iconDesc') }}</td></tr>
                      <tr><td><strong>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.color') }}</strong></td><td>{{ t('help.facetTypeAdmin.createFacetType.basicSettings.colorDesc') }}</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2">mdi-format-list-checks</v-icon>
                  {{ t('help.facetTypeAdmin.createFacetType.valueType.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-list density="compact">
                    <v-list-item>
                      <v-list-item-title><strong>{{ t('help.facetTypeAdmin.createFacetType.valueType.structured') }}</strong></v-list-item-title>
                      <v-list-item-subtitle>{{ t('help.facetTypeAdmin.createFacetType.valueType.structuredDesc') }}</v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item>
                      <v-list-item-title><strong>{{ t('help.facetTypeAdmin.createFacetType.valueType.text') }}</strong></v-list-item-title>
                      <v-list-item-subtitle>{{ t('help.facetTypeAdmin.createFacetType.valueType.textDesc') }}</v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item>
                      <v-list-item-title><strong>{{ t('help.facetTypeAdmin.createFacetType.valueType.number') }}</strong></v-list-item-title>
                      <v-list-item-subtitle>{{ t('help.facetTypeAdmin.createFacetType.valueType.numberDesc') }}</v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item>
                      <v-list-item-title><strong>{{ t('help.facetTypeAdmin.createFacetType.valueType.boolean') }}</strong></v-list-item-title>
                      <v-list-item-subtitle>{{ t('help.facetTypeAdmin.createFacetType.valueType.booleanDesc') }}</v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item>
                      <v-list-item-title><strong>{{ t('help.facetTypeAdmin.createFacetType.valueType.date') }}</strong></v-list-item-title>
                      <v-list-item-subtitle>{{ t('help.facetTypeAdmin.createFacetType.valueType.dateDesc') }}</v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2">mdi-link-variant</v-icon>
                  {{ t('help.facetTypeAdmin.createFacetType.entityTypeAssignment.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <p class="mb-2">{{ t('help.facetTypeAdmin.createFacetType.entityTypeAssignment.description') }}</p>
                  <v-list density="compact">
                    <v-list-item prepend-icon="mdi-select-all">
                      <v-list-item-title><strong>{{ t('help.facetTypeAdmin.createFacetType.entityTypeAssignment.allTypes') }}</strong></v-list-item-title>
                      <v-list-item-subtitle>{{ t('help.facetTypeAdmin.createFacetType.entityTypeAssignment.allTypesDesc') }}</v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item prepend-icon="mdi-select-group">
                      <v-list-item-title><strong>{{ t('help.facetTypeAdmin.createFacetType.entityTypeAssignment.specificTypes') }}</strong></v-list-item-title>
                      <v-list-item-subtitle>{{ t('help.facetTypeAdmin.createFacetType.entityTypeAssignment.specificTypesDesc') }}</v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>

            <h3 class="text-h6 mb-3">{{ t('help.facetTypeAdmin.schema.title') }}</h3>
            <p class="mb-2">{{ t('help.facetTypeAdmin.schema.description') }}</p>
            <v-card variant="outlined" class="mb-4 pa-3">
              <div class="text-caption mb-1">{{ t('help.facetTypeAdmin.schema.example') }}</div>
              <code class="text-body-2" style="white-space: pre-wrap;">{{ t('help.facetTypeAdmin.schema.exampleSchema') }}</code>
            </v-card>
            <v-alert type="info" variant="tonal" density="compact" class="mb-4">
              {{ t('help.facetTypeAdmin.schema.tip') }}
            </v-alert>

            <h3 class="text-h6 mb-3">{{ t('help.facetTypeAdmin.aiExtraction.title') }}</h3>
            <v-table density="compact" class="mb-4">
              <tbody>
                <tr>
                  <td><strong>{{ t('help.facetTypeAdmin.aiExtraction.enabled') }}</strong></td>
                  <td>{{ t('help.facetTypeAdmin.aiExtraction.enabledDesc') }}</td>
                </tr>
                <tr>
                  <td><strong>{{ t('help.facetTypeAdmin.aiExtraction.prompt') }}</strong></td>
                  <td>{{ t('help.facetTypeAdmin.aiExtraction.promptDesc') }}</td>
                </tr>
                <tr>
                  <td><strong>{{ t('help.facetTypeAdmin.aiExtraction.timeBased') }}</strong></td>
                  <td>{{ t('help.facetTypeAdmin.aiExtraction.timeBasedDesc') }}</td>
                </tr>
              </tbody>
            </v-table>
            <v-card variant="outlined" class="mb-4 pa-3 bg-blue-grey-lighten-5">
              <div class="text-caption text-medium-emphasis">{{ t('help.facetTypeAdmin.aiExtraction.promptExample') }}</div>
            </v-card>

            <h3 class="text-h6 mb-3">{{ t('help.facetTypeAdmin.entityTypesView.title') }}</h3>
            <p class="mb-2">{{ t('help.facetTypeAdmin.entityTypesView.description') }}</p>
            <v-list density="compact">
              <v-list-item prepend-icon="mdi-table-column">
                <v-list-item-title>{{ t('help.facetTypeAdmin.entityTypesView.features.facetColumn') }}</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-palette">
                <v-list-item-title>{{ t('help.facetTypeAdmin.entityTypesView.features.colorCoded') }}</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-flash">
                <v-list-item-title>{{ t('help.facetTypeAdmin.entityTypesView.features.quickAssign') }}</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>

        <!-- Ergebnisse -->
        <v-card id="results" class="mb-4">
          <v-card-title class="text-h5 bg-orange">
            <v-icon class="mr-2">mdi-chart-bar</v-icon>
            {{ t('help.results.title') }}
          </v-card-title>
          <v-card-text class="pt-4">
            <p class="mb-4">{{ t('help.results.description') }}</p>

            <h3 class="text-h6 mb-3">{{ t('help.results.statisticsCards') }}</h3>
            <v-row class="mb-4">
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-2">
                  <div class="text-subtitle-1">{{ t('help.results.cards.total') }}</div>
                  <div class="text-caption">{{ t('help.results.cards.totalDesc') }}</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-2" color="success">
                  <div class="text-subtitle-1">{{ t('help.results.cards.verified') }}</div>
                  <div class="text-caption">{{ t('help.results.cards.verifiedDesc') }}</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-2" color="info">
                  <div class="text-subtitle-1">{{ t('help.results.cards.highConfidence') }}</div>
                  <div class="text-caption">{{ t('help.results.cards.highConfidenceDesc') }}</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-2">
                  <div class="text-subtitle-1">{{ t('help.results.cards.average') }}</div>
                  <div class="text-caption">{{ t('help.results.cards.averageDesc') }}</div>
                </v-card>
              </v-col>
            </v-row>

            <h3 class="text-h6 mb-3">{{ t('help.results.availableFilters') }}</h3>
            <v-chip-group class="mb-4">
              <v-chip size="small" variant="outlined">{{ t('help.results.filters[0]') }}</v-chip>
              <v-chip size="small" variant="outlined">{{ t('help.results.filters[1]') }}</v-chip>
              <v-chip size="small" variant="outlined">{{ t('help.results.filters[2]') }}</v-chip>
              <v-chip size="small" variant="outlined">{{ t('help.results.filters[3]') }}</v-chip>
            </v-chip-group>

            <h3 class="text-h6 mb-3">{{ t('help.results.whatIsExtracted') }}</h3>
            <v-list density="compact">
              <v-list-item prepend-icon="mdi-tag">
                <v-list-item-title>{{ t('help.results.extracted.topicSummary') }}</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-emoticon-sad">
                <v-list-item-title>{{ t('help.results.extracted.painPoints') }}</v-list-item-title>
                <v-list-item-subtitle>{{ t('help.results.extracted.painPointsDesc') }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-emoticon-happy">
                <v-list-item-title>{{ t('help.results.extracted.opportunities') }}</v-list-item-title>
                <v-list-item-subtitle>{{ t('help.results.extracted.opportunitiesDesc') }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-emoticon-neutral">
                <v-list-item-title>{{ t('help.results.extracted.sentiment') }}</v-list-item-title>
                <v-list-item-subtitle>{{ t('help.results.extracted.sentimentDesc') }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-percent">
                <v-list-item-title>{{ t('help.results.extracted.confidence') }}</v-list-item-title>
                <v-list-item-subtitle>{{ t('help.results.extracted.confidenceDesc') }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>

            <h3 class="text-h6 mt-4 mb-3">{{ t('help.results.detailDialog.title') }}</h3>
            <p class="mb-2">{{ t('help.results.detailDialog.description') }}</p>

            <h4 class="text-subtitle-1 mb-2">{{ t('help.results.detailDialog.header') }}</h4>
            <v-list density="compact" class="mb-3">
              <v-list-item prepend-icon="mdi-text">{{ t('help.results.detailDialog.headerItems[0]') }}</v-list-item>
              <v-list-item prepend-icon="mdi-percent">{{ t('help.results.detailDialog.headerItems[1]') }}</v-list-item>
              <v-list-item prepend-icon="mdi-link">{{ t('help.results.detailDialog.headerItems[2]') }}</v-list-item>
            </v-list>

            <h4 class="text-subtitle-1 mb-2">{{ t('help.results.detailDialog.infoCards') }}</h4>
            <v-row class="mb-3">
              <v-col cols="3"><v-chip size="small" variant="outlined" color="success">Relevant?</v-chip></v-col>
              <v-col cols="3"><v-chip size="small" variant="outlined">Relevanz</v-chip></v-col>
              <v-col cols="3"><v-chip size="small" variant="outlined">Gemeinde</v-chip></v-col>
              <v-col cols="3"><v-chip size="small" variant="outlined" color="warning">Priorität</v-chip></v-col>
            </v-row>

            <v-expansion-panels variant="accordion" class="mb-4">
              <v-expansion-panel :title="t('help.results.detailDialog.sections.summary')">
                <v-expansion-panel-text>
                  {{ t('help.results.detailDialog.sections.summaryDesc') }}
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2" color="error">mdi-alert</v-icon> {{ t('help.results.detailDialog.sections.painPoints') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  {{ t('help.results.detailDialog.sections.painPointsDesc') }}
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2" color="success">mdi-thumb-up</v-icon> {{ t('help.results.detailDialog.sections.positiveSignals') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  {{ t('help.results.detailDialog.sections.positiveSignalsDesc') }}
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2" color="primary">mdi-account-group</v-icon> {{ t('help.results.detailDialog.sections.decisionMakers') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  {{ t('help.results.detailDialog.sections.decisionMakersDesc') }}
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2">mdi-code-json</v-icon> {{ t('help.results.detailDialog.sections.rawJson') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  {{ t('help.results.detailDialog.sections.rawJsonDesc') }}
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>

            <v-alert type="success" variant="tonal" density="compact" class="mb-4">
              {{ t('help.results.detailDialog.tip') }}
            </v-alert>

            <h3 class="text-h6 mt-4 mb-3">{{ t('help.results.understandingConfidence.title') }}</h3>
            <v-table density="compact">
              <thead><tr><th>Bereich</th><th>Bedeutung</th><th>Empfehlung</th></tr></thead>
              <tbody>
                <tr>
                  <td><v-chip size="small" color="error">0-50%</v-chip></td>
                  <td>{{ t('help.results.understandingConfidence.lowDesc') }}</td>
                  <td>{{ t('help.results.understandingConfidence.lowAction') }}</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="warning">50-70%</v-chip></td>
                  <td>{{ t('help.results.understandingConfidence.mediumDesc') }}</td>
                  <td>{{ t('help.results.understandingConfidence.mediumAction') }}</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="success">70-100%</v-chip></td>
                  <td>{{ t('help.results.understandingConfidence.highDesc') }}</td>
                  <td>{{ t('help.results.understandingConfidence.highAction') }}</td>
                </tr>
              </tbody>
            </v-table>
          </v-card-text>
        </v-card>

        <!-- Export -->
        <v-card id="export" class="mb-4">
          <v-card-title class="text-h5 bg-deep-purple">
            <v-icon class="mr-2">mdi-export</v-icon>
            {{ t('help.export.title') }}
          </v-card-title>
          <v-card-text class="pt-4">
            <h3 class="text-h6 mb-3">{{ t('help.export.exportFormats') }}</h3>
            <v-row class="mb-4">
              <v-col cols="6">
                <v-card variant="outlined" class="pa-3 text-center">
                  <v-icon size="48" color="primary">mdi-code-json</v-icon>
                  <div class="text-h6">{{ t('help.export.formats.json') }}</div>
                  <div class="text-caption">{{ t('help.export.formats.jsonDesc') }}</div>
                </v-card>
              </v-col>
              <v-col cols="6">
                <v-card variant="outlined" class="pa-3 text-center">
                  <v-icon size="48" color="success">mdi-file-delimited</v-icon>
                  <div class="text-h6">{{ t('help.export.formats.csv') }}</div>
                  <div class="text-caption">{{ t('help.export.formats.csvDesc') }}</div>
                </v-card>
              </v-col>
            </v-row>

            <h3 class="text-h6 mb-3">{{ t('help.export.exportFilters') }}</h3>
            <v-chip-group class="mb-4">
              <v-chip size="small" variant="outlined">{{ t('help.export.filters[0]') }}</v-chip>
              <v-chip size="small" variant="outlined">{{ t('help.export.filters[1]') }}</v-chip>
              <v-chip size="small" variant="outlined">{{ t('help.export.filters[2]') }}</v-chip>
              <v-chip size="small" variant="outlined">{{ t('help.export.filters[3]') }}</v-chip>
              <v-chip size="small" variant="outlined">{{ t('help.export.filters[4]') }}</v-chip>
            </v-chip-group>

            <h3 class="text-h6 mb-3">{{ t('help.export.webhookTest.title') }}</h3>
            <p class="mb-2">{{ t('help.export.webhookTest.description') }}</p>
            <v-list density="compact" class="mb-4">
              <v-list-item prepend-icon="mdi-link">
                <v-list-item-title>{{ t('help.export.webhookTest.items[0]') }}</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-send">
                <v-list-item-title>{{ t('help.export.webhookTest.items[1]') }}</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-check">
                <v-list-item-title>{{ t('help.export.webhookTest.items[2]') }}</v-list-item-title>
              </v-list-item>
            </v-list>

            <h3 class="text-h6 mb-3">{{ t('help.export.changesFeed.title') }}</h3>
            <p class="mb-2">{{ t('help.export.changesFeed.description') }}</p>
            <v-table density="compact" class="mb-4">
              <thead><tr><th>{{ t('common.changeType') }}</th><th>{{ t('common.description') }}</th></tr></thead>
              <tbody>
                <tr><td><v-chip size="small" color="success">NEW</v-chip></td><td>{{ t('help.export.changesFeed.newDesc') }}</td></tr>
                <tr><td><v-chip size="small" color="info">UPDATED</v-chip></td><td>{{ t('help.export.changesFeed.updatedDesc') }}</td></tr>
                <tr><td><v-chip size="small" color="warning">VERIFIED</v-chip></td><td>{{ t('help.export.changesFeed.verifiedDesc') }}</td></tr>
              </tbody>
            </v-table>

            <h3 class="text-h6 mb-3">{{ t('help.export.apiEndpoints.title') }}</h3>
            <v-table density="compact">
              <thead><tr><th>{{ t('common.endpoint') }}</th><th>{{ t('common.description') }}</th></tr></thead>
              <tbody>
                <tr><td><code>GET /api/v1/data</code></td><td>{{ t('help.export.apiEndpoints.getData') }}</td></tr>
                <tr><td><code>GET /api/v1/data/documents</code></td><td>{{ t('help.export.apiEndpoints.getDocuments') }}</td></tr>
                <tr><td><code>GET /api/v1/data/search?q=...</code></td><td>{{ t('help.export.apiEndpoints.search') }}</td></tr>
                <tr><td><code>GET /api/v1/export/json</code></td><td>{{ t('help.export.apiEndpoints.exportJson') }}</td></tr>
                <tr><td><code>GET /api/v1/export/csv</code></td><td>{{ t('help.export.apiEndpoints.exportCsv') }}</td></tr>
                <tr><td><code>GET /api/v1/export/changes</code></td><td>{{ t('help.export.apiEndpoints.getChanges') }}</td></tr>
                <tr><td><code>POST /api/v1/export/webhook/test</code></td><td>{{ t('help.export.apiEndpoints.testWebhook') }}</td></tr>
              </tbody>
            </v-table>
          </v-card-text>
        </v-card>

        <!-- Benachrichtigungen -->
        <v-card id="notifications" class="mb-4">
          <v-card-title class="text-h5 bg-orange-darken-2">
            <v-icon class="mr-2">mdi-bell</v-icon>
            {{ t('help.notifications.title') }}
          </v-card-title>
          <v-card-text class="pt-4">
            <p class="mb-4">
              {{ t('help.notifications.description') }}
            </p>

            <h3 class="text-h6 mb-3">{{ t('help.notifications.overview.title') }}</h3>
            <p class="mb-4">
              {{ t('help.notifications.overview.description') }}
            </p>

            <v-list density="compact" class="mb-4">
              <v-list-item prepend-icon="mdi-inbox">
                <v-list-item-title><strong>{{ t('help.notifications.overview.inbox') }}</strong></v-list-item-title>
                <v-list-item-subtitle>{{ t('help.notifications.overview.inboxDesc') }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-filter-cog">
                <v-list-item-title><strong>{{ t('help.notifications.overview.rules') }}</strong></v-list-item-title>
                <v-list-item-subtitle>{{ t('help.notifications.overview.rulesDesc') }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-cog">
                <v-list-item-title><strong>{{ t('help.notifications.overview.settings') }}</strong></v-list-item-title>
                <v-list-item-subtitle>{{ t('help.notifications.overview.settingsDesc') }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>

            <v-divider class="my-4"></v-divider>

            <h3 class="text-h6 mb-3">{{ t('help.notifications.eventTypes.title') }}</h3>
            <p class="mb-4">{{ t('help.notifications.eventTypes.description') }}</p>

            <v-table density="compact" class="mb-4">
              <thead>
                <tr><th>Event</th><th>{{ t('common.description') }}</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td><v-chip size="small" color="success">{{ t('help.notifications.eventTypes.newDocument') }}</v-chip></td>
                  <td>{{ t('help.notifications.eventTypes.newDocumentDesc') }}</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="info">{{ t('help.notifications.eventTypes.documentChanged') }}</v-chip></td>
                  <td>{{ t('help.notifications.eventTypes.documentChangedDesc') }}</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="error">{{ t('help.notifications.eventTypes.documentRemoved') }}</v-chip></td>
                  <td>{{ t('help.notifications.eventTypes.documentRemovedDesc') }}</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="purple">{{ t('help.notifications.eventTypes.crawlStarted') }}</v-chip></td>
                  <td>{{ t('help.notifications.eventTypes.crawlStartedDesc') }}</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="success">{{ t('help.notifications.eventTypes.crawlCompleted') }}</v-chip></td>
                  <td>{{ t('help.notifications.eventTypes.crawlCompletedDesc') }}</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="error">{{ t('help.notifications.eventTypes.crawlFailed') }}</v-chip></td>
                  <td>{{ t('help.notifications.eventTypes.crawlFailedDesc') }}</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="cyan">{{ t('help.notifications.eventTypes.aiAnalysisCompleted') }}</v-chip></td>
                  <td>{{ t('help.notifications.eventTypes.aiAnalysisCompletedDesc') }}</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="orange">{{ t('help.notifications.eventTypes.highConfidence') }}</v-chip></td>
                  <td>{{ t('help.notifications.eventTypes.highConfidenceDesc') }}</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="grey">{{ t('help.notifications.eventTypes.sourceStatusChanged') }}</v-chip></td>
                  <td>{{ t('help.notifications.eventTypes.sourceStatusChangedDesc') }}</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="error">{{ t('help.notifications.eventTypes.sourceError') }}</v-chip></td>
                  <td>{{ t('help.notifications.eventTypes.sourceErrorDesc') }}</td>
                </tr>
              </tbody>
            </v-table>

            <v-divider class="my-4"></v-divider>

            <h3 class="text-h6 mb-3">{{ t('help.notifications.channels.title') }}</h3>

            <v-row class="mb-4">
              <v-col cols="12" md="4">
                <v-card variant="outlined" class="pa-3">
                  <div class="d-flex align-center mb-2">
                    <v-icon color="blue" class="mr-2">mdi-email</v-icon>
                    <strong>{{ t('help.notifications.channels.email') }}</strong>
                  </div>
                  <p class="text-body-2">
                    {{ t('help.notifications.channels.emailDesc') }}
                  </p>
                </v-card>
              </v-col>
              <v-col cols="12" md="4">
                <v-card variant="outlined" class="pa-3">
                  <div class="d-flex align-center mb-2">
                    <v-icon color="purple" class="mr-2">mdi-webhook</v-icon>
                    <strong>{{ t('help.notifications.channels.webhook') }}</strong>
                  </div>
                  <p class="text-body-2">
                    {{ t('help.notifications.channels.webhookDesc') }}
                  </p>
                </v-card>
              </v-col>
              <v-col cols="12" md="4">
                <v-card variant="outlined" class="pa-3">
                  <div class="d-flex align-center mb-2">
                    <v-icon color="green" class="mr-2">mdi-bell-ring</v-icon>
                    <strong>{{ t('help.notifications.channels.inApp') }}</strong>
                  </div>
                  <p class="text-body-2">
                    {{ t('help.notifications.channels.inAppDesc') }}
                  </p>
                </v-card>
              </v-col>
            </v-row>

            <v-divider class="my-4"></v-divider>

            <h3 class="text-h6 mb-3">{{ t('help.notifications.createRules.title') }}</h3>
            <p class="mb-4">{{ t('help.notifications.createRules.description') }}</p>

            <v-timeline density="compact" side="end" class="mb-4">
              <v-timeline-item dot-color="primary" size="small">
                <template v-slot:opposite><strong>1</strong></template>
                <div><strong>{{ t('help.notifications.createRules.step1Title') }}</strong><br>{{ t('help.notifications.createRules.step1Desc') }}</div>
              </v-timeline-item>
              <v-timeline-item dot-color="success" size="small">
                <template v-slot:opposite><strong>2</strong></template>
                <div><strong>{{ t('help.notifications.createRules.step2Title') }}</strong><br>{{ t('help.notifications.createRules.step2Desc') }}</div>
              </v-timeline-item>
              <v-timeline-item dot-color="warning" size="small">
                <template v-slot:opposite><strong>3</strong></template>
                <div><strong>{{ t('help.notifications.createRules.step3Title') }}</strong><br>{{ t('help.notifications.createRules.step3Desc') }}</div>
              </v-timeline-item>
              <v-timeline-item dot-color="info" size="small">
                <template v-slot:opposite><strong>4</strong></template>
                <div><strong>{{ t('help.notifications.createRules.step4Title') }}</strong><br>{{ t('help.notifications.createRules.step4Desc') }}</div>
              </v-timeline-item>
            </v-timeline>

            <h3 class="text-h6 mb-3">{{ t('help.notifications.filterOptions.title') }}</h3>
            <v-table density="compact" class="mb-4">
              <thead>
                <tr><th>Filter</th><th>{{ t('common.description') }}</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>{{ t('help.notifications.filterOptions.categories') }}</strong></td>
                  <td>{{ t('help.notifications.filterOptions.categoriesDesc') }}</td>
                </tr>
                <tr>
                  <td><strong>{{ t('help.notifications.filterOptions.dataSources') }}</strong></td>
                  <td>{{ t('help.notifications.filterOptions.dataSourcesDesc') }}</td>
                </tr>
                <tr>
                  <td><strong>{{ t('help.notifications.filterOptions.minConfidence') }}</strong></td>
                  <td>{{ t('help.notifications.filterOptions.minConfidenceDesc') }}</td>
                </tr>
                <tr>
                  <td><strong>{{ t('help.notifications.filterOptions.keywords') }}</strong></td>
                  <td>{{ t('help.notifications.filterOptions.keywordsDesc') }}</td>
                </tr>
              </tbody>
            </v-table>

            <v-divider class="my-4"></v-divider>

            <h3 class="text-h6 mb-3">{{ t('help.notifications.digestMode.title') }}</h3>
            <p class="mb-4">
              {{ t('help.notifications.digestMode.description') }}
            </p>
            <v-alert type="info" variant="tonal" class="mb-4">
              {{ t('help.notifications.digestMode.info') }}
            </v-alert>

            <h3 class="text-h6 mb-3">{{ t('help.notifications.emailAddresses.title') }}</h3>
            <p class="mb-4">
              {{ t('help.notifications.emailAddresses.description') }}
            </p>
            <v-list density="compact" class="mb-4">
              <v-list-item prepend-icon="mdi-plus">
                <v-list-item-title>{{ t('help.notifications.emailAddresses.add') }}</v-list-item-title>
                <v-list-item-subtitle>{{ t('help.notifications.emailAddresses.addDesc') }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-email-check">
                <v-list-item-title>{{ t('help.notifications.emailAddresses.verify') }}</v-list-item-title>
                <v-list-item-subtitle>{{ t('help.notifications.emailAddresses.verifyDesc') }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-delete">
                <v-list-item-title>{{ t('help.notifications.emailAddresses.delete') }}</v-list-item-title>
                <v-list-item-subtitle>{{ t('help.notifications.emailAddresses.deleteDesc') }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>

            <v-divider class="my-4"></v-divider>

            <h3 class="text-h6 mb-3">{{ t('help.notifications.webhookConfig.title') }}</h3>
            <p class="mb-4">
              {{ t('help.notifications.webhookConfig.description') }}
            </p>
            <v-table density="compact" class="mb-4">
              <thead>
                <tr><th>Methode</th><th>{{ t('common.description') }}</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>{{ t('help.notifications.webhookConfig.none') }}</strong></td>
                  <td>{{ t('help.notifications.webhookConfig.noneDesc') }}</td>
                </tr>
                <tr>
                  <td><strong>{{ t('help.notifications.webhookConfig.bearer') }}</strong></td>
                  <td>{{ t('help.notifications.webhookConfig.bearerDesc') }}</td>
                </tr>
                <tr>
                  <td><strong>{{ t('help.notifications.webhookConfig.apiKey') }}</strong></td>
                  <td>{{ t('help.notifications.webhookConfig.apiKeyDesc') }}</td>
                </tr>
                <tr>
                  <td><strong>{{ t('help.notifications.webhookConfig.basicAuth') }}</strong></td>
                  <td>{{ t('help.notifications.webhookConfig.basicAuthDesc') }}</td>
                </tr>
              </tbody>
            </v-table>

            <v-alert type="warning" variant="tonal" class="mb-4">
              {{ t('help.notifications.webhookConfig.warning') }}
            </v-alert>
          </v-card-text>
</v-card>

        <!-- API Referenz -->
        <v-card id="api" class="mb-4">
          <v-card-title class="text-h5 bg-grey-darken-3">
            <v-icon class="mr-2">mdi-api</v-icon>
            {{ t('help.api.title') }}
          </v-card-title>
          <v-card-text class="pt-4">
            <p class="mb-4">
              {{ t('help.api.description') }}
            </p>

            <v-expansion-panels variant="accordion">
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="primary" class="mr-2">mdi-folder-multiple</v-icon>
                  {{ t('help.apiGroups.categories.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <thead><tr><th>{{ t('help.api.tableHeaders.method') }}</th><th>{{ t('help.api.tableHeaders.endpoint') }}</th><th>{{ t('help.api.tableHeaders.description') }}</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/categories</code></td><td>{{ t('help.apiGroups.categories.endpoints.list') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/categories</code></td><td>{{ t('help.apiGroups.categories.endpoints.create') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/categories/{id}</code></td><td>{{ t('help.apiGroups.categories.endpoints.get') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="warning">PUT</v-chip></td><td><code>/api/admin/categories/{id}</code></td><td>{{ t('help.apiGroups.categories.endpoints.update') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="error">DELETE</v-chip></td><td><code>/api/admin/categories/{id}</code></td><td>{{ t('help.apiGroups.categories.endpoints.delete') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/categories/{id}/stats</code></td><td>{{ t('help.apiGroups.categories.endpoints.stats') }}</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="teal" class="mr-2">mdi-web</v-icon>
                  {{ t('help.apiGroups.sources.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <thead><tr><th>{{ t('help.api.tableHeaders.method') }}</th><th>{{ t('help.api.tableHeaders.endpoint') }}</th><th>{{ t('help.api.tableHeaders.description') }}</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/sources</code></td><td>{{ t('help.apiGroups.sources.endpoints.list') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/sources</code></td><td>{{ t('help.apiGroups.sources.endpoints.create') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/sources/bulk-import</code></td><td>{{ t('help.apiGroups.sources.endpoints.bulkImport') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/sources/meta/countries</code></td><td>{{ t('help.apiGroups.sources.endpoints.countries') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/sources/meta/locations</code></td><td>{{ t('help.apiGroups.sources.endpoints.locations') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/sources/{id}</code></td><td>{{ t('help.apiGroups.sources.endpoints.get') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="warning">PUT</v-chip></td><td><code>/api/admin/sources/{id}</code></td><td>{{ t('help.apiGroups.sources.endpoints.update') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="error">DELETE</v-chip></td><td><code>/api/admin/sources/{id}</code></td><td>{{ t('help.apiGroups.sources.endpoints.delete') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/sources/{id}/reset</code></td><td>{{ t('help.apiGroups.sources.endpoints.reset') }}</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="cyan" class="mr-2">mdi-robot</v-icon>
                  {{ t('help.apiGroups.crawler.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <thead><tr><th>{{ t('help.api.tableHeaders.method') }}</th><th>{{ t('help.api.tableHeaders.endpoint') }}</th><th>{{ t('help.api.tableHeaders.description') }}</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/crawler/start</code></td><td>{{ t('help.apiGroups.crawler.endpoints.start') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/crawler/status</code></td><td>{{ t('help.apiGroups.crawler.endpoints.status') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/crawler/stats</code></td><td>{{ t('help.apiGroups.crawler.endpoints.stats') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/crawler/running</code></td><td>{{ t('help.apiGroups.crawler.endpoints.running') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/crawler/jobs</code></td><td>{{ t('help.apiGroups.crawler.endpoints.jobs') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/crawler/jobs/{id}</code></td><td>{{ t('help.apiGroups.crawler.endpoints.jobDetails') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/crawler/jobs/{id}/log</code></td><td>{{ t('help.apiGroups.crawler.endpoints.jobLog') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/crawler/jobs/{id}/cancel</code></td><td>{{ t('help.apiGroups.crawler.endpoints.cancelJob') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/crawler/reanalyze</code></td><td>{{ t('help.apiGroups.crawler.endpoints.reanalyze') }}</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="purple" class="mr-2">mdi-brain</v-icon>
                  {{ t('help.apiGroups.aiTasks.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <thead><tr><th>{{ t('help.api.tableHeaders.method') }}</th><th>{{ t('help.api.tableHeaders.endpoint') }}</th><th>{{ t('help.api.tableHeaders.description') }}</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/crawler/ai-tasks</code></td><td>{{ t('help.apiGroups.aiTasks.endpoints.list') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/crawler/ai-tasks/running</code></td><td>{{ t('help.apiGroups.aiTasks.endpoints.running') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/crawler/ai-tasks/{id}/cancel</code></td><td>{{ t('help.apiGroups.aiTasks.endpoints.cancel') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/crawler/documents/{id}/process</code></td><td>{{ t('help.apiGroups.aiTasks.endpoints.processDocument') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/crawler/documents/{id}/analyze</code></td><td>{{ t('help.apiGroups.aiTasks.endpoints.analyzeDocument') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/crawler/documents/process-pending</code></td><td>{{ t('help.apiGroups.aiTasks.endpoints.processPending') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/crawler/documents/stop-all</code></td><td>{{ t('help.apiGroups.aiTasks.endpoints.stopAll') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/crawler/documents/reanalyze-filtered</code></td><td>{{ t('help.apiGroups.aiTasks.endpoints.reanalyzeFiltered') }}</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="indigo" class="mr-2">mdi-map-marker</v-icon>
                  {{ t('help.apiGroups.locations.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <thead><tr><th>{{ t('help.api.tableHeaders.method') }}</th><th>{{ t('help.api.tableHeaders.endpoint') }}</th><th>{{ t('help.api.tableHeaders.description') }}</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/locations</code></td><td>{{ t('help.apiGroups.locations.endpoints.list') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/locations/{id}</code></td><td>{{ t('help.apiGroups.locations.endpoints.get') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/locations/search</code></td><td>{{ t('help.apiGroups.locations.endpoints.search') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/locations/with-sources</code></td><td>{{ t('help.apiGroups.locations.endpoints.withSources') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/locations/countries</code></td><td>{{ t('help.apiGroups.sources.endpoints.countries') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/locations/states</code></td><td>{{ t('help.apiGroups.locations.endpoints.states') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/locations/admin-levels</code></td><td>{{ t('help.apiGroups.locations.endpoints.adminLevels') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/locations</code></td><td>{{ t('help.apiGroups.locations.endpoints.create') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="warning">PUT</v-chip></td><td><code>/api/admin/locations/{id}</code></td><td>{{ t('help.apiGroups.locations.endpoints.update') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="error">DELETE</v-chip></td><td><code>/api/admin/locations/{id}</code></td><td>{{ t('help.apiGroups.locations.endpoints.delete') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/locations/link-sources</code></td><td>{{ t('help.apiGroups.locations.endpoints.linkSources') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/locations/enrich-admin-levels</code></td><td>{{ t('help.apiGroups.locations.endpoints.enrichAdminLevels') }}</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="info" class="mr-2">mdi-database-search</v-icon>
                  {{ t('help.apiGroups.publicApi.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <thead><tr><th>{{ t('help.api.tableHeaders.method') }}</th><th>{{ t('help.api.tableHeaders.endpoint') }}</th><th>{{ t('help.api.tableHeaders.description') }}</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data</code></td><td>{{ t('help.apiGroups.publicApi.endpoints.data') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/stats</code></td><td>{{ t('help.apiGroups.publicApi.endpoints.stats') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/locations</code></td><td>{{ t('help.apiGroups.publicApi.endpoints.locations') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/countries</code></td><td>{{ t('help.apiGroups.publicApi.endpoints.countries') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/documents</code></td><td>{{ t('help.apiGroups.publicApi.endpoints.documents') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/documents/{id}</code></td><td>{{ t('help.apiGroups.publicApi.endpoints.documentDetails') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/documents/locations</code></td><td>{{ t('help.apiGroups.publicApi.endpoints.documentLocations') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/search</code></td><td>{{ t('help.export.apiEndpoints.search') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="warning">PUT</v-chip></td><td><code>/api/v1/data/extracted/{id}/verify</code></td><td>{{ t('help.apiGroups.publicApi.endpoints.verify') }}</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="deep-purple" class="mr-2">mdi-cube-outline</v-icon>
                  {{ t('help.apiGroups.entities.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <thead><tr><th>{{ t('help.api.tableHeaders.method') }}</th><th>{{ t('help.api.tableHeaders.endpoint') }}</th><th>{{ t('help.api.tableHeaders.description') }}</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/entities</code></td><td>{{ t('help.apiGroups.entities.endpoints.list') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/v1/entities</code></td><td>{{ t('help.apiGroups.entities.endpoints.create') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/entities/{id}</code></td><td>{{ t('help.apiGroups.entities.endpoints.get') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="warning">PUT</v-chip></td><td><code>/api/v1/entities/{id}</code></td><td>{{ t('help.apiGroups.entities.endpoints.update') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="error">DELETE</v-chip></td><td><code>/api/v1/entities/{id}</code></td><td>{{ t('help.apiGroups.entities.endpoints.delete') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/entities/{id}/brief</code></td><td>{{ t('help.apiGroups.entities.endpoints.brief') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/entities/{id}/children</code></td><td>{{ t('help.apiGroups.entities.endpoints.children') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/entities/hierarchy/{type}</code></td><td>{{ t('help.apiGroups.entities.endpoints.hierarchy') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/entities/filter-options/location</code></td><td>{{ t('help.apiGroups.entities.endpoints.filterLocation') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/entities/filter-options/attributes</code></td><td>{{ t('help.apiGroups.entities.endpoints.filterAttributes') }}</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="pink" class="mr-2">mdi-brain</v-icon>
                  {{ t('help.apiGroups.smartQuery.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-alert type="info" variant="tonal" class="mb-3">
                    {{ t('help.apiGroups.smartQuery.note') }}
                  </v-alert>
                  <v-table density="compact">
                    <thead><tr><th>{{ t('help.api.tableHeaders.method') }}</th><th>{{ t('help.api.tableHeaders.endpoint') }}</th><th>{{ t('help.api.tableHeaders.description') }}</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/v1/analysis/smart-query</code></td><td>{{ t('help.apiGroups.smartQuery.endpoints.query') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/v1/analysis/smart-write</code></td><td>{{ t('help.apiGroups.smartQuery.endpoints.write') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/analysis/smart-query/examples</code></td><td>{{ t('help.apiGroups.smartQuery.endpoints.examples') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/analysis/templates</code></td><td>{{ t('help.apiGroups.smartQuery.endpoints.templates') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/v1/analysis/templates</code></td><td>{{ t('help.apiGroups.pysis.templates.endpoints.create') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/analysis/templates/{id}</code></td><td>{{ t('help.apiGroups.pysis.templates.endpoints.get') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="warning">PUT</v-chip></td><td><code>/api/v1/analysis/templates/{id}</code></td><td>{{ t('help.apiGroups.pysis.templates.endpoints.update') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="error">DELETE</v-chip></td><td><code>/api/v1/analysis/templates/{id}</code></td><td>{{ t('help.apiGroups.smartQuery.endpoints.deleteTemplate') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/analysis/overview</code></td><td>{{ t('help.apiGroups.smartQuery.endpoints.overview') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/analysis/report/{entity_id}</code></td><td>{{ t('help.apiGroups.smartQuery.endpoints.report') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/analysis/stats</code></td><td>{{ t('help.apiGroups.smartQuery.endpoints.stats') }}</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="orange" class="mr-2">mdi-city</v-icon>
                  {{ t('help.apiGroups.municipalities.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <thead><tr><th>{{ t('help.api.tableHeaders.method') }}</th><th>{{ t('help.api.tableHeaders.endpoint') }}</th><th>{{ t('help.api.tableHeaders.description') }}</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/municipalities</code></td><td>{{ t('help.apiGroups.municipalities.endpoints.list') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/municipalities/{name}/report</code></td><td>{{ t('help.apiGroups.municipalities.endpoints.report') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/municipalities/{name}/documents</code></td><td>{{ t('help.apiGroups.municipalities.endpoints.documents') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/report/overview</code></td><td>{{ t('help.apiGroups.municipalities.endpoints.overview') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/history/municipalities</code></td><td>{{ t('help.apiGroups.municipalities.endpoints.history') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/history/crawls</code></td><td>{{ t('help.apiGroups.municipalities.endpoints.crawlHistory') }}</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="deep-purple" class="mr-2">mdi-export</v-icon>
                  {{ t('help.export.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <thead><tr><th>{{ t('help.api.tableHeaders.method') }}</th><th>{{ t('help.api.tableHeaders.endpoint') }}</th><th>{{ t('help.api.tableHeaders.description') }}</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/export/json</code></td><td>{{ t('help.apiGroups.export.endpoints.json') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/export/csv</code></td><td>{{ t('help.apiGroups.export.endpoints.csv') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/export/changes</code></td><td>{{ t('help.export.apiEndpoints.getChanges') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/v1/export/webhook/test</code></td><td>{{ t('help.export.apiEndpoints.testWebhook') }}</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="pink" class="mr-2">mdi-sync</v-icon>
                  {{ t('help.apiGroups.pysis.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-alert type="info" variant="tonal" class="mb-3">
                    {{ t('help.apiGroups.pysis.note') }}
                  </v-alert>

                  <h4 class="text-subtitle-2 mb-2">{{ t('help.apiGroups.pysis.templates.heading') }}</h4>
                  <v-table density="compact" class="mb-4">
                    <thead><tr><th>{{ t('help.api.tableHeaders.method') }}</th><th>{{ t('help.api.tableHeaders.endpoint') }}</th><th>{{ t('help.api.tableHeaders.description') }}</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/pysis/templates</code></td><td>{{ t('help.apiGroups.pysis.templates.endpoints.list') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/templates</code></td><td>{{ t('help.apiGroups.pysis.templates.endpoints.create') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/pysis/templates/{id}</code></td><td>{{ t('help.apiGroups.pysis.templates.endpoints.get') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="warning">PUT</v-chip></td><td><code>/api/admin/pysis/templates/{id}</code></td><td>{{ t('help.apiGroups.pysis.templates.endpoints.update') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="error">DELETE</v-chip></td><td><code>/api/admin/pysis/templates/{id}</code></td><td>{{ t('help.apiGroups.pysis.templates.endpoints.delete') }}</td></tr>
                    </tbody>
                  </v-table>

                  <h4 class="text-subtitle-2 mb-2">{{ t('help.apiGroups.pysis.processes.heading') }}</h4>
                  <v-table density="compact" class="mb-4">
                    <thead><tr><th>{{ t('help.api.tableHeaders.method') }}</th><th>{{ t('help.api.tableHeaders.endpoint') }}</th><th>{{ t('help.api.tableHeaders.description') }}</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/pysis/available-processes</code></td><td>{{ t('help.apiGroups.pysis.processes.endpoints.available') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/pysis/locations/{name}/processes</code></td><td>{{ t('help.apiGroups.pysis.processes.endpoints.locationProcesses') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/locations/{name}/processes</code></td><td>{{ t('help.apiGroups.pysis.processes.endpoints.createForLocation') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/pysis/processes/{id}</code></td><td>{{ t('help.apiGroups.pysis.processes.endpoints.details') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="warning">PUT</v-chip></td><td><code>/api/admin/pysis/processes/{id}</code></td><td>{{ t('help.apiGroups.pysis.processes.endpoints.update') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="error">DELETE</v-chip></td><td><code>/api/admin/pysis/processes/{id}</code></td><td>{{ t('help.apiGroups.pysis.processes.endpoints.delete') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/processes/{id}/apply-template</code></td><td>{{ t('help.apiGroups.pysis.processes.endpoints.applyTemplate') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/processes/{id}/generate</code></td><td>{{ t('help.apiGroups.pysis.processes.endpoints.generate') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/processes/{id}/sync/pull</code></td><td>{{ t('help.apiGroups.pysis.processes.endpoints.syncPull') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/processes/{id}/sync/push</code></td><td>{{ t('help.apiGroups.pysis.processes.endpoints.syncPush') }}</td></tr>
                    </tbody>
                  </v-table>

                  <h4 class="text-subtitle-2 mb-2">{{ t('help.apiGroups.pysis.fields.heading') }}</h4>
                  <v-table density="compact" class="mb-4">
                    <thead><tr><th>{{ t('help.api.tableHeaders.method') }}</th><th>{{ t('help.api.tableHeaders.endpoint') }}</th><th>{{ t('help.api.tableHeaders.description') }}</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/pysis/processes/{id}/fields</code></td><td>{{ t('help.apiGroups.pysis.fields.endpoints.list') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/processes/{id}/fields</code></td><td>{{ t('help.apiGroups.pysis.fields.endpoints.add') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="warning">PUT</v-chip></td><td><code>/api/admin/pysis/fields/{id}</code></td><td>{{ t('help.apiGroups.pysis.fields.endpoints.update') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="warning">PUT</v-chip></td><td><code>/api/admin/pysis/fields/{id}/value</code></td><td>{{ t('help.apiGroups.pysis.fields.endpoints.setValue') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="error">DELETE</v-chip></td><td><code>/api/admin/pysis/fields/{id}</code></td><td>{{ t('help.apiGroups.pysis.fields.endpoints.delete') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/fields/{id}/generate</code></td><td>{{ t('help.apiGroups.pysis.fields.endpoints.generate') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/fields/{id}/accept-ai</code></td><td>{{ t('help.apiGroups.pysis.fields.endpoints.acceptAi') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/fields/{id}/reject-ai</code></td><td>{{ t('help.apiGroups.pysis.fields.endpoints.rejectAi') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/fields/{id}/sync/push</code></td><td>{{ t('help.apiGroups.pysis.fields.endpoints.syncPush') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/pysis/fields/{id}/history</code></td><td>{{ t('help.apiGroups.pysis.fields.endpoints.history') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/fields/{id}/restore/{history_id}</code></td><td>{{ t('help.apiGroups.pysis.fields.endpoints.restore') }}</td></tr>
                    </tbody>
                  </v-table>

                  <h4 class="text-subtitle-2 mb-2">{{ t('help.apiGroups.pysis.connection.heading') }}</h4>
                  <v-table density="compact">
                    <thead><tr><th>{{ t('help.api.tableHeaders.method') }}</th><th>{{ t('help.api.tableHeaders.endpoint') }}</th><th>{{ t('help.api.tableHeaders.description') }}</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/pysis/test-connection</code></td><td>{{ t('help.apiGroups.pysis.connection.endpoints.test') }}</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="green" class="mr-2">mdi-heart-pulse</v-icon>
                  {{ t('help.apiGroups.system.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <thead><tr><th>{{ t('help.api.tableHeaders.method') }}</th><th>{{ t('help.api.tableHeaders.endpoint') }}</th><th>{{ t('help.api.tableHeaders.description') }}</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/</code></td><td>{{ t('help.apiGroups.system.endpoints.root') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/health</code></td><td>{{ t('help.apiGroups.system.endpoints.health') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/docs</code></td><td>{{ t('help.apiGroups.system.endpoints.swagger') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/redoc</code></td><td>{{ t('help.apiGroups.system.endpoints.redoc') }}</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/openapi.json</code></td><td>{{ t('help.apiGroups.system.endpoints.openapi') }}</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>

            <v-alert type="info" variant="tonal" class="mt-4">
              <v-icon>mdi-information</v-icon>
              {{ t('help.api.fullDocumentation') }}
              <a href="/docs" target="_blank" class="text-primary">/docs</a> (Swagger UI) {{ t('help.api.or') }}
              <a href="/redoc" target="_blank" class="text-primary">/redoc</a> (ReDoc).
            </v-alert>
          </v-card-text>
        </v-card>

        <!-- Tipps -->
        <v-card id="tips" class="mb-4">
          <v-card-title class="text-h5 bg-amber">
            <v-icon class="mr-2">mdi-lightbulb</v-icon>
            {{ t('help.tips.title') }}
          </v-card-title>
          <v-card-text class="pt-4">
            <v-expansion-panels variant="accordion">
              <v-expansion-panel :title="t('help.tips.efficientCrawling.title')">
                <v-expansion-panel-text>
                  <v-list density="compact">
                    <v-list-item prepend-icon="mdi-filter">
                      <v-list-item-title>{{ t('help.tips.efficientCrawling.useBlacklist') }}</v-list-item-title>
                      <v-list-item-subtitle>{{ t('help.tips.efficientCrawling.useBlacklistDesc') }}</v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item prepend-icon="mdi-stairs">
                      <v-list-item-title>{{ t('help.tips.efficientCrawling.limitDepth') }}</v-list-item-title>
                      <v-list-item-subtitle>{{ t('help.tips.efficientCrawling.limitDepthDesc') }}</v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item prepend-icon="mdi-file-document">
                      <v-list-item-title>{{ t('help.tips.efficientCrawling.restrictDocTypes') }}</v-list-item-title>
                      <v-list-item-subtitle>{{ t('help.tips.efficientCrawling.restrictDocTypesDesc') }}</v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel :title="t('help.tips.betterAiResults.title')">
                <v-expansion-panel-text>
                  <v-list density="compact">
                    <v-list-item prepend-icon="mdi-text-box">
                      <v-list-item-title>{{ t('help.tips.betterAiResults.precisePrompts') }}</v-list-item-title>
                      <v-list-item-subtitle>{{ t('help.tips.betterAiResults.precisePromptsDesc') }}</v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item prepend-icon="mdi-tag-multiple">
                      <v-list-item-title>{{ t('help.tips.betterAiResults.optimizeKeywords') }}</v-list-item-title>
                      <v-list-item-subtitle>{{ t('help.tips.betterAiResults.optimizeKeywordsDesc') }}</v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item prepend-icon="mdi-test-tube">
                      <v-list-item-title>{{ t('help.tips.betterAiResults.testFirst') }}</v-list-item-title>
                      <v-list-item-subtitle>{{ t('help.tips.betterAiResults.testFirstDesc') }}</v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel :title="t('help.tips.organization.title')">
                <v-expansion-panel-text>
                  <v-list density="compact">
                    <v-list-item prepend-icon="mdi-folder-multiple">
                      <v-list-item-title>{{ t('help.tips.organization.separateCategories') }}</v-list-item-title>
                      <v-list-item-subtitle>{{ t('help.tips.organization.separateCategoriesDesc') }}</v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item prepend-icon="mdi-map-marker">
                      <v-list-item-title>{{ t('help.tips.organization.maintainLocations') }}</v-list-item-title>
                      <v-list-item-subtitle>{{ t('help.tips.organization.maintainLocationsDesc') }}</v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item prepend-icon="mdi-update">
                      <v-list-item-title>{{ t('help.tips.organization.regularMaintenance') }}</v-list-item-title>
                      <v-list-item-subtitle>{{ t('help.tips.organization.regularMaintenanceDesc') }}</v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </v-card-text>
        </v-card>

        <!-- Sicherheit & Authentifizierung -->
        <v-card id="security" class="mb-4">
          <v-card-title class="text-h5 bg-purple">
            <v-icon class="mr-2">mdi-shield-lock</v-icon>
            {{ t('help.security.title') }}
          </v-card-title>
          <v-card-text class="pt-4">
            <h3 class="text-h6 mb-3">{{ t('help.security.login.heading') }}</h3>
            <p class="mb-4">
              {{ t('help.security.login.description') }}
            </p>

            <v-alert type="info" variant="tonal" class="mb-4">
              <strong>{{ t('help.security.login.important') }}</strong> {{ t('help.security.login.tokenExpiry') }}
            </v-alert>

            <h3 class="text-h6 mb-3">{{ t('help.security.roles.heading') }}</h3>
            <v-table density="compact" class="mb-4">
              <thead>
                <tr><th>{{ t('help.security.roles.role') }}</th><th>{{ t('help.security.roles.permissions') }}</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td><v-chip size="small" color="error">ADMIN</v-chip></td>
                  <td>
                    <ul class="pl-4">
                      <li>{{ t('help.security.roles.admin.fullAccess') }}</li>
                      <li>{{ t('help.security.roles.admin.userManagement') }}</li>
                      <li>{{ t('help.security.roles.admin.auditLog') }}</li>
                      <li>{{ t('help.security.roles.admin.systemConfig') }}</li>
                    </ul>
                  </td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="warning">EDITOR</v-chip></td>
                  <td>
                    <ul class="pl-4">
                      <li>{{ t('help.security.roles.editor.manageCategories') }}</li>
                      <li>{{ t('help.security.roles.editor.controlCrawler') }}</li>
                      <li>{{ t('help.security.roles.editor.processDocuments') }}</li>
                      <li>{{ t('help.security.roles.editor.exportResults') }}</li>
                    </ul>
                  </td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="info">VIEWER</v-chip></td>
                  <td>
                    <ul class="pl-4">
                      <li>{{ t('help.security.roles.viewer.viewData') }}</li>
                      <li>{{ t('help.security.roles.editor.exportResults') }}</li>
                      <li>{{ t('help.security.roles.viewer.noEditRights') }}</li>
                    </ul>
                  </td>
                </tr>
              </tbody>
            </v-table>

            <h3 class="text-h6 mb-3">{{ t('help.security.password.heading') }}</h3>
            <v-alert type="warning" variant="tonal" class="mb-4">
              <strong>{{ t('help.security.password.requirements') }}</strong>
              <ul class="pl-4 mt-2">
                <li>{{ t('help.security.password.minLength') }}</li>
                <li>{{ t('help.security.password.uppercase') }}</li>
                <li>{{ t('help.security.password.lowercase') }}</li>
                <li>{{ t('help.security.password.digit') }}</li>
                <li>{{ t('help.security.password.specialChar') }}</li>
              </ul>
            </v-alert>

            <h3 class="text-h6 mb-3">{{ t('help.security.features.heading') }}</h3>
            <v-expansion-panels variant="accordion" class="mb-4">
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="success" class="mr-2">mdi-shield-check</v-icon>
                  {{ t('help.security.features.rateLimit.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <p>{{ t('help.security.features.rateLimit.description') }}</p>
                  <v-table density="compact" class="mt-2">
                    <thead><tr><th>{{ t('help.security.features.rateLimit.action') }}</th><th>{{ t('help.security.features.rateLimit.limit') }}</th><th>{{ t('help.security.features.rateLimit.timeWindow') }}</th></tr></thead>
                    <tbody>
                      <tr><td>{{ t('help.security.features.rateLimit.loginAttempts') }}</td><td>5</td><td>{{ t('help.security.features.rateLimit.perMinute') }}</td></tr>
                      <tr><td>{{ t('help.security.features.rateLimit.failedLogins') }}</td><td>10</td><td>{{ t('help.security.features.rateLimit.per15Minutes') }}</td></tr>
                      <tr><td>{{ t('help.security.features.rateLimit.passwordChanges') }}</td><td>3</td><td>{{ t('help.security.features.rateLimit.per5Minutes') }}</td></tr>
                      <tr><td>{{ t('help.security.features.rateLimit.apiRequests') }}</td><td>100</td><td>{{ t('help.security.features.rateLimit.perMinute') }}</td></tr>
                    </tbody>
                  </v-table>
                  <v-alert type="info" variant="tonal" class="mt-2" density="compact">
                    {{ t('help.security.features.rateLimit.note') }}
                  </v-alert>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="success" class="mr-2">mdi-logout</v-icon>
                  {{ t('help.security.features.tokenBlacklist.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <p>
                    {{ t('help.security.features.tokenBlacklist.description') }}
                  </p>
                  <v-alert type="success" variant="tonal" class="mt-2" density="compact">
                    {{ t('help.security.features.tokenBlacklist.note') }}
                  </v-alert>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="success" class="mr-2">mdi-lock</v-icon>
                  {{ t('help.security.features.encryption.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <tbody>
                      <tr><td><strong>{{ t('help.security.features.encryption.passwordHashing') }}</strong></td><td>{{ t('help.security.features.encryption.passwordHashingValue') }}</td></tr>
                      <tr><td><strong>{{ t('help.security.features.encryption.tokenSignature') }}</strong></td><td>{{ t('help.security.features.encryption.tokenSignatureValue') }}</td></tr>
                      <tr><td><strong>{{ t('help.security.features.encryption.transport') }}</strong></td><td>{{ t('help.security.features.encryption.transportValue') }}</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="success" class="mr-2">mdi-history</v-icon>
                  {{ t('help.security.features.auditLog.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <p><strong>{{ t('help.security.features.auditLog.auditLogHeading') }}</strong> {{ t('help.security.features.auditLog.description') }}</p>
                  <ul class="pl-4 mb-3">
                    <li>{{ t('help.security.features.auditLog.who') }}</li>
                    <li>{{ t('help.security.features.auditLog.when') }}</li>
                    <li>{{ t('help.security.features.auditLog.what') }}</li>
                  </ul>
                  <p><strong>{{ t('help.security.features.auditLog.versioningHeading') }}</strong> {{ t('help.security.features.auditLog.versioningDescription') }}</p>
                  <ul class="pl-4">
                    <li>{{ t('help.security.features.auditLog.onlyChanges') }}</li>
                    <li>{{ t('help.security.features.auditLog.fullState') }}</li>
                    <li>{{ t('help.security.features.auditLog.snapshots') }}</li>
                  </ul>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>

            <h3 class="text-h6 mb-3">{{ t('help.security.changePassword.heading') }}</h3>
            <v-timeline density="compact" side="end" class="mb-4">
              <v-timeline-item dot-color="primary" size="small">
                <v-card variant="outlined" class="pa-3">
                  <strong>1.</strong> {{ t('help.security.changePassword.step1') }}
                </v-card>
              </v-timeline-item>
              <v-timeline-item dot-color="primary" size="small">
                <v-card variant="outlined" class="pa-3">
                  <strong>2.</strong> {{ t('help.security.changePassword.step2') }}
                </v-card>
              </v-timeline-item>
              <v-timeline-item dot-color="primary" size="small">
                <v-card variant="outlined" class="pa-3">
                  <strong>3.</strong> {{ t('help.security.changePassword.step3') }}
                </v-card>
              </v-timeline-item>
              <v-timeline-item dot-color="success" size="small">
                <v-card variant="outlined" class="pa-3">
                  <strong>4.</strong> {{ t('help.security.changePassword.step4') }}
                </v-card>
              </v-timeline-item>
            </v-timeline>

            <h3 class="text-h6 mb-3">{{ t('help.security.adminFunctions.heading') }}</h3>
            <v-alert type="error" variant="tonal" class="mb-4">
              <strong>{{ t('help.security.adminFunctions.adminOnly') }}</strong>
              {{ t('help.security.adminFunctions.description') }}
            </v-alert>

            <v-row>
              <v-col cols="12" md="6">
                <v-card variant="outlined" class="pa-3 h-100">
                  <h4 class="text-subtitle-1 mb-2">
                    <v-icon class="mr-1">mdi-account-multiple</v-icon>
                    {{ t('help.security.adminFunctions.userManagement.heading') }}
                  </h4>
                  <ul class="pl-4 text-body-2">
                    <li>{{ t('help.security.adminFunctions.userManagement.createUsers') }}</li>
                    <li>{{ t('help.security.adminFunctions.userManagement.assignRoles') }}</li>
                    <li>{{ t('help.security.adminFunctions.userManagement.resetPasswords') }}</li>
                    <li>{{ t('help.security.adminFunctions.userManagement.deactivateUsers') }}</li>
                  </ul>
                </v-card>
              </v-col>
              <v-col cols="12" md="6">
                <v-card variant="outlined" class="pa-3 h-100">
                  <h4 class="text-subtitle-1 mb-2">
                    <v-icon class="mr-1">mdi-clipboard-text-clock</v-icon>
                    {{ t('help.security.adminFunctions.auditLog.heading') }}
                  </h4>
                  <ul class="pl-4 text-body-2">
                    <li>{{ t('help.security.adminFunctions.auditLog.viewActivities') }}</li>
                    <li>{{ t('help.security.adminFunctions.auditLog.filterByUser') }}</li>
                    <li>{{ t('help.security.adminFunctions.auditLog.trackChanges') }}</li>
                    <li>{{ t('help.security.adminFunctions.auditLog.securityChecks') }}</li>
                  </ul>
                </v-card>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>

        <!-- Fehlerbehebung -->
        <v-card id="troubleshooting" class="mb-4">
          <v-card-title class="text-h5 bg-red">
            <v-icon class="mr-2">mdi-wrench</v-icon>
            {{ t('help.troubleshooting.title') }}
          </v-card-title>
          <v-card-text class="pt-4">
            <v-expansion-panels variant="accordion">
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="error" class="mr-2">mdi-alert</v-icon>
                  {{ t('help.troubleshooting.noDocuments.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <strong>{{ t('help.troubleshooting.noDocuments.possibleCauses') }}</strong>
                  <ul class="pl-4 mb-3">
                    <li>{{ t('help.troubleshooting.noDocuments.causes.excludePatterns') }}</li>
                    <li>{{ t('help.troubleshooting.noDocuments.causes.includePatterns') }}</li>
                    <li>{{ t('help.troubleshooting.noDocuments.causes.hiddenBehindJs') }}</li>
                    <li>{{ t('help.troubleshooting.noDocuments.causes.blockedCrawler') }}</li>
                  </ul>
                  <strong>{{ t('help.troubleshooting.noDocuments.solutions') }}</strong>
                  <ul class="pl-4">
                    <li>{{ t('help.troubleshooting.noDocuments.solutionSteps.checkBlacklist') }}</li>
                    <li>{{ t('help.troubleshooting.noDocuments.solutionSteps.emptyWhitelist') }}</li>
                    <li>{{ t('help.troubleshooting.noDocuments.solutionSteps.enableJs') }}</li>
                    <li>{{ t('help.troubleshooting.noDocuments.solutionSteps.increaseDepth') }}</li>
                  </ul>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="error" class="mr-2">mdi-alert</v-icon>
                  {{ t('help.troubleshooting.noAiResults.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <strong>{{ t('help.troubleshooting.noDocuments.possibleCauses') }}</strong>
                  <ul class="pl-4 mb-3">
                    <li>{{ t('help.troubleshooting.noAiResults.causes.strictKeywords') }}</li>
                    <li>{{ t('help.troubleshooting.noAiResults.causes.noRelevantContent') }}</li>
                    <li>{{ t('help.troubleshooting.noAiResults.causes.unsuitablePrompt') }}</li>
                  </ul>
                  <strong>{{ t('help.troubleshooting.noDocuments.solutions') }}</strong>
                  <ul class="pl-4">
                    <li>{{ t('help.troubleshooting.noAiResults.solutionSteps.expandKeywords') }}</li>
                    <li>{{ t('help.troubleshooting.noAiResults.solutionSteps.analyzeFiltered') }}</li>
                    <li>{{ t('help.troubleshooting.noAiResults.solutionSteps.optimizePrompt') }}</li>
                  </ul>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="warning" class="mr-2">mdi-clock-alert</v-icon>
                  {{ t('help.troubleshooting.pendingDocuments.title') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <strong>{{ t('help.troubleshooting.noDocuments.possibleCauses') }}</strong>
                  <ul class="pl-4 mb-3">
                    <li>{{ t('help.troubleshooting.pendingDocuments.causes.workerInactive') }}</li>
                    <li>{{ t('help.troubleshooting.pendingDocuments.causes.queueOverloaded') }}</li>
                  </ul>
                  <strong>{{ t('help.troubleshooting.noDocuments.solutions') }}</strong>
                  <ul class="pl-4">
                    <li>{{ t('help.troubleshooting.pendingDocuments.solutionSteps.checkWorker') }}</li>
                    <li>{{ t('help.troubleshooting.pendingDocuments.solutionSteps.manualProcess') }}</li>
                  </ul>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>

            <h3 class="text-h6 mt-4 mb-3">{{ t('help.troubleshooting.statusCodes.heading') }}</h3>
            <v-table density="compact">
              <thead><tr><th>{{ t('help.troubleshooting.statusCodes.status') }}</th><th>{{ t('help.troubleshooting.statusCodes.meaning') }}</th><th>{{ t('help.troubleshooting.statusCodes.action') }}</th></tr></thead>
              <tbody>
                <tr>
                  <td><v-chip size="small" color="warning">PENDING</v-chip></td>
                  <td>{{ t('help.troubleshooting.statusCodes.pending.meaning') }}</td>
                  <td>{{ t('help.troubleshooting.statusCodes.pending.action') }}</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="info">PROCESSING</v-chip></td>
                  <td>{{ t('help.troubleshooting.statusCodes.processing.meaning') }}</td>
                  <td>{{ t('help.troubleshooting.statusCodes.processing.action') }}</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="secondary">ANALYZING</v-chip></td>
                  <td>{{ t('help.troubleshooting.statusCodes.analyzing.meaning') }}</td>
                  <td>Abwarten</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="success">COMPLETED</v-chip></td>
                  <td>{{ t('help.troubleshooting.statusCodes.completed.meaning') }}</td>
                  <td>{{ t('help.troubleshooting.statusCodes.completed.action') }}</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="grey">FILTERED</v-chip></td>
                  <td>{{ t('help.troubleshooting.statusCodes.filtered.meaning') }}</td>
                  <td>{{ t('help.troubleshooting.statusCodes.filtered.action') }}</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="error">FAILED</v-chip></td>
                  <td>{{ t('help.troubleshooting.statusCodes.failed.meaning') }}</td>
                  <td>{{ t('help.troubleshooting.statusCodes.failed.action') }}</td>
                </tr>
              </tbody>
            </v-table>
          </v-card-text>
        </v-card>

      </v-col>

      <!-- Sidebar TOC (Desktop) -->
      <v-col cols="3" class="d-none d-lg-block">
        <v-card class="position-sticky" style="top: 80px;">
          <v-card-title class="text-subtitle-1">{{ t('help.sidebar.title') }}</v-card-title>
          <v-list density="compact" nav>
            <v-list-item
              v-for="section in sections"
              :key="section.id"
              :class="{ 'v-list-item--active': activeSection === section.id }"
              @click="scrollTo(section.id)"
            >
              <template v-slot:prepend>
                <v-icon size="small">{{ section.icon }}</v-icon>
              </template>
              <v-list-item-title class="text-body-2">{{ section.title }}</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const activeSection = ref('intro')

const sections = [
  { id: 'intro', title: t('help.sections.intro'), icon: 'mdi-information' },
  { id: 'quickstart', title: t('help.sections.quickstart'), icon: 'mdi-rocket-launch' },
  { id: 'smart-query', title: t('help.sections.smartQuery'), icon: 'mdi-brain' },
  { id: 'dashboard', title: t('help.sections.dashboard'), icon: 'mdi-view-dashboard' },
  { id: 'categories', title: t('help.sections.categories'), icon: 'mdi-folder-multiple' },
  { id: 'sources', title: t('help.sections.sources'), icon: 'mdi-web' },
  { id: 'crawler', title: t('help.sections.crawler'), icon: 'mdi-robot' },
  { id: 'documents', title: t('help.sections.documents'), icon: 'mdi-file-document-multiple' },
  { id: 'municipalities', title: t('help.sections.municipalities'), icon: 'mdi-city' },
  { id: 'entity-facet', title: t('help.sections.entityFacet'), icon: 'mdi-database' },
  { id: 'facet-type-admin', title: t('help.sections.facetTypeAdmin'), icon: 'mdi-tag-multiple' },
  { id: 'results', title: t('help.sections.results'), icon: 'mdi-chart-bar' },
  { id: 'export', title: t('help.sections.export'), icon: 'mdi-export' },
  { id: 'notifications', title: t('help.sections.notifications'), icon: 'mdi-bell' },
  { id: 'api', title: t('help.sections.api'), icon: 'mdi-api' },
  { id: 'tips', title: t('help.sections.tips'), icon: 'mdi-lightbulb' },
  { id: 'security', title: t('help.sections.security'), icon: 'mdi-shield-lock' },
  { id: 'troubleshooting', title: t('help.sections.troubleshooting'), icon: 'mdi-wrench' },
]

const scrollTo = (id: string) => {
  const element = document.getElementById(id)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' })
    activeSection.value = id
  }
}

// Track active section on scroll
let observer: IntersectionObserver | null = null

onMounted(() => {
  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          activeSection.value = entry.target.id
        }
      })
    },
    { threshold: 0.3, rootMargin: '-100px 0px -50% 0px' }
  )

  sections.forEach((section) => {
    const element = document.getElementById(section.id)
    if (element) observer?.observe(element)
  })
})

onUnmounted(() => {
  observer?.disconnect()
})
</script>

<style scoped>
.v-code {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  border-radius: 4px;
  font-family: monospace;
}
</style>
