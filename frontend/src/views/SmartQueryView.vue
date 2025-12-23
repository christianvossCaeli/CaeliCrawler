<template>
  <div class="smart-query-view">
    <!-- Modern Header with Mode Toggle -->
    <PageHeader
      :title="t('smartQueryView.title')"
      :subtitle="t('smartQueryView.subtitle')"
      icon="mdi-brain"
    >
      <template #actions>
        <div class="mode-toggle-block">
          <v-btn-toggle
            v-model="currentMode"
            mandatory
            divided
            density="comfortable"
            class="mode-toggle"
            :disabled="previewData !== null"
          >
            <v-btn value="read" min-width="110">
              <v-icon start :color="currentMode === 'read' ? 'primary' : undefined">mdi-magnify</v-icon>
              {{ t('smartQueryView.mode.read') }}
            </v-btn>
            <v-btn value="write" min-width="110">
              <v-icon start :color="currentMode === 'write' ? 'warning' : undefined">mdi-pencil-plus</v-icon>
              {{ t('smartQueryView.mode.write') }}
            </v-btn>
            <v-btn value="plan" min-width="110">
              <v-icon start :color="currentMode === 'plan' ? 'info' : undefined">mdi-lightbulb-on</v-icon>
              {{ t('smartQueryView.mode.plan') }}
            </v-btn>
          </v-btn-toggle>
          <div class="mode-toggle-hint text-caption text-medium-emphasis">
            {{ modeHint }}
          </div>
        </div>

        <!-- History Toggle Button -->
        <v-btn
          icon
          variant="tonal"
          :color="showHistory ? 'primary' : undefined"
          @click="showHistory = !showHistory"
        >
          <v-badge
            v-if="historyStore.favoriteCount > 0"
            :content="historyStore.favoriteCount"
            color="warning"
            floating
          >
            <v-icon>mdi-history</v-icon>
          </v-badge>
          <v-icon v-else>mdi-history</v-icon>
          <v-tooltip activator="parent" location="bottom">
            {{ t('smartQuery.history.title') }}
          </v-tooltip>
        </v-btn>
      </template>
    </PageHeader>

    <!-- Chat-Style Input Card -->
    <v-card class="input-card mb-6" :class="{ 'input-card--active': question.trim() || pendingAttachments.length > 0 }">
      <!-- Attachment Preview inside card -->
      <div v-if="pendingAttachments.length > 0" class="attachment-preview pa-3 pb-0">
        <div class="d-flex flex-wrap ga-2">
          <v-chip
            v-for="attachment in pendingAttachments"
            :key="attachment.id"
            closable
            @click:close="removeAttachment(attachment.id)"
            color="primary"
            variant="tonal"
            size="small"
          >
            <v-avatar start size="20" v-if="attachment.preview">
              <v-img :src="attachment.preview" />
            </v-avatar>
            <v-icon v-else start size="16">{{ getAttachmentIcon(attachment.contentType) }}</v-icon>
            {{ attachment.filename }}
          </v-chip>
        </div>
      </div>

      <!-- Textarea -->
      <v-textarea
        v-model="question"
        :placeholder="getInputPlaceholder"
        rows="2"
        auto-grow
        max-rows="8"
        variant="plain"
        hide-details
        class="input-textarea"
        :disabled="previewData !== null"
        @paste="handlePaste"
        @keydown.enter.ctrl="executeQuery"
        @keydown.enter.meta="executeQuery"
      />

      <!-- Interim transcript overlay -->
      <div v-if="interimTranscript" class="interim-transcript px-4 pb-2">
        <span class="text-caption text-medium-emphasis font-italic">
          <v-icon size="12" class="mr-1">mdi-microphone</v-icon>
          {{ interimTranscript }}
        </span>
      </div>

      <v-divider />

      <!-- Action Bar -->
      <div class="input-actions">
        <div class="action-buttons d-flex ga-1">
          <!-- Attachment Button -->
          <v-btn
            icon
            variant="text"
            size="small"
            :disabled="previewData !== null || loading || isUploading"
            :loading="isUploading"
            @click="triggerFileInput"
          >
            <v-icon size="20">mdi-paperclip</v-icon>
            <v-tooltip activator="parent" location="top">
              {{ t('assistant.attachFile') }}
            </v-tooltip>
          </v-btn>
          <input
            ref="fileInputRef"
            type="file"
            accept="image/png,image/jpeg,image/gif,image/webp,application/pdf"
            style="display: none"
            @change="handleFileSelect"
            multiple
          />

          <!-- Voice Button -->
          <v-btn
            v-if="hasMicrophone"
            icon
            variant="text"
            size="small"
            :color="isListening ? 'error' : undefined"
            :class="{ 'voice-btn-listening': isListening }"
            :disabled="previewData !== null || loading"
            @click="handleVoiceInput"
          >
            <v-icon size="20">{{ isListening ? 'mdi-microphone-off' : 'mdi-microphone' }}</v-icon>
            <v-tooltip activator="parent" location="top">
              {{ isListening ? t('smartQueryView.voice.stopRecording') : t('smartQueryView.voice.startRecording') }}
            </v-tooltip>
          </v-btn>

          <!-- Write Mode Indicator -->
          <v-chip v-if="writeMode && !previewData" color="warning" size="x-small" variant="flat" class="ml-2">
            <v-icon start size="12">mdi-eye</v-icon>
            {{ t('smartQueryView.mode.previewFirst') }}
          </v-chip>
        </div>

        <!-- Submit Button -->
        <v-btn
          v-if="!previewData"
          :color="getSubmitButtonColor"
          rounded="pill"
          :loading="loading"
          :disabled="!question.trim() && pendingAttachments.length === 0"
          @click="executeQuery"
          class="submit-btn"
        >
          <v-icon start>{{ getSubmitButtonIcon }}</v-icon>
          {{ getSubmitButtonText }}
        </v-btn>
      </div>
    </v-card>

    <!-- Plan Mode Chat Interface -->
    <v-card v-if="currentMode === 'plan'" class="plan-mode-card mb-6">
      <PlanModeChat
        :conversation="planConversation"
        :loading="planLoading"
        :generated-prompt="planGeneratedPrompt"
        @send="(msg) => { question = msg; executePlanQuery() }"
        @adopt-prompt="adoptPrompt"
        @reset="handlePlanReset"
      />
    </v-card>

    <!-- Example Queries as Card Grid (only for read/write modes) -->
    <div v-if="!results && !previewData && !loading && currentMode !== 'plan'" class="examples-section mb-6">
      <div class="d-flex align-center mb-4">
        <v-icon class="mr-2" :color="writeMode ? 'warning' : 'primary'">mdi-lightbulb-outline</v-icon>
        <span class="text-subtitle-1 font-weight-medium">
          {{ writeMode ? t('smartQueryView.examples.commandsTitle') : t('smartQueryView.examples.questionsTitle') }}
        </span>
      </div>
      <div class="examples-grid">
        <v-card
          v-for="example in currentExamplesWithMeta"
          :key="example.question"
          class="example-card"
          :class="{ 'example-card--write': writeMode }"
          @click="useExample(example.question)"
          hover
          variant="outlined"
        >
          <v-card-text class="example-card-content pa-4">
            <div class="example-main">
              <v-avatar
                :color="writeMode ? 'warning' : 'primary'"
                size="44"
                class="example-avatar"
                variant="tonal"
              >
                <v-icon size="22">{{ example.icon }}</v-icon>
              </v-avatar>
              <div class="example-text-block">
                <div class="text-body-2 font-weight-medium example-title">{{ example.title }}</div>
                <div class="text-caption text-medium-emphasis example-question">{{ example.question }}</div>
              </div>
            </div>
            <v-icon size="18" class="example-arrow" color="grey">mdi-arrow-right</v-icon>
          </v-card-text>
        </v-card>
      </div>
    </div>

    <!-- Error -->
    <v-alert v-if="error" type="error" class="mb-6" closable @click:close="error = null">
      {{ error }}
    </v-alert>

    <!-- Loading State - Read Mode -->
    <div v-if="loading && !writeMode" class="loading-section mb-6">
      <v-card class="loading-card">
        <v-card-text class="text-center py-8">
          <div class="loading-animation mb-4">
            <v-progress-circular
              indeterminate
              size="56"
              width="4"
              color="primary"
            />
          </div>
          <div class="text-h6 mb-2">{{ t('smartQueryView.loading.analyzing') }}</div>
          <div class="text-body-2 text-medium-emphasis">{{ t('smartQueryView.loading.pleaseWait') }}</div>
        </v-card-text>
      </v-card>
    </div>

    <!-- AI Generation Progress - Write Mode -->
    <v-card v-if="loading && writeMode" class="mb-6 generation-card">
      <v-card-text class="pa-6">
        <div class="d-flex align-center mb-6">
          <v-avatar color="warning" size="48" class="mr-4">
            <v-icon size="24" class="generation-icon">mdi-robot</v-icon>
          </v-avatar>
          <div>
            <div class="text-h6">{{ t('smartQueryView.generation.running') }}</div>
            <div class="text-body-2 text-medium-emphasis">{{ t('smartQueryView.generation.processing') }}</div>
          </div>
        </div>

        <!-- Timeline Steps -->
        <v-timeline density="compact" side="end" class="generation-timeline">
          <v-timeline-item
            v-for="step in generationSteps"
            :key="step.value"
            :dot-color="getStepColor(step.value)"
            size="small"
          >
            <template #icon>
              <v-icon v-if="currentStep > step.value" size="16" color="white">mdi-check</v-icon>
              <v-progress-circular
                v-else-if="currentStep === step.value"
                indeterminate
                size="16"
                width="2"
                color="white"
              />
            </template>
            <div class="d-flex align-center">
              <div>
                <div class="text-body-2 font-weight-medium" :class="{ 'text-medium-emphasis': currentStep < step.value }">
                  {{ step.title }}
                </div>
                <div class="text-caption text-medium-emphasis">{{ step.subtitle }}</div>
              </div>
            </div>
          </v-timeline-item>
        </v-timeline>
      </v-card-text>
    </v-card>

    <!-- Preview Mode (Write) -->
    <template v-if="previewData">
      <v-card class="mb-4" color="warning" variant="tonal">
        <v-card-title>
          <v-icon left>mdi-eye-check</v-icon>
          {{ t('smartQueryView.preview.title') }}
        </v-card-title>
        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-4">
            <strong>{{ previewData.preview?.operation_de }}</strong>
            <div class="mt-1">{{ previewData.preview?.description }}</div>
          </v-alert>

          <v-card variant="outlined" class="mb-4">
            <v-card-title class="text-subtitle-1">
              <v-icon left size="small">mdi-format-list-bulleted</v-icon>
              {{ t('common.details') }}
            </v-card-title>
            <v-card-text>
              <v-list density="compact" class="bg-transparent">
                <v-list-item
                  v-for="(detail, idx) in previewData.preview?.details || []"
                  :key="idx"
                  :title="detail"
                >
                  <template v-slot:prepend>
                    <v-icon size="small" color="primary">mdi-check</v-icon>
                  </template>
                </v-list-item>
              </v-list>
            </v-card-text>
          </v-card>

          <!-- Technical Details -->
          <v-expansion-panels variant="accordion">
            <v-expansion-panel :title="t('smartQueryView.preview.technicalDetails')">
              <v-expansion-panel-text>
                <pre class="text-caption">{{ JSON.stringify(previewData.interpretation, null, 2) }}</pre>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="tonal" @click="cancelPreview">
            <v-icon start>mdi-close</v-icon>
            {{ t('common.cancel') }}
          </v-btn>
          <v-btn color="success" variant="elevated" :loading="loading" @click="confirmWrite">
            <v-icon start>mdi-check</v-icon>
            {{ t('smartQueryView.preview.confirmAndCreate') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </template>

    <!-- Write Results -->
    <template v-if="results?.mode === 'write'">
      <v-card class="mb-4" :color="results.success ? 'success' : 'error'" variant="tonal">
        <v-card-title>
          <v-icon left>{{ results.success ? 'mdi-check-circle' : 'mdi-alert-circle' }}</v-icon>
          {{ results.success ? t('smartQueryView.results.successfullyCreated') : t('common.error') }}
        </v-card-title>
        <v-card-text>
          <div class="text-body-1 mb-3">{{ results.message }}</div>

          <!-- Created Items -->
          <template v-if="results.created_items?.length > 0">
            <div class="text-subtitle-2 mb-2">{{ t('smartQueryView.results.createdItems') }}</div>
            <v-list density="compact" class="bg-transparent">
              <v-list-item
                v-for="item in results.created_items"
                :key="item.id"
                :title="item.name || item.type"
                :subtitle="`${item.type}${item.entity_type ? ' (' + item.entity_type + ')' : ''}${item.slug ? ' [' + item.slug + ']' : ''} - ID: ${item.id.substring(0, 8)}...`"
              >
                <template v-slot:prepend>
                  <v-icon :color="getItemTypeColor(item.type)">
                    {{ getItemTypeIcon(item.type) }}
                  </v-icon>
                </template>
              </v-list-item>
            </v-list>
          </template>

          <!-- Crawl Information -->
          <template v-if="results.sources_count || results.crawl_jobs?.length > 0">
            <v-divider class="my-3" />
            <div class="text-subtitle-2 mb-2">
              <v-icon left size="small">mdi-spider-web</v-icon>
              {{ t('smartQueryView.results.crawlDetails') }}
            </div>
            <v-chip v-if="results.sources_count" class="mr-2 mb-2" color="info" size="small">
              {{ t('smartQueryView.results.dataSources', { count: results.sources_count }) }}
            </v-chip>
            <v-chip v-if="results.crawl_jobs?.length" class="mr-2 mb-2" color="success" size="small">
              {{ t('smartQueryView.results.jobsStarted', { count: results.crawl_jobs.length }) }}
            </v-chip>
          </template>

          <!-- Linked Sources -->
          <template v-if="results.linked_sources_count">
            <v-divider class="my-3" />
            <div class="text-subtitle-2 mb-2">
              <v-icon left size="small">mdi-link-variant</v-icon>
              {{ t('smartQueryView.results.dataSourcesLink') }}
            </div>
            <v-chip color="primary" size="small">
              {{ t('smartQueryView.results.dataSourcesLinked', { count: results.linked_sources_count }) }}
            </v-chip>
          </template>

          <!-- AI Generation Steps -->
          <template v-if="results.steps?.length > 0">
            <v-divider class="my-3" />
            <div class="text-subtitle-2 mb-2">
              <v-icon left size="small">mdi-robot</v-icon>
              {{ t('smartQueryView.results.aiGenerationSteps') }}
            </div>
            <v-timeline density="compact" side="end">
              <v-timeline-item
                v-for="(step, idx) in results.steps"
                :key="idx"
                :dot-color="step.success !== false ? 'success' : 'error'"
                size="x-small"
              >
                <div>
                  <div class="d-flex align-center">
                    <v-icon :color="step.success !== false ? 'success' : 'error'" size="small" class="mr-2">
                      {{ step.success !== false ? 'mdi-check' : 'mdi-close' }}
                    </v-icon>
                    <span class="text-body-2 font-weight-medium">{{ t('smartQueryView.results.step', { current: step.step, total: step.total }) }}</span>
                  </div>
                  <div class="text-caption text-medium-emphasis ml-6">{{ step.message }}</div>
                  <div v-if="step.result" class="text-caption text-success ml-6">{{ step.result }}</div>
                </div>
              </v-timeline-item>
            </v-timeline>
          </template>

          <!-- AI-Generated Search Terms -->
          <template v-if="results.search_terms?.length > 0">
            <v-divider class="my-3" />
            <div class="text-subtitle-2 mb-2">
              <v-icon left size="small">mdi-magnify</v-icon>
              {{ t('smartQueryView.results.aiSearchTerms') }}
            </div>
            <v-chip
              v-for="term in results.search_terms"
              :key="term"
              size="small"
              class="mr-1 mb-1"
              color="info"
              variant="outlined"
            >
              {{ term }}
            </v-chip>
          </template>

          <!-- AI-Generated URL Patterns -->
          <template v-if="results.url_patterns?.include?.length > 0 || results.url_patterns?.exclude?.length > 0">
            <v-divider class="my-3" />
            <div class="text-subtitle-2 mb-2">
              <v-icon left size="small">mdi-web</v-icon>
              {{ t('smartQueryView.results.urlPatternConfig') }}
            </div>
            <div v-if="results.url_patterns?.reasoning" class="text-caption text-medium-emphasis mb-3">
              {{ results.url_patterns.reasoning }}
            </div>
            <div v-if="results.url_patterns?.include?.length > 0" class="mb-2">
              <div class="text-caption text-success mb-1">{{ t('smartQueryView.results.includePatterns') }}</div>
              <v-chip
                v-for="pattern in results.url_patterns.include"
                :key="pattern"
                size="small"
                class="mr-1 mb-1"
                color="success"
                variant="tonal"
              >
                <code>{{ pattern }}</code>
              </v-chip>
            </div>
            <div v-if="results.url_patterns?.exclude?.length > 0">
              <div class="text-caption text-error mb-1">{{ t('smartQueryView.results.excludePatterns') }}</div>
              <v-chip
                v-for="pattern in results.url_patterns.exclude"
                :key="pattern"
                size="small"
                class="mr-1 mb-1"
                color="error"
                variant="tonal"
              >
                <code>{{ pattern }}</code>
              </v-chip>
            </div>
          </template>

          <!-- AI Extraction Prompt -->
          <template v-if="results.ai_extraction_prompt">
            <v-divider class="my-3" />
            <v-expansion-panels variant="accordion">
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon left size="small" class="mr-2">mdi-brain</v-icon>
                  {{ t('smartQueryView.results.aiExtractionPrompt') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <pre class="text-caption text-pre-wrap">{{ results.ai_extraction_prompt }}</pre>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </template>

          <!-- Combined Operation Results -->
          <template v-if="results.operation_results?.length > 0">
            <v-divider class="my-3" />
            <div class="text-subtitle-2 mb-2">
              <v-icon left size="small">mdi-format-list-checks</v-icon>
              {{ t('smartQueryView.results.executedOperations') }}
            </div>
            <v-list density="compact" class="bg-transparent">
              <v-list-item
                v-for="(opResult, idx) in results.operation_results"
                :key="idx"
                :title="opResult.operation"
                :subtitle="opResult.message"
              >
                <template v-slot:prepend>
                  <v-icon :color="opResult.success ? 'success' : 'error'" size="small">
                    {{ opResult.success ? 'mdi-check' : 'mdi-close' }}
                  </v-icon>
                </template>
              </v-list-item>
            </v-list>
          </template>

          <!-- Interpretation -->
          <v-expansion-panels variant="accordion" class="mt-3">
            <v-expansion-panel :title="t('smartQueryView.results.interpretation')">
              <v-expansion-panel-text>
                <pre class="text-caption">{{ JSON.stringify(results.interpretation, null, 2) }}</pre>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-card-text>
        <v-card-actions>
          <v-btn variant="tonal" @click="resetAll">{{ t('smartQueryView.results.newCommand') }}</v-btn>
          <v-spacer />
          <v-btn
            v-if="fromAssistant"
            color="primary"
            variant="elevated"
            @click="sendResultsToAssistant"
          >
            <v-icon start>mdi-arrow-left</v-icon>
            {{ t('smartQueryView.results.backToAssistant') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </template>

    <!-- Compound Query Results (multiple visualizations) -->
    <transition name="compound-result" appear>
      <div v-if="results?.is_compound" class="compound-results-wrapper">
        <!-- Successful compound query with visualizations -->
        <template v-if="results?.visualizations?.length > 0">
          <v-card class="mb-4 content-reveal">
            <CompoundQueryResult
              :visualizations="results.visualizations"
              :explanation="results.explanation"
              :suggested-actions="results.suggested_actions || []"
              @action="handleVisualizationAction"
            />
          </v-card>
        </template>

        <!-- Compound query with no visualizations (edge case / error) -->
        <template v-else>
          <v-alert type="warning" variant="tonal" class="mb-4">
            <v-alert-title>{{ t('smartQueryView.errors.noVisualizationsTitle') }}</v-alert-title>
            {{ results.error || results.explanation || t('smartQueryView.errors.noVisualizationsHint') }}
          </v-alert>
        </template>

        <div class="d-flex justify-center">
          <v-btn variant="tonal" @click="resetAll">
            <v-icon start>mdi-refresh</v-icon>
            {{ t('smartQueryView.results.newQuery') }}
          </v-btn>
        </div>
      </div>
    </transition>

    <!-- Visualization Results (single query with visualization) -->
    <template v-else-if="results?.visualization && !results?.is_compound && results?.mode === 'read'">
      <v-card class="mb-4">
        <SmartQueryResult
          :data="results.items || results.data || []"
          :visualization="results.visualization"
          :explanation="results.explanation"
          :source-info="results.source_info"
          :suggested-actions="results.suggested_actions || []"
          @action="handleVisualizationAction"
        />
      </v-card>
      <v-card-actions class="justify-center">
        <v-btn variant="tonal" @click="resetAll">
          <v-icon start>mdi-refresh</v-icon>
          {{ t('smartQueryView.results.newQuery') }}
        </v-btn>
      </v-card-actions>
    </template>

    <!-- Legacy Read Results (without visualization - for backwards compatibility) -->
    <template v-else-if="results?.mode === 'read' && !results?.visualization && !results?.is_compound">
      <!-- Compact Interpretation Bar -->
      <div class="interpretation-bar mb-4 pa-4 d-flex align-center flex-wrap ga-2">
        <v-icon size="20" class="mr-2" color="primary">mdi-brain</v-icon>
        <v-chip size="small" color="primary" variant="flat" class="mr-1">
          <v-icon start size="14">{{ getEntityTypeIcon(results.query_interpretation?.primary_entity_type) }}</v-icon>
          {{ results.query_interpretation?.primary_entity_type }}
        </v-chip>
        <v-chip
          v-for="facet in results.query_interpretation?.facet_types || []"
          :key="facet"
          size="small"
          color="secondary"
          variant="tonal"
          class="mr-1"
        >
          <v-icon start size="14">mdi-tag</v-icon>
          {{ facet }}
        </v-chip>
        <v-chip size="small" :color="getTimeFilterColor(results.query_interpretation?.time_filter)" variant="tonal">
          <v-icon start size="14">mdi-clock-outline</v-icon>
          {{ results.query_interpretation?.time_filter || 'all' }}
        </v-chip>
        <v-spacer />
        <span class="text-body-2 text-medium-emphasis" v-if="results.query_interpretation?.explanation">
          {{ results.query_interpretation.explanation }}
        </span>
      </div>

      <!-- Results Summary Card -->
      <v-card class="results-summary-card mb-6">
        <v-card-text class="d-flex align-center py-4">
          <v-avatar color="success" size="44" class="mr-4" variant="tonal">
            <v-icon>mdi-check</v-icon>
          </v-avatar>
          <div>
            <div class="text-h5 font-weight-bold">{{ results.total }}</div>
            <div class="text-body-2 text-medium-emphasis">{{ t('smartQueryView.read.resultsFound') }}</div>
          </div>
          <v-spacer />
          <v-chip size="small" variant="outlined" class="text-capitalize">
            <v-icon start size="14">mdi-view-list</v-icon>
            {{ results.grouping || 'flat' }}
          </v-chip>
          <v-btn
            variant="tonal"
            size="small"
            class="ml-3"
            @click="resetAll"
          >
            <v-icon start size="18">mdi-refresh</v-icon>
            {{ t('smartQueryView.results.newQuery') }}
          </v-btn>
        </v-card-text>
      </v-card>

      <!-- Event-grouped Results -->
      <transition-group name="result-list" tag="div" v-if="results.grouping === 'by_event'">
        <v-card
          v-for="(event, index) in results.items"
          :key="event.event_name"
          class="result-card mb-4"
          :style="{ '--animation-delay': `${index * 50}ms` }"
        >
          <v-card-text class="pa-0">
            <div class="result-card-header pa-4 d-flex align-center">
              <v-avatar color="orange" size="48" variant="tonal" class="mr-4">
                <v-icon>mdi-calendar-star</v-icon>
              </v-avatar>
              <div class="flex-grow-1">
                <div class="text-h6">{{ event.event_name }}</div>
                <div class="d-flex align-center ga-3 text-body-2 text-medium-emphasis">
                  <span><v-icon size="14" class="mr-1">mdi-calendar</v-icon>{{ event.event_date || t('smartQueryView.read.dateUnknown') }}</span>
                  <span><v-icon size="14" class="mr-1">mdi-map-marker</v-icon>{{ event.event_location || t('smartQueryView.read.locationUnknown') }}</span>
                </div>
              </div>
              <v-chip size="small" color="primary" variant="tonal">
                {{ event.attendees?.length || 0 }} {{ t('smartQueryView.read.attendeesLabel') }}
              </v-chip>
            </div>
            <v-divider />
            <v-list density="compact" class="py-0">
              <v-list-item
                v-for="attendee in event.attendees"
                :key="attendee.person_id"
                class="attendee-item"
              >
                <template v-slot:prepend>
                  <v-avatar color="primary" size="36" variant="tonal">
                    <span class="text-caption font-weight-bold">{{ getInitials(attendee.person_name) }}</span>
                  </v-avatar>
                </template>
                <v-list-item-title class="font-weight-medium">{{ attendee.person_name }}</v-list-item-title>
                <v-list-item-subtitle>{{ formatAttendeeSubtitle(attendee) }}</v-list-item-subtitle>
                <template v-slot:append>
                  <v-chip v-if="attendee.role" size="x-small" color="info" variant="tonal">
                    {{ attendee.role }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </transition-group>

      <!-- Flat Results Grid -->
      <div v-else class="results-grid">
        <transition-group name="result-list" tag="div" class="results-grid-inner">
          <v-card
            v-for="(item, index) in results.items"
            :key="item.entity_id"
            class="result-card"
            :style="{ '--animation-delay': `${index * 50}ms` }"
          >
            <v-card-text class="pa-4">
              <div class="d-flex align-start mb-3">
                <v-avatar
                  :color="getEntityTypeColor(item.entity_type)"
                  size="44"
                  variant="tonal"
                  class="mr-3"
                >
                  <v-icon size="22">{{ getEntityTypeIcon(item.entity_type) }}</v-icon>
                </v-avatar>
                <div class="flex-grow-1 overflow-hidden">
                  <div class="text-subtitle-1 font-weight-bold text-truncate">{{ item.entity_name }}</div>
                  <div v-if="item.attributes?.position" class="text-body-2 text-medium-emphasis">
                    {{ item.attributes.position }}
                    <span v-if="item.relations?.works_for" class="text-primary">
                      @ {{ item.relations.works_for.entity_name }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- Facets -->
              <template v-if="Object.keys(item.facets || {}).length > 0">
                <template v-for="(values, facetType) in item.facets" :key="facetType">
                  <div v-if="values.length > 0" class="facet-group mb-2">
                    <div class="text-caption text-medium-emphasis mb-1 d-flex align-center">
                      <v-icon size="12" class="mr-1">mdi-tag-outline</v-icon>
                      {{ facetType }}
                      <span class="ml-1">({{ values.length }})</span>
                    </div>
                    <div class="d-flex flex-wrap ga-1">
                      <v-chip
                        v-for="fv in values.slice(0, 3)"
                        :key="fv.id"
                        size="x-small"
                        variant="tonal"
                        :color="getSourceTypeColor(fv.source_type)"
                      >
                        <v-icon v-if="fv.source_type" start size="10">{{ getSourceTypeIcon(fv.source_type) }}</v-icon>
                        {{ fv.text?.substring(0, 40) }}{{ fv.text?.length > 40 ? '...' : '' }}
                        <v-tooltip activator="parent" location="top">
                          {{ fv.text }} ({{ getSourceTypeLabel(fv.source_type) }})
                        </v-tooltip>
                      </v-chip>
                      <v-chip v-if="values.length > 3" size="x-small" variant="text" color="primary">
                        +{{ values.length - 3 }}
                      </v-chip>
                    </div>
                  </div>
                </template>
              </template>
            </v-card-text>
          </v-card>
        </transition-group>
      </div>

      <!-- No Results -->
      <v-card v-if="results.total === 0" class="no-results-card text-center py-12">
        <v-avatar size="80" color="grey-lighten-3" class="mb-4">
          <v-icon size="40" color="grey">mdi-database-search</v-icon>
        </v-avatar>
        <div class="text-h6 mb-2">{{ t('smartQueryView.read.noResults') }}</div>
        <div class="text-body-2 text-medium-emphasis mb-4">
          {{ t('smartQueryView.read.noResultsHint') }}
        </div>
        <v-btn variant="tonal" @click="resetAll">
          <v-icon start>mdi-refresh</v-icon>
          {{ t('smartQueryView.results.newQuery') }}
        </v-btn>
      </v-card>

      <!-- Back to Assistant Button -->
      <v-card v-if="fromAssistant" class="mt-4">
        <v-card-actions class="justify-center">
          <v-btn variant="tonal" @click="resetAll">{{ t('smartQueryView.results.newQuery') }}</v-btn>
          <v-btn
            color="primary"
            variant="elevated"
            @click="sendResultsToAssistant"
          >
            <v-icon start>mdi-arrow-left</v-icon>
            {{ t('smartQueryView.results.backToAssistant') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </template>

    <!-- History Drawer -->
    <v-navigation-drawer
      v-model="showHistory"
      location="right"
      temporary
      width="360"
    >
      <SmartQueryHistoryPanel
        @close="showHistory = false"
        @rerun="handleHistoryRerun"
      />
    </v-navigation-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { api, assistantApi } from '@/services/api'
import { useSpeechRecognition } from '@/composables/useSpeechRecognition'
import { usePlanMode } from '@/composables/usePlanMode'
import { useQueryContextStore } from '@/stores/queryContext'
import { useSmartQueryHistoryStore } from '@/stores/smartQueryHistory'
import SmartQueryHistoryPanel from '@/components/smartquery/SmartQueryHistoryPanel.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { SmartQueryResult } from '@/components/smartquery/visualizations'
import CompoundQueryResult from '@/components/smartquery/CompoundQueryResult.vue'
import PlanModeChat from '@/components/smartquery/PlanModeChat.vue'

// Types for attachments
interface AttachmentInfo {
  id: string
  filename: string
  contentType: string
  size: number
  preview?: string
}

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const queryContextStore = useQueryContextStore()
const historyStore = useSmartQueryHistoryStore()

const question = ref('')
const showHistory = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)
const results = ref<any>(null)
const previewData = ref<any>(null)
// Query mode: 'read' | 'write' | 'plan'
type QueryMode = 'read' | 'write' | 'plan'
const currentMode = ref<QueryMode>('read')
const fromAssistant = ref(false)

// Plan mode composable
const {
  conversation: planConversation,
  loading: planLoading,
  error: planError,
  generatedPrompt: planGeneratedPrompt,
  executePlanQueryStream: executePlanModeQueryStream,
  reset: resetPlanMode,
} = usePlanMode()

// Backwards compatibility computed
const writeMode = computed(() => currentMode.value === 'write')

// Attachment state
const pendingAttachments = ref<AttachmentInfo[]>([])
const isUploading = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)

// Speech Recognition
const {
  isListening,
  hasMicrophone,
  transcript,
  interimTranscript,
  error: speechError,
  toggleListening,
  clearTranscript
} = useSpeechRecognition()

// Watch transcript changes and update question
watch(transcript, (newVal) => {
  if (newVal) {
    question.value = newVal
  }
})

// Watch speech errors and show them
watch(speechError, (newVal) => {
  if (newVal) {
    error.value = newVal
  }
})

// Handle voice input toggle
function handleVoiceInput() {
  if (isListening.value) {
    toggleListening()
  } else {
    // Clear previous content when starting new voice input
    clearTranscript()
    question.value = ''
    toggleListening()
  }
}

// ============================================================================
// Attachment Functions
// ============================================================================

function triggerFileInput() {
  fileInputRef.value?.click()
}

async function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  const files = input.files
  if (!files) return

  for (const file of Array.from(files)) {
    await uploadAttachment(file)
  }

  // Clear the input so the same file can be selected again
  input.value = ''
}

async function handlePaste(event: ClipboardEvent) {
  const items = event.clipboardData?.items
  if (!items) return

  for (const item of Array.from(items)) {
    if (item.type.startsWith('image/')) {
      event.preventDefault()
      const file = item.getAsFile()
      if (file) {
        await uploadAttachment(file)
      }
    }
  }
}

async function uploadAttachment(file: File): Promise<boolean> {
  // Validate file type
  const allowedTypes = ['image/png', 'image/jpeg', 'image/gif', 'image/webp', 'application/pdf']
  if (!allowedTypes.includes(file.type)) {
    error.value = t('assistant.attachmentTypeError')
    return false
  }

  // Validate file size (10MB max)
  const maxSize = 10 * 1024 * 1024
  if (file.size > maxSize) {
    error.value = t('assistant.attachmentTooLarge')
    return false
  }

  isUploading.value = true
  error.value = null

  try {
    const response = await assistantApi.uploadAttachment(file)
    const data = response.data

    // Create preview for images
    let preview: string | undefined
    if (file.type.startsWith('image/')) {
      preview = await createImagePreview(file)
    }

    pendingAttachments.value.push({
      id: data.attachment.attachment_id,
      filename: data.attachment.filename,
      contentType: data.attachment.content_type,
      size: data.attachment.size,
      preview,
    })

    return true
  } catch (e: any) {
    error.value = e.response?.data?.detail || e.message || t('assistant.attachmentError')
    return false
  } finally {
    isUploading.value = false
  }
}

function createImagePreview(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => resolve(e.target?.result as string)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

async function removeAttachment(attachmentId: string) {
  try {
    await assistantApi.deleteAttachment(attachmentId)
  } catch (e) {
    // Ignore delete errors
  }
  pendingAttachments.value = pendingAttachments.value.filter(a => a.id !== attachmentId)
}

function getAttachmentIcon(contentType: string): string {
  if (contentType.startsWith('image/')) {
    return 'mdi-image'
  }
  if (contentType === 'application/pdf') {
    return 'mdi-file-pdf-box'
  }
  return 'mdi-file'
}

// ============================================================================
// AI Generation Progress
const currentStep = ref(1)

// Generation steps for timeline
const generationSteps = computed(() => [
  {
    value: 1,
    title: t('smartQueryView.generation.stepperTitles.entityType'),
    subtitle: t('smartQueryView.generation.stepperSubtitles.entityType')
  },
  {
    value: 2,
    title: t('smartQueryView.generation.stepperTitles.category'),
    subtitle: t('smartQueryView.generation.stepperSubtitles.category')
  },
  {
    value: 3,
    title: t('smartQueryView.generation.stepperTitles.crawlConfig'),
    subtitle: t('smartQueryView.generation.stepperSubtitles.crawlConfig')
  }
])

function getStepColor(stepValue: number): string {
  if (currentStep.value > stepValue) return 'success'
  if (currentStep.value === stepValue) return 'warning'
  return 'grey'
}

// ============================================================================
// Input computed properties
const getInputPlaceholder = computed(() => {
  if (isListening.value) return t('smartQueryView.input.placeholderListening')
  if (currentMode.value === 'plan') return t('smartQueryView.plan.placeholder')
  return currentMode.value === 'write'
    ? t('smartQueryView.input.placeholderWrite')
    : t('smartQueryView.input.placeholderRead')
})

const modeHint = computed(() => {
  const shortcut = t('smartQueryView.mode.shortcut')
  if (currentMode.value === 'plan') {
    return t('smartQueryView.mode.planHint', { shortcut })
  }
  return currentMode.value === 'write'
    ? t('smartQueryView.mode.writeHint', { shortcut })
    : t('smartQueryView.mode.readHint', { shortcut })
})

const getSubmitButtonColor = computed(() => {
  if (pendingAttachments.value.length > 0) return 'info'
  if (currentMode.value === 'plan') return 'info'
  return currentMode.value === 'write' ? 'warning' : 'primary'
})

const getSubmitButtonIcon = computed(() => {
  if (pendingAttachments.value.length > 0) return 'mdi-image-search'
  if (currentMode.value === 'plan') return 'mdi-send'
  return currentMode.value === 'write' ? 'mdi-eye' : 'mdi-send'
})

const getSubmitButtonText = computed(() => {
  if (pendingAttachments.value.length > 0) return t('smartQueryView.actions.analyzeImage')
  if (currentMode.value === 'plan') return t('smartQueryView.actions.query')
  return currentMode.value === 'write' ? t('smartQueryView.actions.preview') : t('smartQueryView.actions.query')
})

// ============================================================================
// Examples with metadata
const readExamples = ref([
  {
    question: t('smartQueryView.examples.read.futureEvents'),
    icon: 'mdi-calendar-clock',
    title: t('smartQueryView.examples.read.futureEventsTitle')
  },
  {
    question: t('smartQueryView.examples.read.mayorsOnEvents'),
    icon: 'mdi-account-tie',
    title: t('smartQueryView.examples.read.mayorsOnEventsTitle')
  },
  {
    question: t('smartQueryView.examples.read.allPainPoints'),
    icon: 'mdi-alert-circle-outline',
    title: t('smartQueryView.examples.read.allPainPointsTitle')
  },
  {
    question: t('smartQueryView.examples.read.gummersbachPainPoints'),
    icon: 'mdi-map-marker',
    title: t('smartQueryView.examples.read.gummersbachPainPointsTitle')
  },
])

const writeExamples = ref([
  {
    question: t('smartQueryView.examples.write.createPerson'),
    icon: 'mdi-account-plus',
    title: t('smartQueryView.examples.write.createPersonTitle')
  },
  {
    question: t('smartQueryView.examples.write.addPainPoint'),
    icon: 'mdi-comment-plus-outline',
    title: t('smartQueryView.examples.write.addPainPointTitle')
  },
  {
    question: t('smartQueryView.examples.write.findEvents'),
    icon: 'mdi-calendar-search',
    title: t('smartQueryView.examples.write.findEventsTitle')
  },
  {
    question: t('smartQueryView.examples.write.startCrawls'),
    icon: 'mdi-spider-web',
    title: t('smartQueryView.examples.write.startCrawlsTitle')
  },
  {
    question: t('smartQueryView.examples.write.createCategory'),
    icon: 'mdi-folder-plus',
    title: t('smartQueryView.examples.write.createCategoryTitle')
  },
  {
    question: t('smartQueryView.examples.write.analyzePysis'),
    icon: 'mdi-database-sync',
    title: t('smartQueryView.examples.write.analyzePysisTitle')
  },
])

const currentExamples = computed(() => writeMode.value ? writeExamples.value : readExamples.value)
const currentExamplesWithMeta = computed(() => currentExamples.value)

async function loadExamples() {
  try {
    const response = await api.get('/v1/analysis/smart-query/examples')
    if (response.data?.read_examples) {
      readExamples.value = response.data.read_examples
    }
    if (response.data?.write_examples) {
      writeExamples.value = response.data.write_examples
    }
  } catch (e) {
    // Use default examples
  }
}

/**
 * Execute a plan mode query using the composable with streaming
 */
async function executePlanQuery() {
  if (!question.value.trim()) return

  const currentQuestion = question.value
  question.value = '' // Clear input immediately for better UX

  // Use streaming by default for better UX
  const success = await executePlanModeQueryStream(currentQuestion)

  if (!success && planError.value) {
    error.value = planError.value
  }
}

/**
 * Adopt a generated prompt from plan mode into read/write mode
 */
function adoptPrompt(prompt: string, mode: 'read' | 'write') {
  question.value = prompt
  currentMode.value = mode
  // Reset plan conversation when adopting
  resetPlanMode()
  results.value = null
}

/**
 * Handle plan mode reset from UI
 */
function handlePlanReset() {
  resetPlanMode()
  question.value = ''
}

async function executeQuery() {
  // Plan mode has its own execution logic
  if (currentMode.value === 'plan') {
    return executePlanQuery()
  }

  // Allow query with just attachments (empty question)
  if (!question.value.trim() && pendingAttachments.value.length === 0) return

  loading.value = true
  error.value = null
  results.value = null
  previewData.value = null

  try {
    // Check if we have image attachments - use assistant API for image analysis
    if (pendingAttachments.value.length > 0) {
      const attachmentIds = pendingAttachments.value.map(a => a.id)
      const lang = (locale.value === 'de' || locale.value === 'en') ? locale.value : 'de'

      const response = await assistantApi.chat({
        message: question.value.trim() || 'Analysiere das Bild',
        context: {
          current_route: '/smart-query',
          current_entity_id: null,
          current_entity_type: null,
          current_entity_name: null,
          view_mode: 'unknown',
          available_actions: []
        },
        conversation_history: [],
        mode: 'read',
        language: lang,
        attachment_ids: attachmentIds
      })

      // Clear attachments after successful analysis
      for (const attachment of pendingAttachments.value) {
        try {
          await assistantApi.deleteAttachment(attachment.id)
        } catch (e) {
          // Ignore cleanup errors
        }
      }
      pendingAttachments.value = []

      // Format response as results
      const data = response.data
      results.value = {
        mode: 'read',
        success: data.success,
        message: data.response?.message || 'Bildanalyse abgeschlossen',
        response_type: data.response?.type || 'image_analysis',
        items: data.response?.data?.items || [],
        total: data.response?.data?.total || pendingAttachments.value.length,
        interpretation: {
          operation: 'image_analysis',
          query: question.value || 'Bildanalyse'
        },
        suggested_actions: data.suggested_actions || []
      }
    } else if (writeMode.value) {
      // Write mode - get preview first
      const response = await api.post('/v1/analysis/smart-write', {
        question: question.value,
        preview_only: true,
        confirmed: false
      })

      if (response.data.mode === 'preview' && response.data.success) {
        previewData.value = response.data
      } else {
        error.value = response.data.message || t('smartQueryView.errors.noWriteOperation')
      }
    } else {
      // Read mode - execute directly
      const response = await api.post('/v1/analysis/smart-query', {
        question: question.value,
        allow_write: false
      })
      results.value = response.data
    }
  } catch (e: any) {
    error.value = e.response?.data?.detail || e.message || t('smartQueryView.errors.queryError')
  } finally {
    loading.value = false
  }
}

async function confirmWrite() {
  if (!question.value.trim()) return

  loading.value = true
  error.value = null
  currentStep.value = 1

  // Step progression simulation for category_setup operations
  const isAiGeneration = previewData.value?.interpretation?.operation === 'create_category_setup'
  let stepInterval: ReturnType<typeof setInterval> | null = null

  if (isAiGeneration) {
    // Simulate step progression during AI generation
    stepInterval = setInterval(() => {
      if (currentStep.value < 4) {
        currentStep.value++
      }
    }, 2500) // Advance every 2.5 seconds
  }

  try {
    const response = await api.post('/v1/analysis/smart-write', {
      question: question.value,
      preview_only: false,
      confirmed: true
    })
    results.value = response.data
    previewData.value = null
    currentStep.value = 4 // Show complete
  } catch (e: any) {
    error.value = e.response?.data?.detail || e.message || t('smartQuery.createError')
  } finally {
    if (stepInterval) {
      clearInterval(stepInterval)
    }
    loading.value = false
  }
}

function cancelPreview() {
  previewData.value = null
}

function resetAll() {
  results.value = null
  previewData.value = null
  question.value = ''
}

/**
 * Handle actions from visualization component
 */
function handleVisualizationAction(action: string, params: Record<string, any>) {
  console.log('Visualization action:', action, params)

  // Handle specific actions
  switch (action) {
    case 'setup_sync':
    case 'setup_api_sync':
      // Switch to write mode with a sync setup command
      currentMode.value = 'write'
      question.value = `Richte automatische Synchronisation ein für ${params.entity_type || 'Daten'}`
      break

    case 'save_to_entities':
      // Switch to write mode to save external data
      currentMode.value = 'write'
      question.value = `Speichere die externen Daten als Entities`
      break

    case 'change_visualization':
      // Could open a dialog to change visualization type
      break

    default:
      // Other actions can be handled here
      break
  }
}

/**
 * Handle rerun from history panel
 */
function handleHistoryRerun(commandText: string, _interpretation: Record<string, any>) {
  // Set the command text and switch to write mode
  question.value = commandText
  currentMode.value = 'write'
  showHistory.value = false

  // Execute the query
  executeQuery()
}

function useExample(q: string) {
  question.value = q
  executeQuery()
}

function getTimeFilterColor(filter?: string): string {
  switch (filter) {
    case 'future_only': return 'success'
    case 'past_only': return 'grey'
    default: return 'info'
  }
}

function getEntityTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    person: 'mdi-account',
    municipality: 'mdi-city',
    event: 'mdi-calendar-star',
    organization: 'mdi-domain',
  }
  return icons[type] || 'mdi-circle'
}

function getEntityTypeColor(type: string): string {
  const colors: Record<string, string> = {
    person: 'blue',
    municipality: 'green',
    event: 'orange',
    organization: 'purple',
  }
  return colors[type] || 'grey'
}

function getSourceTypeColor(sourceType?: string): string {
  const colors: Record<string, string> = {
    PYSIS: 'info',
    DOCUMENT: 'secondary',
    MANUAL: 'success',
    SMART_QUERY: 'warning',
    AI_ASSISTANT: 'purple',
    IMPORT: 'blue-grey',
    ATTACHMENT: 'teal',
  }
  return colors[sourceType || ''] || 'secondary'
}

function getSourceTypeIcon(sourceType?: string): string {
  const icons: Record<string, string> = {
    PYSIS: 'mdi-database-sync',
    DOCUMENT: 'mdi-file-document',
    MANUAL: 'mdi-account-edit',
    SMART_QUERY: 'mdi-brain',
    AI_ASSISTANT: 'mdi-robot',
    IMPORT: 'mdi-import',
    ATTACHMENT: 'mdi-paperclip',
  }
  return icons[sourceType || ''] || 'mdi-tag'
}

function getSourceTypeLabel(sourceType?: string): string {
  const labels: Record<string, string> = {
    PYSIS: 'PySis',
    DOCUMENT: t('smartQueryView.sourceTypes.document'),
    MANUAL: t('smartQueryView.sourceTypes.manual'),
    SMART_QUERY: 'Smart Query',
    AI_ASSISTANT: t('smartQueryView.sourceTypes.aiAssistant'),
    IMPORT: t('smartQueryView.sourceTypes.import'),
    ATTACHMENT: t('smartQueryView.sourceTypes.attachment'),
  }
  return labels[sourceType || ''] || sourceType || t('smartQueryView.sourceTypes.unknown')
}

function getItemTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    entity: 'mdi-shape',
    entity_type: 'mdi-folder-multiple',
    facet_value: 'mdi-tag',
    relation: 'mdi-arrow-right-bold',
    category: 'mdi-shape-outline',
    crawl_job: 'mdi-spider-web',
  }
  return icons[type] || 'mdi-check'
}

function getItemTypeColor(type: string): string {
  const colors: Record<string, string> = {
    entity: 'primary',
    entity_type: 'purple',
    facet_value: 'secondary',
    relation: 'info',
    category: 'orange',
    crawl_job: 'success',
  }
  return colors[type] || 'grey'
}

function getInitials(name: string): string {
  return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
}

function formatAttendeeSubtitle(attendee: any): string {
  const parts = []
  if (attendee.position) parts.push(attendee.position)
  if (attendee.municipality?.name) parts.push(attendee.municipality.name)
  if (attendee.topic) parts.push(`"${attendee.topic}"`)
  return parts.join(' | ') || t('smartQueryView.read.noDetails')
}

/**
 * Send results back to the assistant and navigate back
 */
function sendResultsToAssistant() {
  if (!results.value) return

  // Build result summary
  const isWriteMode = results.value.mode === 'write'
  const summary = isWriteMode
    ? (results.value.success
      ? t('smartQueryView.assistant.elementsCreated', { count: results.value.created_items?.length || 0 })
      : results.value.message || t('smartQueryView.assistant.executionError'))
    : t('smartQueryView.assistant.resultsFound', { count: results.value.total || 0 })

  // Store results for assistant to pick up
  queryContextStore.setResults({
    summary,
    total: results.value.total || results.value.created_items?.length || 0,
    items: results.value.items?.slice(0, 5) || results.value.created_items?.slice(0, 5) || [],
    interpretation: results.value.query_interpretation || results.value.interpretation,
    success: results.value.success !== false,
    mode: isWriteMode ? 'write' : 'read',
  })

  // Navigate back (the assistant will check for results)
  router.back()
}

/**
 * Initialize from URL params and assistant context
 */
function initializeFromContext() {
  // Check for context from assistant store
  const assistantContext = queryContextStore.consumeContext()
  if (assistantContext) {
    question.value = assistantContext.query
    currentMode.value = assistantContext.mode === 'write' ? 'write' : 'read'
    fromAssistant.value = true
    return true
  }

  // Check URL params
  const urlQuery = route.query.q as string
  const urlMode = route.query.mode as string
  const urlFrom = route.query.from as string

  if (urlQuery) {
    question.value = urlQuery
    fromAssistant.value = urlFrom === 'assistant'
  }
  if (urlMode === 'write') {
    currentMode.value = 'write'
  } else if (urlMode === 'plan') {
    currentMode.value = 'plan'
  }

  return !!urlQuery
}

onMounted(() => {
  loadExamples()

  // Initialize from context/URL
  const hasContext = initializeFromContext()

  // Auto-execute if we have a query from the assistant
  if (hasContext && fromAssistant.value && question.value.trim()) {
    executeQuery()
  }
})
</script>

<style scoped>
/* ============================================================================
   Smart Query View - Modern UX Styles
   ============================================================================ */

/* Header Section */
.smart-query-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  background: linear-gradient(135deg, rgba(var(--v-theme-primary), 0.06) 0%, rgba(var(--v-theme-primary), 0.02) 100%);
  border-radius: 16px;
  border: 1px solid rgba(var(--v-theme-primary), 0.1);
}

.header-avatar {
  box-shadow: 0 4px 12px rgba(var(--v-theme-primary), 0.2);
}

.header-actions {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.mode-toggle-block {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.mode-toggle-hint {
  max-width: 320px;
  line-height: 1.35;
}

.mode-toggle {
  border-radius: 12px !important;
  overflow: hidden;
}

/* Input Card */
.input-card {
  border-radius: 16px !important;
  overflow: hidden;
  transition: box-shadow 0.3s ease, border-color 0.3s ease;
  border: 2px solid transparent;
  position: sticky;
  top: calc(var(--v-layout-top, 0px) + 12px);
  z-index: 5;
}

.input-card--active {
  border-color: rgba(var(--v-theme-primary), 0.3);
  box-shadow: 0 4px 20px rgba(var(--v-theme-primary), 0.1);
}

.input-textarea {
  padding: 16px 20px 8px;
}

.input-textarea :deep(.v-field__input) {
  font-size: 1rem;
  line-height: 1.6;
}

.interim-transcript {
  background: rgba(var(--v-theme-error), 0.05);
  margin: 0 16px 8px;
  padding: 8px 12px;
  border-radius: 8px;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: rgba(var(--v-theme-surface-variant), 0.3);
}

.submit-btn {
  padding-left: 20px;
  padding-right: 20px;
}

/* Examples Section */
.examples-section {
  animation: fadeIn 0.3s ease;
}

.examples-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(280px, 100%), 1fr));
  gap: 12px;
}

.example-card {
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 12px !important;
  display: flex;
  align-items: center;
}

.example-card:hover {
  transform: translateY(-2px);
  border-color: rgba(var(--v-theme-primary), 0.4) !important;
}

.example-card--write:hover {
  border-color: rgba(var(--v-theme-warning), 0.4) !important;
}

.example-card-content {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding-right: 40px;
  flex: 1 1 auto;
  width: 100%;
}

.example-main {
  display: flex;
  align-items: center;
  gap: 12px;
  max-width: 100%;
}

.example-avatar {
  transition: transform 0.2s ease;
}

.example-text-block {
  min-width: 0;
}

.example-title,
.example-question {
  white-space: normal;
  overflow-wrap: anywhere;
}

.example-card:hover .example-avatar {
  transform: scale(1.05);
}

.example-arrow {
  position: absolute;
  right: 16px;
  top: 50%;
  opacity: 0;
  transform: translateY(-50%) translateX(-4px);
  transition: all 0.2s ease;
}

.example-card:hover .example-arrow {
  opacity: 1;
  transform: translateY(-50%) translateX(0);
}

/* Loading Section */
.loading-card {
  border-radius: 16px !important;
}

.loading-animation {
  animation: pulse 1.5s ease-in-out infinite;
}

.generation-card {
  border-radius: 16px !important;
  border-left: 4px solid rgb(var(--v-theme-warning));
}

.generation-icon {
  animation: rotate 2s linear infinite;
}

.generation-timeline {
  margin-left: 8px;
}

/* Interpretation Bar */
.interpretation-bar {
  background: rgba(var(--v-theme-surface-variant), 0.4);
  border-radius: 12px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
}

/* Results */
.results-summary-card {
  border-radius: 16px !important;
  border-left: 4px solid rgb(var(--v-theme-success));
}

.results-grid-inner {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.result-card {
  border-radius: 12px !important;
  transition: all 0.2s ease;
  animation: slideUp 0.3s ease backwards;
  animation-delay: var(--animation-delay, 0ms);
}

.result-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(var(--v-theme-on-surface), 0.1);
}

.result-card-header {
  background: rgba(var(--v-theme-surface-variant), 0.2);
}

.attendee-item {
  transition: background-color 0.2s ease;
}

.attendee-item:hover {
  background: rgba(var(--v-theme-primary), 0.04);
}

.facet-group {
  padding: 8px;
  background: rgba(var(--v-theme-surface-variant), 0.3);
  border-radius: 8px;
}

.no-results-card {
  border-radius: 16px !important;
}

/* Voice Button Animation */
.voice-btn-listening {
  animation: pulse-voice 1.5s ease-in-out infinite;
}

/* Animations */
@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}

@keyframes pulse-voice {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.15);
    opacity: 0.85;
  }
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Transition Group Animations */
.result-list-enter-active {
  animation: slideUp 0.3s ease;
}

.result-list-leave-active {
  animation: slideUp 0.2s ease reverse;
}

.result-list-move {
  transition: transform 0.3s ease;
}

/* Compound Query Result Transitions */
.compound-result-enter-active,
.compound-result-leave-active {
  transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.compound-result-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.compound-result-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* Staggered fade-in for visualization cards */
@keyframes fadeInStagger {
  from {
    opacity: 0;
    transform: translateY(15px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.visualization-stagger-enter {
  animation: fadeInStagger 0.35s ease-out backwards;
}

/* Enhanced loading skeleton pulse */
@keyframes skeletonPulse {
  0%, 100% {
    background-position: 200% 0;
  }
  50% {
    background-position: -200% 0;
  }
}

.skeleton-loading {
  background: linear-gradient(
    90deg,
    rgba(var(--v-theme-surface-variant), 0.3) 25%,
    rgba(var(--v-theme-surface-variant), 0.6) 50%,
    rgba(var(--v-theme-surface-variant), 0.3) 75%
  );
  background-size: 400% 100%;
  animation: skeletonPulse 1.5s ease-in-out infinite;
  border-radius: 8px;
}

/* Smooth content reveal */
.content-reveal {
  animation: contentReveal 0.4s ease-out;
}

@keyframes contentReveal {
  from {
    opacity: 0;
    clip-path: inset(0 0 100% 0);
  }
  to {
    opacity: 1;
    clip-path: inset(0 0 0 0);
  }
}

/* Plan Mode Card */
.plan-mode-card {
  border-radius: 16px !important;
  border: 2px solid rgba(var(--v-theme-info), 0.2);
  min-height: clamp(300px, 50vh, 400px);
  overflow: hidden;
}

/* Mobile-specific adjustments for Plan Mode */
@media (max-width: 600px) {
  .plan-mode-card {
    min-height: 280px;
    border-radius: 12px !important;
  }
}

/* Responsive */
@media (max-width: 768px) {
  .smart-query-header {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }

  .header-content {
    flex-direction: column;
  }

  .header-actions {
    align-items: center;
  }

  .mode-toggle-block {
    align-items: center;
    text-align: center;
  }

  .mode-toggle-hint {
    max-width: 100%;
  }

  .header-avatar {
    margin-right: 0 !important;
    margin-bottom: 12px;
  }

  .examples-grid {
    grid-template-columns: 1fr;
  }

  .results-grid-inner {
    grid-template-columns: 1fr;
  }

  .interpretation-bar {
    flex-direction: column;
    align-items: flex-start !important;
  }
}
</style>
