<template>
  <div>
    <!-- Loading State -->
    <v-overlay :model-value="loading" class="align-center justify-center" persistent scrim="rgba(0,0,0,0.7)">
      <v-card class="pa-8 text-center" min-width="320" elevation="24">
        <v-progress-circular indeterminate size="80" width="6" color="primary" class="mb-4"></v-progress-circular>
        <div class="text-h6 mb-2">Lade Details</div>
      </v-card>
    </v-overlay>

    <!-- Breadcrumbs -->
    <v-breadcrumbs :items="breadcrumbs" class="px-0">
      <template v-slot:prepend>
        <v-icon icon="mdi-home" size="small"></v-icon>
      </template>
    </v-breadcrumbs>

    <!-- Entity Header -->
    <v-card v-if="entity" class="mb-6">
      <v-card-text>
        <div class="d-flex align-center">
          <v-icon :icon="entityType?.icon || 'mdi-folder'" :color="entityType?.color" size="48" class="mr-4"></v-icon>
          <div class="flex-grow-1">
            <div class="d-flex align-center mb-1">
              <h1 class="text-h4 mr-3">{{ entity.name }}</h1>
              <v-chip v-if="entity.external_id" size="small" variant="outlined">
                {{ entity.external_id }}
              </v-chip>
            </div>
            <div v-if="entity.hierarchy_path" class="text-body-2 text-grey">
              {{ entity.hierarchy_path }}
            </div>
          </div>
          <div class="d-flex ga-2">
            <v-btn variant="text" @click="notesDialog = true" title="Notizen">
              <v-icon>mdi-note-text</v-icon>
              <v-badge v-if="notes.length" :content="notes.length" color="primary" floating></v-badge>
            </v-btn>
            <v-btn variant="text" @click="exportDialog = true" title="Exportieren">
              <v-icon>mdi-export</v-icon>
            </v-btn>
            <v-btn variant="outlined" @click="editDialog = true">
              <v-icon start>mdi-pencil</v-icon>
              Bearbeiten
            </v-btn>
            <v-btn color="primary" @click="addFacetDialog = true">
              <v-icon start>mdi-plus</v-icon>
              Facet hinzufuegen
            </v-btn>
          </div>
        </div>

        <!-- Stats Row -->
        <v-row class="mt-4">
          <v-col cols="6" sm="3" md="2">
            <div class="text-center">
              <div class="text-h5">{{ entity.facet_count || 0 }}</div>
              <div class="text-caption text-grey">Facet-Werte</div>
            </div>
          </v-col>
          <v-col cols="6" sm="3" md="2">
            <div class="text-center">
              <div class="text-h5">{{ entity.relation_count || 0 }}</div>
              <div class="text-caption text-grey">Verknuepfungen</div>
            </div>
          </v-col>
          <v-col cols="6" sm="3" md="2">
            <div class="text-center">
              <div class="text-h5">{{ facetsSummary?.verified_count || 0 }}</div>
              <div class="text-caption text-grey">Verifiziert</div>
            </div>
          </v-col>
          <v-col cols="6" sm="3" md="2">
            <div class="text-center">
              <div class="text-h5">{{ dataSources.length }}</div>
              <div class="text-caption text-grey">Datenquellen</div>
            </div>
          </v-col>
          <v-col v-if="entity.latitude && entity.longitude" cols="12" sm="6" md="4">
            <div class="text-center">
              <v-chip size="small" color="info">
                <v-icon start size="small">mdi-map-marker</v-icon>
                {{ entity.latitude.toFixed(4) }}, {{ entity.longitude.toFixed(4) }}
              </v-chip>
            </div>
          </v-col>
        </v-row>

        <!-- Core Attributes -->
        <v-row v-if="hasAttributes" class="mt-2">
          <v-col v-for="(value, key) in entity.core_attributes" :key="key" cols="auto">
            <v-chip size="small" variant="tonal">
              <strong class="mr-1">{{ formatAttributeKey(key) }}:</strong>
              {{ formatAttributeValue(value) }}
            </v-chip>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Tabs for Content -->
    <v-tabs v-model="activeTab" color="primary" class="mb-4">
      <v-tab value="facets">
        <v-icon start>mdi-tag-multiple</v-icon>
        Eigenschaften
        <v-chip v-if="facetsSummary" size="x-small" class="ml-2">{{ facetsSummary.total_facet_values }}</v-chip>
      </v-tab>
      <v-tab value="relations">
        <v-icon start>mdi-link</v-icon>
        Verknuepfungen
        <v-chip v-if="relations.length" size="x-small" class="ml-2">{{ relations.length }}</v-chip>
      </v-tab>
      <v-tab value="sources">
        <v-icon start>mdi-web</v-icon>
        Datenquellen
        <v-chip v-if="dataSources.length" size="x-small" class="ml-2">{{ dataSources.length }}</v-chip>
      </v-tab>
      <v-tab value="documents">
        <v-icon start>mdi-file-document-multiple</v-icon>
        Dokumente
      </v-tab>
      <v-tab v-if="entityType?.slug === 'municipality'" value="pysis">
        <v-icon start>mdi-database-sync</v-icon>
        PySis
      </v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <!-- Facets Tab -->
      <v-window-item value="facets">
        <!-- Search Bar for Facets -->
        <v-card v-if="facetsSummary?.facets_by_type?.length" class="mb-4" variant="outlined">
          <v-card-text class="py-2">
            <v-text-field
              v-model="facetSearchQuery"
              prepend-inner-icon="mdi-magnify"
              label="In Eigenschaften suchen..."
              clearable
              hide-details
              density="compact"
              variant="plain"
            ></v-text-field>
          </v-card-text>
        </v-card>

        <v-row>
          <v-col
            v-for="facetGroup in facetsSummary?.facets_by_type || []"
            :key="facetGroup.facet_type_id"
            cols="12"
          >
            <v-card>
              <v-card-title class="d-flex align-center">
                <v-icon :icon="facetGroup.facet_type_icon" :color="facetGroup.facet_type_color" class="mr-2"></v-icon>
                {{ facetGroup.facet_type_name }}
                <v-chip size="small" class="ml-2">{{ facetGroup.value_count }}</v-chip>
                <v-chip v-if="facetGroup.verified_count" size="x-small" color="success" class="ml-1">
                  {{ facetGroup.verified_count }} verifiziert
                </v-chip>
                <v-spacer></v-spacer>
                <v-btn size="small" variant="text" @click="toggleFacetExpand(facetGroup.facet_type_slug)">
                  <v-icon>{{ expandedFacets.includes(facetGroup.facet_type_slug) ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
                </v-btn>
              </v-card-title>

              <v-expand-transition>
                <v-card-text v-show="expandedFacets.includes(facetGroup.facet_type_slug)">
                  <!-- Facet Values List -->
                  <div v-if="getDisplayedFacets(facetGroup).length" class="mb-4">
                    <div
                      v-for="(sample, idx) in getDisplayedFacets(facetGroup)"
                      :key="sample.id || idx"
                      class="mb-3 pa-3 rounded facet-item"
                      :class="{ 'selected': selectedFacetIds.includes(sample.id) }"
                      :style="{ backgroundColor: 'rgba(var(--v-theme-surface-variant), 0.3)' }"
                    >
                      <!-- Checkbox for bulk selection -->
                      <div class="d-flex align-start">
                        <v-checkbox
                          v-if="bulkMode"
                          :model-value="selectedFacetIds.includes(sample.id)"
                          @update:model-value="toggleFacetSelection(sample.id)"
                          hide-details
                          density="compact"
                          class="mr-2 mt-0"
                        ></v-checkbox>
                        <div class="flex-grow-1">
                      <!-- Structured Value Display for Pain Points -->
                      <template v-if="facetGroup.facet_type_slug === 'pain_point'">
                        <div class="d-flex align-start ga-2 mb-2">
                          <v-icon size="small" color="error">mdi-alert-circle</v-icon>
                          <div class="flex-grow-1">
                            <div class="text-body-1">{{ getStructuredDescription(sample) }}</div>
                            <div class="d-flex flex-wrap ga-2 mt-2">
                              <v-chip v-if="getStructuredType(sample)" size="small" variant="outlined" color="error">
                                {{ getStructuredType(sample) }}
                              </v-chip>
                              <v-chip
                                v-if="getStructuredSeverity(sample)"
                                size="small"
                                :color="getSeverityColor(getStructuredSeverity(sample))"
                              >
                                {{ getStructuredSeverity(sample) }}
                              </v-chip>
                            </div>
                            <div v-if="getStructuredQuote(sample)" class="mt-2 pa-2 rounded bg-grey-lighten-4">
                              <v-icon size="small" class="mr-1">mdi-format-quote-open</v-icon>
                              <span class="text-body-2 font-italic">{{ getStructuredQuote(sample) }}</span>
                            </div>
                            <div v-if="sample.source_url" class="mt-2">
                              <v-chip size="x-small" variant="outlined" :href="sample.source_url" target="_blank" tag="a">
                                <v-icon start size="x-small">mdi-link</v-icon>
                                Quelle
                              </v-chip>
                            </div>
                          </div>
                        </div>
                      </template>

                      <!-- Structured Value Display for Positive Signals -->
                      <template v-else-if="facetGroup.facet_type_slug === 'positive_signal'">
                        <div class="d-flex align-start ga-2 mb-2">
                          <v-icon size="small" color="success">mdi-lightbulb-on</v-icon>
                          <div class="flex-grow-1">
                            <div class="text-body-1">{{ getStructuredDescription(sample) }}</div>
                            <div class="d-flex flex-wrap ga-2 mt-2">
                              <v-chip v-if="getStructuredType(sample)" size="small" variant="outlined" color="success">
                                {{ getStructuredType(sample) }}
                              </v-chip>
                            </div>
                            <div v-if="getStructuredQuote(sample)" class="mt-2 pa-2 rounded bg-grey-lighten-4">
                              <v-icon size="small" class="mr-1">mdi-format-quote-open</v-icon>
                              <span class="text-body-2 font-italic">{{ getStructuredQuote(sample) }}</span>
                            </div>
                            <div v-if="sample.source_url" class="mt-2">
                              <v-chip size="x-small" variant="outlined" :href="sample.source_url" target="_blank" tag="a">
                                <v-icon start size="x-small">mdi-link</v-icon>
                                Quelle
                              </v-chip>
                            </div>
                          </div>
                        </div>
                      </template>

                      <!-- Structured Value Display for Contacts -->
                      <template v-else-if="facetGroup.facet_type_slug === 'contact'">
                        <div class="d-flex align-start ga-2 mb-2">
                          <v-icon size="small" color="primary">mdi-account-tie</v-icon>
                          <div class="flex-grow-1">
                            <div class="text-body-1 font-weight-medium">{{ getContactName(sample) }}</div>
                            <div v-if="getContactRole(sample)" class="text-body-2 text-grey">{{ getContactRole(sample) }}</div>
                            <div class="d-flex flex-wrap ga-2 mt-2">
                              <v-chip v-if="getContactEmail(sample)" size="small" variant="outlined" @click.stop="copyToClipboard(getContactEmail(sample))">
                                <v-icon start size="small">mdi-email</v-icon>
                                {{ getContactEmail(sample) }}
                              </v-chip>
                              <v-chip v-if="getContactPhone(sample)" size="small" variant="outlined">
                                <v-icon start size="small">mdi-phone</v-icon>
                                {{ getContactPhone(sample) }}
                              </v-chip>
                              <v-chip
                                v-if="getContactSentiment(sample)"
                                size="small"
                                :color="getSentimentColor(getContactSentiment(sample))"
                              >
                                {{ getContactSentiment(sample) }}
                              </v-chip>
                            </div>
                            <div v-if="getContactStatement(sample)" class="mt-2 pa-2 rounded bg-grey-lighten-4">
                              <v-icon size="small" class="mr-1">mdi-format-quote-open</v-icon>
                              <span class="text-body-2 font-italic">{{ getContactStatement(sample) }}</span>
                            </div>
                            <div v-if="sample.source_url" class="mt-2">
                              <v-chip size="x-small" variant="outlined" :href="sample.source_url" target="_blank" tag="a">
                                <v-icon start size="x-small">mdi-link</v-icon>
                                Quelle
                              </v-chip>
                            </div>
                          </div>
                        </div>
                      </template>

                      <!-- Default/Text Display -->
                      <template v-else>
                        <div class="text-body-1">{{ formatFacetValue(sample) }}</div>
                        <div v-if="sample.source_url" class="mt-2">
                          <v-chip size="x-small" variant="outlined" :href="sample.source_url" target="_blank" tag="a">
                            <v-icon start size="x-small">mdi-link</v-icon>
                            Quelle
                          </v-chip>
                        </div>
                      </template>

                      <!-- Confidence Score (shown for all types) -->
                      <div v-if="sample.confidence_score" class="d-flex align-center mt-2">
                        <v-progress-linear
                          :model-value="sample.confidence_score * 100"
                          :color="getConfidenceColor(sample.confidence_score)"
                          height="4"
                          class="mr-2"
                          style="max-width: 100px;"
                        ></v-progress-linear>
                        <span class="text-caption text-grey">{{ Math.round(sample.confidence_score * 100) }}%</span>
                        <v-chip v-if="sample.human_verified" size="x-small" color="success" class="ml-2">
                          <v-icon size="x-small">mdi-check</v-icon>
                        </v-chip>
                        <v-spacer></v-spacer>
                        <!-- Inline verify button -->
                        <v-btn
                          v-if="!sample.human_verified && sample.id"
                          size="x-small"
                          color="success"
                          variant="text"
                          @click.stop="verifyFacet(sample.id)"
                        >
                          <v-icon size="small">mdi-check</v-icon>
                        </v-btn>
                      </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Load More / Show Less Buttons -->
                  <div class="d-flex align-center ga-2 flex-wrap">
                    <v-btn
                      v-if="canLoadMore(facetGroup)"
                      variant="tonal"
                      size="small"
                      :loading="loadingMoreFacets[facetGroup.facet_type_slug]"
                      @click="loadMoreFacets(facetGroup)"
                    >
                      <v-icon start>mdi-plus</v-icon>
                      Mehr laden ({{ getRemainingCount(facetGroup) }} weitere)
                    </v-btn>
                    <v-btn
                      v-if="isExpanded(facetGroup)"
                      variant="text"
                      size="small"
                      @click="collapseFacets(facetGroup)"
                    >
                      <v-icon start>mdi-chevron-up</v-icon>
                      Weniger anzeigen
                    </v-btn>
                    <v-spacer></v-spacer>
                    <!-- Bulk Mode Toggle -->
                    <v-btn
                      v-if="getDisplayedFacets(facetGroup).length > 1"
                      variant="text"
                      size="small"
                      @click="bulkMode = !bulkMode"
                    >
                      <v-icon start>{{ bulkMode ? 'mdi-close' : 'mdi-checkbox-multiple-marked' }}</v-icon>
                      {{ bulkMode ? 'Abbrechen' : 'Mehrfachauswahl' }}
                    </v-btn>
                  </div>

                  <!-- Bulk Actions Bar -->
                  <v-slide-y-transition>
                    <div v-if="bulkMode && selectedFacetIds.length > 0" class="mt-3 pa-3 rounded bg-primary-lighten-5">
                      <div class="d-flex align-center ga-2">
                        <span class="text-body-2">{{ selectedFacetIds.length }} ausgewaehlt</span>
                        <v-spacer></v-spacer>
                        <v-btn
                          size="small"
                          color="success"
                          variant="tonal"
                          @click="bulkVerify"
                          :loading="bulkActionLoading"
                        >
                          <v-icon start>mdi-check-all</v-icon>
                          Alle verifizieren
                        </v-btn>
                        <v-btn
                          size="small"
                          color="error"
                          variant="tonal"
                          @click="bulkDeleteConfirm = true"
                          :loading="bulkActionLoading"
                        >
                          <v-icon start>mdi-delete</v-icon>
                          Loeschen
                        </v-btn>
                      </div>
                    </div>
                  </v-slide-y-transition>
                </v-card-text>
              </v-expand-transition>
            </v-card>
          </v-col>
        </v-row>

        <!-- Empty State for Facets -->
        <v-card v-if="!facetsSummary?.facets_by_type?.length" class="mt-4 text-center pa-8" variant="outlined">
          <v-icon size="80" color="grey-lighten-1" class="mb-4">mdi-tag-off-outline</v-icon>
          <h3 class="text-h6 mb-2">Noch keine Eigenschaften vorhanden</h3>
          <p class="text-body-2 text-grey mb-4">
            Eigenschaften wie Pain Points, Positive Signale oder Kontakte werden automatisch durch Crawling extrahiert
            oder koennen manuell hinzugefuegt werden.
          </p>
          <div class="d-flex justify-center ga-2">
            <v-btn color="primary" @click="addFacetDialog = true">
              <v-icon start>mdi-plus</v-icon>
              Manuell hinzufuegen
            </v-btn>
            <v-btn variant="outlined" @click="activeTab = 'sources'">
              <v-icon start>mdi-web</v-icon>
              Datenquellen pruefen
            </v-btn>
          </div>
        </v-card>

        <!-- No Search Results -->
        <v-card v-else-if="facetSearchQuery && !hasSearchResults" class="mt-4 text-center pa-6" variant="outlined">
          <v-icon size="60" color="grey-lighten-1" class="mb-3">mdi-magnify-close</v-icon>
          <h3 class="text-h6 mb-2">Keine Treffer fuer "{{ facetSearchQuery }}"</h3>
          <p class="text-body-2 text-grey mb-3">
            Versuche einen anderen Suchbegriff oder loesche die Suche.
          </p>
          <v-btn variant="text" @click="facetSearchQuery = ''">
            <v-icon start>mdi-close</v-icon>
            Suche loeschen
          </v-btn>
        </v-card>
      </v-window-item>

      <!-- Relations Tab -->
      <v-window-item value="relations">
        <v-card>
          <v-card-text>
            <!-- Loading State -->
            <div v-if="loadingRelations" class="text-center pa-8">
              <v-progress-circular indeterminate color="primary" size="48"></v-progress-circular>
              <p class="mt-4 text-grey">Lade Verknuepfungen...</p>
            </div>
            <div v-else-if="relations.length">
              <v-list>
                <v-list-item
                  v-for="rel in relations"
                  :key="rel.id"
                  @click="navigateToRelatedEntity(rel)"
                  class="cursor-pointer"
                >
                  <template v-slot:prepend>
                    <v-icon :color="rel.relation_type_color || 'primary'">mdi-link-variant</v-icon>
                  </template>
                  <v-list-item-title>
                    <span v-if="rel.source_entity_id === entity?.id">
                      {{ rel.relation_type_name }}: <strong>{{ rel.target_entity_name }}</strong>
                    </span>
                    <span v-else>
                      {{ rel.relation_type_name_inverse || rel.relation_type_name }}: <strong>{{ rel.source_entity_name }}</strong>
                    </span>
                  </v-list-item-title>
                  <v-list-item-subtitle v-if="rel.attributes && Object.keys(rel.attributes).length">
                    <v-chip v-for="(val, key) in rel.attributes" :key="key" size="x-small" class="mr-1">
                      {{ key }}: {{ val }}
                    </v-chip>
                  </v-list-item-subtitle>
                  <template v-slot:append>
                    <div class="d-flex align-center ga-2">
                      <v-chip v-if="rel.human_verified" size="x-small" color="success">
                        <v-icon size="x-small">mdi-check</v-icon>
                      </v-chip>
                      <v-icon>mdi-chevron-right</v-icon>
                    </div>
                  </template>
                </v-list-item>
              </v-list>
            </div>
            <!-- Empty State for Relations -->
            <div v-else class="text-center pa-8">
              <v-icon size="80" color="grey-lighten-1" class="mb-4">mdi-link-off</v-icon>
              <h3 class="text-h6 mb-2">Keine Verknuepfungen vorhanden</h3>
              <p class="text-body-2 text-grey mb-4">
                Verknuepfungen zeigen Beziehungen zu anderen Entities wie Personen, Organisationen oder Veranstaltungen.
              </p>
              <v-btn color="primary" @click="addRelationDialog = true">
                <v-icon start>mdi-link-plus</v-icon>
                Verknuepfung hinzufuegen
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- Data Sources Tab -->
      <v-window-item value="sources">
        <v-card>
          <v-card-text>
            <div v-if="loadingDataSources" class="text-center pa-4">
              <v-progress-circular indeterminate></v-progress-circular>
            </div>
            <div v-else-if="dataSources.length">
              <v-list>
                <v-list-item
                  v-for="source in dataSources"
                  :key="source.id"
                >
                  <template v-slot:prepend>
                    <v-icon :color="getSourceStatusColor(source.status)">
                      {{ getSourceStatusIcon(source.status) }}
                    </v-icon>
                  </template>
                  <v-list-item-title>
                    {{ source.name }}
                    <v-chip v-if="source.hasRunningJob" size="x-small" color="info" class="ml-2">
                      Laeuft
                    </v-chip>
                  </v-list-item-title>
                  <v-list-item-subtitle>
                    <a :href="source.base_url" target="_blank" class="text-decoration-none">
                      {{ source.base_url }}
                    </a>
                  </v-list-item-subtitle>
                  <template v-slot:append>
                    <v-btn
                      v-if="!source.hasRunningJob"
                      size="small"
                      color="primary"
                      variant="tonal"
                      @click="startCrawl(source)"
                      :loading="startingCrawl === source.id"
                    >
                      <v-icon start>mdi-play</v-icon>
                      Crawlen
                    </v-btn>
                  </template>
                </v-list-item>
              </v-list>
            </div>
            <!-- Empty State for Data Sources -->
            <div v-else class="text-center pa-8">
              <v-icon size="80" color="grey-lighten-1" class="mb-4">mdi-web-off</v-icon>
              <h3 class="text-h6 mb-2">Keine Datenquellen verknuepft</h3>
              <p class="text-body-2 text-grey mb-4">
                Datenquellen sind Webseiten oder APIs, die automatisch gecrawlt werden,
                um relevante Informationen zu extrahieren.
              </p>
              <v-btn color="primary" @click="goToSources">
                <v-icon start>mdi-plus</v-icon>
                Datenquelle hinzufuegen
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- Documents Tab -->
      <v-window-item value="documents">
        <v-card>
          <v-card-text>
            <div v-if="loadingDocuments" class="text-center pa-4">
              <v-progress-circular indeterminate></v-progress-circular>
            </div>
            <v-data-table
              v-else
              :headers="documentHeaders"
              :items="documents"
              :items-per-page="10"
            >
              <template v-slot:item.title="{ item }">
                <a :href="item.url" target="_blank" class="text-decoration-none">
                  {{ item.title || 'Dokument' }}
                </a>
              </template>
              <template v-slot:item.created_at="{ item }">
                {{ formatDate(item.created_at) }}
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- PySis Tab (only for municipalities) -->
      <v-window-item v-if="entityType?.slug === 'municipality'" value="pysis" eager>
        <PySisTab
          v-if="entity"
          :municipality="entity.name"
        />
      </v-window-item>
    </v-window>

    <!-- Add Facet Dialog -->
    <v-dialog v-model="addFacetDialog" max-width="600">
      <v-card>
        <v-card-title>Facet hinzufuegen</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveFacetValue">
            <v-select
              v-model="newFacet.facet_type_id"
              :items="store.activeFacetTypes"
              item-title="name"
              item-value="id"
              label="Facet-Typ *"
              :rules="[v => !!v || 'Facet-Typ ist erforderlich']"
            ></v-select>

            <v-textarea
              v-model="newFacet.text_representation"
              label="Wert / Beschreibung *"
              :rules="[v => !!v || 'Wert ist erforderlich']"
              rows="3"
            ></v-textarea>

            <v-text-field
              v-model="newFacet.source_url"
              label="Quell-URL"
              placeholder="https://..."
            ></v-text-field>

            <v-slider
              v-model="newFacet.confidence_score"
              label="Konfidenz"
              :min="0"
              :max="1"
              :step="0.1"
              thumb-label
              :color="getConfidenceColor(newFacet.confidence_score)"
            ></v-slider>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="addFacetDialog = false">Abbrechen</v-btn>
          <v-btn
            color="primary"
            :loading="savingFacet"
            @click="saveFacetValue"
          >
            Speichern
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Facet Details Dialog -->
    <v-dialog v-model="facetDetailsDialog" max-width="800" scrollable>
      <v-card v-if="selectedFacetGroup">
        <v-card-title class="d-flex align-center">
          <v-icon :icon="selectedFacetGroup.facet_type_icon" :color="selectedFacetGroup.facet_type_color" class="mr-2"></v-icon>
          {{ selectedFacetGroup.facet_type_name }}
          <v-spacer></v-spacer>
          <v-btn icon="mdi-close" variant="text" @click="facetDetailsDialog = false"></v-btn>
        </v-card-title>
        <v-card-text>
          <div class="d-flex flex-column ga-3">
            <v-card
              v-for="fv in facetDetails"
              :key="fv.id"
              variant="outlined"
              class="pa-3"
            >
              <!-- Pain Point Display -->
              <template v-if="selectedFacetGroup.facet_type_slug === 'pain_point'">
                <div class="d-flex align-start ga-2">
                  <v-icon color="error">mdi-alert-circle</v-icon>
                  <div class="flex-grow-1">
                    <div class="text-body-1">{{ getStructuredDescription(fv) }}</div>
                    <div class="d-flex flex-wrap ga-2 mt-2">
                      <v-chip v-if="getStructuredType(fv)" size="small" variant="outlined" color="error">
                        {{ getStructuredType(fv) }}
                      </v-chip>
                      <v-chip
                        v-if="getStructuredSeverity(fv)"
                        size="small"
                        :color="getSeverityColor(getStructuredSeverity(fv))"
                      >
                        <v-icon start size="x-small">{{ getSeverityIcon(getStructuredSeverity(fv)) }}</v-icon>
                        {{ getStructuredSeverity(fv) }}
                      </v-chip>
                    </div>
                    <div v-if="getStructuredQuote(fv)" class="mt-2 pa-2 rounded bg-grey-lighten-4">
                      <v-icon size="small" class="mr-1">mdi-format-quote-open</v-icon>
                      <span class="text-body-2 font-italic">{{ getStructuredQuote(fv) }}</span>
                    </div>
                  </div>
                </div>
              </template>

              <!-- Positive Signal Display -->
              <template v-else-if="selectedFacetGroup.facet_type_slug === 'positive_signal'">
                <div class="d-flex align-start ga-2">
                  <v-icon color="success">mdi-lightbulb-on</v-icon>
                  <div class="flex-grow-1">
                    <div class="text-body-1">{{ getStructuredDescription(fv) }}</div>
                    <div class="d-flex flex-wrap ga-2 mt-2">
                      <v-chip v-if="getStructuredType(fv)" size="small" variant="outlined" color="success">
                        {{ getStructuredType(fv) }}
                      </v-chip>
                    </div>
                    <div v-if="getStructuredQuote(fv)" class="mt-2 pa-2 rounded bg-grey-lighten-4">
                      <v-icon size="small" class="mr-1">mdi-format-quote-open</v-icon>
                      <span class="text-body-2 font-italic">{{ getStructuredQuote(fv) }}</span>
                    </div>
                  </div>
                </div>
              </template>

              <!-- Contact Display -->
              <template v-else-if="selectedFacetGroup.facet_type_slug === 'contact'">
                <div class="d-flex align-start ga-2">
                  <v-avatar color="primary" size="40">
                    <v-icon color="white">mdi-account</v-icon>
                  </v-avatar>
                  <div class="flex-grow-1">
                    <div class="text-body-1 font-weight-medium">{{ getContactName(fv) }}</div>
                    <div v-if="getContactRole(fv)" class="text-body-2 text-grey">{{ getContactRole(fv) }}</div>
                    <div class="d-flex flex-wrap ga-2 mt-2">
                      <v-chip v-if="getContactEmail(fv)" size="small" variant="outlined" @click.stop="copyToClipboard(getContactEmail(fv))">
                        <v-icon start size="small">mdi-email</v-icon>
                        {{ getContactEmail(fv) }}
                      </v-chip>
                      <v-chip v-if="getContactPhone(fv)" size="small" variant="outlined">
                        <v-icon start size="small">mdi-phone</v-icon>
                        {{ getContactPhone(fv) }}
                      </v-chip>
                      <v-chip
                        v-if="getContactSentiment(fv)"
                        size="small"
                        :color="getSentimentColor(getContactSentiment(fv))"
                      >
                        {{ getContactSentiment(fv) }}
                      </v-chip>
                    </div>
                    <div v-if="getContactStatement(fv)" class="mt-2 pa-2 rounded bg-grey-lighten-4">
                      <v-icon size="small" class="mr-1">mdi-format-quote-open</v-icon>
                      <span class="text-body-2 font-italic">{{ getContactStatement(fv) }}</span>
                    </div>
                  </div>
                </div>
              </template>

              <!-- Default Display -->
              <template v-else>
                <div class="text-body-1">{{ fv.text_representation || formatFacetValue(fv) }}</div>
              </template>

              <!-- Meta Info (shown for all) -->
              <v-divider class="my-3"></v-divider>
              <div class="d-flex align-center ga-2 flex-wrap">
                <v-progress-linear
                  :model-value="(fv.confidence_score || 0) * 100"
                  :color="getConfidenceColor(fv.confidence_score)"
                  height="4"
                  style="max-width: 80px;"
                ></v-progress-linear>
                <span class="text-caption">{{ Math.round((fv.confidence_score || 0) * 100) }}%</span>
                <v-chip v-if="fv.human_verified" size="x-small" color="success">
                  <v-icon start size="x-small">mdi-check</v-icon>
                  Verifiziert
                </v-chip>
                <v-chip v-if="fv.source_url" size="x-small" variant="outlined" :href="fv.source_url" target="_blank" tag="a">
                  <v-icon start size="x-small">mdi-link</v-icon>
                  Quelle
                </v-chip>
                <v-spacer></v-spacer>
                <v-btn
                  v-if="!fv.human_verified"
                  size="small"
                  color="success"
                  variant="tonal"
                  @click="verifyFacet(fv.id)"
                >
                  <v-icon start size="small">mdi-check</v-icon>
                  Verifizieren
                </v-btn>
              </div>

              <!-- Timestamps / History -->
              <div v-if="fv.created_at || fv.updated_at" class="mt-2 d-flex align-center ga-3 text-caption text-grey">
                <span v-if="fv.created_at">
                  <v-icon size="x-small" class="mr-1">mdi-clock-plus-outline</v-icon>
                  Erstellt: {{ formatDate(fv.created_at) }}
                </span>
                <span v-if="fv.updated_at && fv.updated_at !== fv.created_at">
                  <v-icon size="x-small" class="mr-1">mdi-clock-edit-outline</v-icon>
                  Geaendert: {{ formatDate(fv.updated_at) }}
                </span>
              </div>
            </v-card>
          </div>
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- Edit Entity Dialog -->
    <v-dialog v-model="editDialog" max-width="500">
      <v-card>
        <v-card-title>{{ entityType?.name }} bearbeiten</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveEntity">
            <v-text-field
              v-model="editForm.name"
              label="Name *"
              :rules="[v => !!v || 'Name ist erforderlich']"
            ></v-text-field>
            <v-text-field
              v-model="editForm.external_id"
              label="Externe ID"
            ></v-text-field>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="editDialog = false">Abbrechen</v-btn>
          <v-btn color="primary" :loading="savingEntity" @click="saveEntity">
            Speichern
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Bulk Delete Confirmation Dialog -->
    <v-dialog v-model="bulkDeleteConfirm" max-width="400">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon color="error" class="mr-2">mdi-alert</v-icon>
          Facets loeschen?
        </v-card-title>
        <v-card-text>
          <p>Moechtest du wirklich <strong>{{ selectedFacetIds.length }}</strong> Facet-Werte loeschen?</p>
          <p class="text-caption text-grey mt-2">Diese Aktion kann nicht rueckgaengig gemacht werden.</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="bulkDeleteConfirm = false">Abbrechen</v-btn>
          <v-btn color="error" :loading="bulkActionLoading" @click="bulkDelete">
            <v-icon start>mdi-delete</v-icon>
            Loeschen
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Export Dialog -->
    <v-dialog v-model="exportDialog" max-width="500">
      <v-card>
        <v-card-title>
          <v-icon start>mdi-export</v-icon>
          Daten exportieren
        </v-card-title>
        <v-card-text>
          <p class="mb-4">Waehle das Exportformat und die zu exportierenden Daten:</p>

          <v-select
            v-model="exportFormat"
            :items="exportFormats"
            item-title="label"
            item-value="value"
            label="Format"
            variant="outlined"
            class="mb-4"
          ></v-select>

          <v-checkbox
            v-model="exportOptions.facets"
            label="Eigenschaften (Pain Points, Signale, Kontakte)"
            hide-details
          ></v-checkbox>
          <v-checkbox
            v-model="exportOptions.relations"
            label="Verknuepfungen"
            hide-details
          ></v-checkbox>
          <v-checkbox
            v-model="exportOptions.dataSources"
            label="Datenquellen"
            hide-details
          ></v-checkbox>
          <v-checkbox
            v-model="exportOptions.notes"
            label="Notizen"
            hide-details
          ></v-checkbox>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="exportDialog = false">Abbrechen</v-btn>
          <v-btn color="primary" :loading="exporting" @click="exportData">
            <v-icon start>mdi-download</v-icon>
            Exportieren
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Notes Dialog -->
    <v-dialog v-model="notesDialog" max-width="700" scrollable>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start>mdi-note-text</v-icon>
          Notizen
          <v-spacer></v-spacer>
          <v-btn icon="mdi-close" variant="text" @click="notesDialog = false"></v-btn>
        </v-card-title>
        <v-card-text>
          <!-- Add Note Form -->
          <v-textarea
            v-model="newNote"
            label="Neue Notiz hinzufuegen..."
            rows="3"
            variant="outlined"
            class="mb-4"
          ></v-textarea>
          <div class="d-flex justify-end mb-4">
            <v-btn
              color="primary"
              :disabled="!newNote.trim()"
              :loading="savingNote"
              @click="saveNote"
            >
              <v-icon start>mdi-plus</v-icon>
              Notiz speichern
            </v-btn>
          </div>

          <v-divider class="mb-4"></v-divider>

          <!-- Notes List -->
          <div v-if="notes.length">
            <v-card
              v-for="note in notes"
              :key="note.id"
              variant="outlined"
              class="mb-3 pa-3"
            >
              <div class="d-flex align-start">
                <v-avatar size="32" color="primary" class="mr-3">
                  <v-icon size="small" color="white">mdi-account</v-icon>
                </v-avatar>
                <div class="flex-grow-1">
                  <div class="d-flex align-center mb-1">
                    <span class="text-body-2 font-weight-medium">{{ note.author || 'System' }}</span>
                    <span class="text-caption text-grey ml-2">{{ formatDate(note.created_at) }}</span>
                    <v-spacer></v-spacer>
                    <v-btn
                      icon="mdi-delete"
                      size="x-small"
                      variant="text"
                      color="error"
                      @click="deleteNote(note.id)"
                    ></v-btn>
                  </div>
                  <p class="text-body-2 mb-0" style="white-space: pre-wrap;">{{ note.content }}</p>
                </div>
              </div>
            </v-card>
          </div>
          <div v-else class="text-center pa-4 text-grey">
            <v-icon size="48" color="grey-lighten-2" class="mb-2">mdi-note-off-outline</v-icon>
            <p>Noch keine Notizen vorhanden</p>
          </div>
        </v-card-text>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEntityStore, type FacetValue, type Entity, type EntityType } from '@/stores/entity'
import { adminApi, facetApi, relationApi } from '@/services/api'
import { format } from 'date-fns'
import { de } from 'date-fns/locale'
import { useSnackbar } from '@/composables/useSnackbar'
import PySisTab from '@/components/PySisTab.vue'

// ============================================================================
// Local Types
// ============================================================================

interface FacetGroup {
  facet_type_id: string
  facet_type_slug: string
  facet_type_name: string
  facet_type_icon: string
  facet_type_color: string
  value_count: number
  verified_count: number
  sample_values: FacetValue[]
}

interface FacetsSummary {
  total_facet_values: number
  verified_count: number
  facets_by_type: FacetGroup[]
}

interface Relation {
  id: string
  source_entity_id: string
  source_entity_name: string
  source_entity_slug: string
  source_entity_type_slug: string
  target_entity_id: string
  target_entity_name: string
  target_entity_slug: string
  target_entity_type_slug: string
  relation_type_name: string
  relation_type_name_inverse: string | null
  relation_type_color: string | null
  attributes: Record<string, any>
  human_verified: boolean
}

interface DataSource {
  id: string
  name: string
  base_url: string
  status: string
  hasRunningJob?: boolean
}

interface Note {
  id: string
  content: string
  author: string
  created_at: string
}

// ============================================================================
// Entity Cache (for performance)
// ============================================================================
const entityCache = new Map<string, { data: any; timestamp: number }>()
const CACHE_TTL = 5 * 60 * 1000 // 5 minutes

function getCachedData(key: string): any | null {
  const cached = entityCache.get(key)
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.data
  }
  return null
}

function setCachedData(key: string, data: any) {
  entityCache.set(key, { data, timestamp: Date.now() })
}

const { showSuccess, showError } = useSnackbar()
const route = useRoute()
const router = useRouter()
const store = useEntityStore()

// Route params
const typeSlug = computed(() => route.params.typeSlug as string)
const entitySlug = computed(() => route.params.entitySlug as string)

// State
const loading = ref(true)
const activeTab = ref('facets')
const expandedFacets = ref<string[]>([])

// Entity data
const entity = computed<Entity | null>(() => store.selectedEntity)
const entityType = computed<EntityType | null>(() => store.selectedEntityType)
const facetsSummary = ref<FacetsSummary | null>(null)
const relations = ref<Relation[]>([])
const dataSources = ref<DataSource[]>([])
const documents = ref<any[]>([])

// Loading states
const loadingDataSources = ref(false)
const loadingDocuments = ref(false)
const startingCrawl = ref<string | null>(null)

// Dialogs
const addFacetDialog = ref(false)
const addRelationDialog = ref(false)
const facetDetailsDialog = ref(false)
const editDialog = ref(false)
const selectedFacetGroup = ref<any>(null)
const facetDetails = ref<any[]>([])

// Forms
const newFacet = ref({
  facet_type_id: '',
  text_representation: '',
  source_url: '',
  confidence_score: 0.8,
})

const editForm = ref({
  name: '',
  external_id: '',
})

const savingFacet = ref(false)
const savingEntity = ref(false)

// Facet Search & Expanded State
const facetSearchQuery = ref('')
const expandedFacetValues = ref<Record<string, any[]>>({}) // Stores loaded facets per type
const loadingMoreFacets = ref<Record<string, boolean>>({})

// Bulk Mode
const bulkMode = ref(false)
const selectedFacetIds = ref<string[]>([])
const bulkDeleteConfirm = ref(false)
const bulkActionLoading = ref(false)

// Export
const exportDialog = ref(false)
const exportFormat = ref('csv')
const exportFormats = [
  { label: 'CSV (Excel-kompatibel)', value: 'csv' },
  { label: 'JSON', value: 'json' },
  { label: 'PDF Report', value: 'pdf' },
]
const exportOptions = ref({
  facets: true,
  relations: true,
  dataSources: false,
  notes: false,
})
const exporting = ref(false)

// Notes
const notesDialog = ref(false)
const notes = ref<Note[]>([])
const newNote = ref('')
const savingNote = ref(false)

// Relations Lazy Loading
const loadingRelations = ref(false)
const relationsLoaded = ref(false)

// Computed
const breadcrumbs = computed(() => [
  { title: 'Dashboard', to: '/' },
  { title: entityType.value?.name_plural || 'Entities', to: `/entities/${typeSlug.value}` },
  { title: entity.value?.name || '...', disabled: true },
])

const hasAttributes = computed(() =>
  entity.value?.core_attributes && Object.keys(entity.value.core_attributes).length > 0
)

// Check if search has results
const hasSearchResults = computed(() => {
  if (!facetSearchQuery.value) return true
  const query = facetSearchQuery.value.toLowerCase()
  for (const group of facetsSummary.value?.facets_by_type || []) {
    const facets = getDisplayedFacets(group)
    if (facets.some((f: any) => matchesFacetSearch(f, query))) {
      return true
    }
  }
  return false
})

const documentHeaders = [
  { title: 'Titel', key: 'title' },
  { title: 'Typ', key: 'document_type' },
  { title: 'Datum', key: 'created_at' },
]

// Methods
async function loadEntityData() {
  loading.value = true
  try {
    // Load entity type first
    await store.fetchEntityTypeBySlug(typeSlug.value)

    // Load entity
    await store.fetchEntityBySlug(typeSlug.value, entitySlug.value)

    if (!entity.value) {
      showError('Entity nicht gefunden')
      router.push(`/entities/${typeSlug.value}`)
      return
    }

    // Load facet types if not loaded
    if (store.facetTypes.length === 0) {
      await store.fetchFacetTypes()
    }

    // Load facets summary
    facetsSummary.value = await store.fetchEntityFacetsSummary(entity.value.id)

    // Expand first facet group by default
    if (facetsSummary.value?.facets_by_type?.length) {
      expandedFacets.value = [facetsSummary.value.facets_by_type[0].facet_type_slug]
    }

    // Load notes (from localStorage for now)
    await loadNotes()

    // Reset lazy loading flags
    relationsLoaded.value = false
    expandedFacetValues.value = {}

    // Populate edit form
    editForm.value = {
      name: entity.value.name,
      external_id: entity.value.external_id || '',
    }
  } catch (e) {
    console.error('Failed to load entity', e)
    showError('Fehler beim Laden der Entity')
  } finally {
    loading.value = false
  }
}

async function loadRelations() {
  if (!entity.value || relationsLoaded.value) return

  // Check cache first
  const cacheKey = `relations_${entity.value.id}`
  const cached = getCachedData(cacheKey)
  if (cached) {
    relations.value = cached
    relationsLoaded.value = true
    return
  }

  loadingRelations.value = true
  try {
    const result = await store.fetchEntityRelations({
      entity_id: entity.value.id,
    })
    relations.value = result.items || []
    relationsLoaded.value = true

    // Cache the result
    setCachedData(cacheKey, relations.value)
  } catch (e) {
    console.error('Failed to load relations', e)
  } finally {
    loadingRelations.value = false
  }
}

// =============================================================================
// FACET DISPLAY & SEARCH FUNCTIONS
// =============================================================================

function getDisplayedFacets(facetGroup: any): any[] {
  const slug = facetGroup.facet_type_slug
  // If we have loaded more, use those; otherwise use sample_values
  const allFacets = expandedFacetValues.value[slug] || facetGroup.sample_values || []

  // Apply search filter
  if (facetSearchQuery.value) {
    const query = facetSearchQuery.value.toLowerCase()
    return allFacets.filter((f: any) => matchesFacetSearch(f, query))
  }

  return allFacets
}

function matchesFacetSearch(facet: any, query: string): boolean {
  // Search in text_representation
  if (facet.text_representation?.toLowerCase().includes(query)) return true
  // Search in value object
  const val = facet.value
  if (typeof val === 'string' && val.toLowerCase().includes(query)) return true
  if (typeof val === 'object' && val) {
    if (val.description?.toLowerCase().includes(query)) return true
    if (val.text?.toLowerCase().includes(query)) return true
    if (val.name?.toLowerCase().includes(query)) return true
    if (val.type?.toLowerCase().includes(query)) return true
    if (val.quote?.toLowerCase().includes(query)) return true
  }
  return false
}

function canLoadMore(facetGroup: any): boolean {
  const slug = facetGroup.facet_type_slug
  const loaded = expandedFacetValues.value[slug]?.length || facetGroup.sample_values?.length || 0
  return loaded < facetGroup.value_count
}

function getRemainingCount(facetGroup: any): number {
  const slug = facetGroup.facet_type_slug
  const loaded = expandedFacetValues.value[slug]?.length || facetGroup.sample_values?.length || 0
  return Math.min(10, facetGroup.value_count - loaded)
}

function isExpanded(facetGroup: any): boolean {
  const slug = facetGroup.facet_type_slug
  return !!expandedFacetValues.value[slug]
}

async function loadMoreFacets(facetGroup: any) {
  if (!entity.value) return
  const slug = facetGroup.facet_type_slug
  loadingMoreFacets.value[slug] = true

  try {
    const currentCount = expandedFacetValues.value[slug]?.length || facetGroup.sample_values?.length || 0
    const response = await facetApi.getFacetValues({
      entity_id: entity.value.id,
      facet_type_slug: slug,
      page: 1,
      per_page: currentCount + 10, // Load 10 more
    })

    expandedFacetValues.value[slug] = response.data.items || []
  } catch (e) {
    console.error('Failed to load more facets', e)
    showError('Fehler beim Laden weiterer Facets')
  } finally {
    loadingMoreFacets.value[slug] = false
  }
}

function collapseFacets(facetGroup: any) {
  const slug = facetGroup.facet_type_slug
  delete expandedFacetValues.value[slug]
}

// =============================================================================
// BULK ACTIONS
// =============================================================================

function toggleFacetSelection(id: string) {
  const idx = selectedFacetIds.value.indexOf(id)
  if (idx >= 0) {
    selectedFacetIds.value.splice(idx, 1)
  } else {
    selectedFacetIds.value.push(id)
  }
}

async function bulkVerify() {
  if (selectedFacetIds.value.length === 0) return
  bulkActionLoading.value = true

  try {
    // Verify all selected facets
    await Promise.all(
      selectedFacetIds.value.map(id => store.verifyFacetValue(id, true))
    )

    showSuccess(`${selectedFacetIds.value.length} Facets verifiziert`)

    // Reset selection and refresh
    selectedFacetIds.value = []
    bulkMode.value = false
    if (entity.value) {
      facetsSummary.value = await store.fetchEntityFacetsSummary(entity.value.id)
    }
  } catch (e) {
    showError('Fehler beim Verifizieren')
  } finally {
    bulkActionLoading.value = false
  }
}

async function bulkDelete() {
  if (selectedFacetIds.value.length === 0) return
  bulkActionLoading.value = true

  try {
    // Delete all selected facets
    await Promise.all(
      selectedFacetIds.value.map(id => facetApi.deleteFacetValue(id))
    )

    showSuccess(`${selectedFacetIds.value.length} Facets geloescht`)

    // Reset selection and refresh
    selectedFacetIds.value = []
    bulkMode.value = false
    bulkDeleteConfirm.value = false
    expandedFacetValues.value = {} // Reset expanded state

    if (entity.value) {
      facetsSummary.value = await store.fetchEntityFacetsSummary(entity.value.id)
    }
  } catch (e) {
    showError('Fehler beim Loeschen')
  } finally {
    bulkActionLoading.value = false
  }
}

// =============================================================================
// EXPORT FUNCTIONS
// =============================================================================

async function exportData() {
  if (!entity.value) return
  exporting.value = true

  try {
    const data: any = {
      entity: {
        id: entity.value.id,
        name: entity.value.name,
        type: entityType.value?.name,
        external_id: entity.value.external_id,
        attributes: entity.value.core_attributes,
      },
    }

    // Collect selected data
    if (exportOptions.value.facets && facetsSummary.value?.facets_by_type) {
      data.facets = {}
      for (const group of facetsSummary.value.facets_by_type) {
        // Load all facets for this type
        const response = await facetApi.getFacetValues({
          entity_id: entity.value.id,
          facet_type_slug: group.facet_type_slug,
          per_page: 10000,
        })
        data.facets[group.facet_type_name] = (response.data.items || []).map((f: any) => ({
          value: f.text_representation || getStructuredDescription(f),
          type: getStructuredType(f),
          severity: getStructuredSeverity(f),
          verified: f.human_verified,
          confidence: f.confidence_score,
          source_url: f.source_url,
        }))
      }
    }

    if (exportOptions.value.relations) {
      data.relations = relations.value.map(r => ({
        type: r.relation_type_name,
        target: r.source_entity_id === entity.value?.id ? r.target_entity_name : r.source_entity_name,
        verified: r.human_verified,
      }))
    }

    if (exportOptions.value.dataSources) {
      data.dataSources = dataSources.value.map(s => ({
        name: s.name,
        url: s.base_url,
        status: s.status,
      }))
    }

    if (exportOptions.value.notes) {
      data.notes = notes.value.map(n => ({
        content: n.content,
        author: n.author,
        date: n.created_at,
      }))
    }

    // Generate export file
    if (exportFormat.value === 'json') {
      downloadFile(
        JSON.stringify(data, null, 2),
        `${entity.value.name}_export.json`,
        'application/json'
      )
    } else if (exportFormat.value === 'csv') {
      const csv = generateCSV(data)
      downloadFile(csv, `${entity.value.name}_export.csv`, 'text/csv')
    } else if (exportFormat.value === 'pdf') {
      // For PDF, we'd need a library like jsPDF or generate on backend
      // For now, show message
      showError('PDF-Export wird in Kuerze verfuegbar sein')
      exporting.value = false
      return
    }

    showSuccess('Export erfolgreich')
    exportDialog.value = false
  } catch (e) {
    console.error('Export failed', e)
    showError('Export fehlgeschlagen')
  } finally {
    exporting.value = false
  }
}

function generateCSV(data: any): string {
  const lines: string[] = []

  // Entity info
  lines.push('# Entity Information')
  lines.push(`Name,${escapeCSV(data.entity.name)}`)
  lines.push(`Typ,${escapeCSV(data.entity.type || '')}`)
  lines.push(`Externe ID,${escapeCSV(data.entity.external_id || '')}`)
  lines.push('')

  // Facets
  if (data.facets) {
    for (const [typeName, facets] of Object.entries(data.facets)) {
      lines.push(`# ${typeName}`)
      lines.push('Wert,Typ,Schweregrad,Verifiziert,Konfidenz')
      for (const f of facets as any[]) {
        lines.push([
          escapeCSV(f.value || ''),
          escapeCSV(f.type || ''),
          escapeCSV(f.severity || ''),
          f.verified ? 'Ja' : 'Nein',
          f.confidence ? `${Math.round(f.confidence * 100)}%` : '',
        ].join(','))
      }
      lines.push('')
    }
  }

  // Relations
  if (data.relations?.length) {
    lines.push('# Verknuepfungen')
    lines.push('Typ,Ziel,Verifiziert')
    for (const r of data.relations) {
      lines.push([
        escapeCSV(r.type),
        escapeCSV(r.target),
        r.verified ? 'Ja' : 'Nein',
      ].join(','))
    }
    lines.push('')
  }

  // Notes
  if (data.notes?.length) {
    lines.push('# Notizen')
    lines.push('Datum,Autor,Inhalt')
    for (const n of data.notes) {
      lines.push([
        escapeCSV(n.date || ''),
        escapeCSV(n.author || ''),
        escapeCSV(n.content || ''),
      ].join(','))
    }
  }

  return lines.join('\n')
}

function escapeCSV(value: string): string {
  if (value.includes(',') || value.includes('"') || value.includes('\n')) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}

function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

// =============================================================================
// NOTES FUNCTIONS
// =============================================================================

async function loadNotes() {
  if (!entity.value) return
  try {
    // Notes are stored as a special facet type or in a separate endpoint
    // For now, we'll store them in localStorage as a simple solution
    const key = `entity_notes_${entity.value.id}`
    const stored = localStorage.getItem(key)
    notes.value = stored ? JSON.parse(stored) : []
  } catch (e) {
    console.error('Failed to load notes', e)
    notes.value = []
  }
}

async function saveNote() {
  if (!entity.value || !newNote.value.trim()) return
  savingNote.value = true

  try {
    const note = {
      id: crypto.randomUUID(),
      content: newNote.value.trim(),
      author: 'Aktueller Benutzer', // Would come from auth
      created_at: new Date().toISOString(),
    }

    notes.value.unshift(note)

    // Save to localStorage (would be API in production)
    const key = `entity_notes_${entity.value.id}`
    localStorage.setItem(key, JSON.stringify(notes.value))

    newNote.value = ''
    showSuccess('Notiz gespeichert')
  } catch (e) {
    showError('Fehler beim Speichern der Notiz')
  } finally {
    savingNote.value = false
  }
}

async function deleteNote(noteId: string) {
  if (!entity.value) return

  try {
    notes.value = notes.value.filter(n => n.id !== noteId)

    // Save to localStorage
    const key = `entity_notes_${entity.value.id}`
    localStorage.setItem(key, JSON.stringify(notes.value))

    showSuccess('Notiz geloescht')
  } catch (e) {
    showError('Fehler beim Loeschen der Notiz')
  }
}

async function loadDataSources() {
  if (!entity.value) return

  // Check cache first
  const cacheKey = `datasources_${entity.value.id}`
  const cached = getCachedData(cacheKey)
  if (cached) {
    dataSources.value = cached
    return
  }

  loadingDataSources.value = true
  try {
    // Sources linked via entity_id
    const response = await adminApi.getSources({ entity_id: entity.value.id, per_page: 10000 })
    dataSources.value = response.data.items || []

    // Also check for sources linked via location_name for backward compatibility
    if (dataSources.value.length === 0) {
      const byNameResponse = await adminApi.getSources({ location_name: entity.value.name, per_page: 10000 })
      dataSources.value = byNameResponse.data.items || []
    }

    // Cache the result
    setCachedData(cacheKey, dataSources.value)
  } catch (e) {
    console.error('Failed to load data sources', e)
  } finally {
    loadingDataSources.value = false
  }
}

async function loadDocuments() {
  if (!entity.value) return
  loadingDocuments.value = true
  try {
    // This would need an endpoint to get documents by entity
    // For now we can use the location_name based endpoint
    const response = await adminApi.getSources({ location_name: entity.value.name })
    // This is a placeholder - would need proper document listing by entity
    documents.value = []
  } catch (e) {
    console.error('Failed to load documents', e)
  } finally {
    loadingDocuments.value = false
  }
}

function toggleFacetExpand(slug: string) {
  const idx = expandedFacets.value.indexOf(slug)
  if (idx >= 0) {
    expandedFacets.value.splice(idx, 1)
  } else {
    expandedFacets.value.push(slug)
  }
}

async function openFacetDetails(facetGroup: any) {
  selectedFacetGroup.value = facetGroup
  facetDetailsDialog.value = true

  try {
    const response = await facetApi.getFacetValues({
      entity_id: entity.value?.id,
      facet_type_slug: facetGroup.facet_type_slug,
      per_page: 10000,
    })
    facetDetails.value = response.data.items || []
  } catch (e) {
    console.error('Failed to load facet details', e)
    facetDetails.value = []
  }
}

async function saveFacetValue() {
  if (!newFacet.value.facet_type_id || !newFacet.value.text_representation) return
  if (!entity.value) return

  savingFacet.value = true
  try {
    await facetApi.createFacetValue({
      entity_id: entity.value.id,
      facet_type_id: newFacet.value.facet_type_id,
      value: { text: newFacet.value.text_representation },
      text_representation: newFacet.value.text_representation,
      source_url: newFacet.value.source_url || null,
      confidence_score: newFacet.value.confidence_score,
    })

    showSuccess('Facet-Wert hinzugefuegt')
    addFacetDialog.value = false

    // Reset form
    newFacet.value = {
      facet_type_id: '',
      text_representation: '',
      source_url: '',
      confidence_score: 0.8,
    }

    // Reload facets summary
    facetsSummary.value = await store.fetchEntityFacetsSummary(entity.value.id)
  } catch (e: any) {
    showError(e.response?.data?.detail || 'Fehler beim Speichern')
  } finally {
    savingFacet.value = false
  }
}

async function verifyFacet(facetValueId: string) {
  try {
    await store.verifyFacetValue(facetValueId, true)
    showSuccess('Facet verifiziert')
    // Reload details
    if (selectedFacetGroup.value) {
      await openFacetDetails(selectedFacetGroup.value)
    }
    // Reload summary
    if (entity.value) {
      facetsSummary.value = await store.fetchEntityFacetsSummary(entity.value.id)
    }
  } catch (e) {
    showError('Fehler beim Verifizieren')
  }
}

async function saveEntity() {
  if (!entity.value) return

  savingEntity.value = true
  try {
    await store.updateEntity(entity.value.id, {
      name: editForm.value.name,
      external_id: editForm.value.external_id || null,
    })
    showSuccess('Entity aktualisiert')
    editDialog.value = false
  } catch (e: any) {
    showError(e.response?.data?.detail || 'Fehler beim Speichern')
  } finally {
    savingEntity.value = false
  }
}

async function startCrawl(source: any) {
  startingCrawl.value = source.id
  try {
    await adminApi.startCrawl({ source_ids: [source.id] })
    showSuccess(`Crawl fuer "${source.name}" gestartet`)
    source.hasRunningJob = true
  } catch (e: any) {
    showError(e.response?.data?.detail || 'Fehler beim Starten')
  } finally {
    startingCrawl.value = null
  }
}

function navigateToRelatedEntity(rel: any) {
  const targetId = rel.source_entity_id === entity.value?.id
    ? rel.target_entity_id
    : rel.source_entity_id
  const targetSlug = rel.source_entity_id === entity.value?.id
    ? rel.target_entity_type_slug
    : rel.source_entity_type_slug
  const targetEntitySlug = rel.source_entity_id === entity.value?.id
    ? rel.target_entity_slug || targetId
    : rel.source_entity_slug || targetId

  router.push({
    name: 'entity-detail',
    params: { typeSlug: targetSlug, entitySlug: targetEntitySlug },
  })
}

function goToSources() {
  router.push({ path: '/sources', query: { location_name: entity.value?.name } })
}

// Attribute key translation map (fallback)
const attributeTranslations: Record<string, string> = {
  population: 'Einwohner',
  area_km2: 'Flaeche (km²)',
  official_code: 'Amtlicher Schluessel',
  locality_type: 'Ortstyp',
  website: 'Website',
  academic_title: 'Titel',
  first_name: 'Vorname',
  last_name: 'Nachname',
  email: 'E-Mail',
  phone: 'Telefon',
  role: 'Position',
  org_type: 'Organisationstyp',
  address: 'Adresse',
  event_date: 'Startdatum',
  event_end_date: 'Enddatum',
  location: 'Ort',
  organizer: 'Veranstalter',
  event_type: 'Veranstaltungstyp',
  description: 'Beschreibung',
}

// Helpers
function formatAttributeKey(key: string): string {
  // First try to get title from entity type's attribute_schema
  const schema = entityType.value?.attribute_schema
  if (schema?.properties?.[key]?.title) {
    return schema.properties[key].title
  }
  // Then try the translation map
  if (attributeTranslations[key]) {
    return attributeTranslations[key]
  }
  // Finally, fallback to basic formatting
  return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

function formatAttributeValue(value: any): string {
  if (typeof value === 'number') {
    return value.toLocaleString('de-DE')
  }
  return String(value)
}

function formatFacetValue(facet: any): string {
  if (facet.text_representation) return facet.text_representation
  if (typeof facet.value === 'string') return facet.value
  if (facet.value?.text) return facet.value.text
  return JSON.stringify(facet.value)
}

function formatDate(dateStr: string): string {
  return format(new Date(dateStr), 'dd.MM.yyyy HH:mm', { locale: de })
}

function getConfidenceColor(score: number | null): string {
  if (!score) return 'grey'
  if (score >= 0.8) return 'success'
  if (score >= 0.5) return 'warning'
  return 'error'
}

function getSourceStatusColor(status: string): string {
  const colors: Record<string, string> = {
    ACTIVE: 'success',
    INACTIVE: 'grey',
    ERROR: 'error',
    PENDING: 'warning',
  }
  return colors[status] || 'grey'
}

function getSourceStatusIcon(status: string): string {
  const icons: Record<string, string> = {
    ACTIVE: 'mdi-check-circle',
    INACTIVE: 'mdi-pause-circle',
    ERROR: 'mdi-alert-circle',
    PENDING: 'mdi-clock',
  }
  return icons[status] || 'mdi-help-circle'
}

// Structured Facet Value Helpers
function getStructuredDescription(facet: any): string {
  // Try text_representation first
  if (facet.text_representation) return facet.text_representation
  // Then try value.description or value.text
  const val = facet.value
  if (!val) return ''
  if (typeof val === 'string') return val
  return val.description || val.text || val.concern || val.opportunity || ''
}

function getStructuredType(facet: any): string | null {
  const val = facet.value
  if (!val || typeof val === 'string') return null
  return val.type || null
}

function getStructuredSeverity(facet: any): string | null {
  const val = facet.value
  if (!val || typeof val === 'string') return null
  return val.severity || null
}

function getStructuredQuote(facet: any): string | null {
  const val = facet.value
  if (!val || typeof val === 'string') return null
  return val.quote || null
}

function getSeverityColor(severity: string | null): string {
  if (!severity) return 'grey'
  const s = severity.toLowerCase()
  if (s === 'hoch' || s === 'high') return 'error'
  if (s === 'mittel' || s === 'medium') return 'warning'
  if (s === 'niedrig' || s === 'low') return 'success'
  return 'grey'
}

function getSeverityIcon(severity: string | null): string {
  if (!severity) return 'mdi-minus'
  const s = severity.toLowerCase()
  if (s === 'hoch' || s === 'high') return 'mdi-alert'
  if (s === 'mittel' || s === 'medium') return 'mdi-alert-circle-outline'
  if (s === 'niedrig' || s === 'low') return 'mdi-information-outline'
  return 'mdi-minus'
}

// Contact Helpers
function getContactName(facet: any): string {
  if (facet.text_representation) return facet.text_representation
  const val = facet.value
  if (!val) return ''
  if (typeof val === 'string') return val
  return val.name || ''
}

function getContactRole(facet: any): string | null {
  const val = facet.value
  if (!val || typeof val === 'string') return null
  return val.role || val.position || null
}

function getContactEmail(facet: any): string | null {
  const val = facet.value
  if (!val || typeof val === 'string') return null
  return val.email || null
}

function getContactPhone(facet: any): string | null {
  const val = facet.value
  if (!val || typeof val === 'string') return null
  return val.phone || val.telefon || null
}

function getContactSentiment(facet: any): string | null {
  const val = facet.value
  if (!val || typeof val === 'string') return null
  return val.sentiment || null
}

function getContactStatement(facet: any): string | null {
  const val = facet.value
  if (!val || typeof val === 'string') return null
  return val.statement || val.quote || null
}

function getSentimentColor(sentiment: string | null): string {
  if (!sentiment) return 'grey'
  const s = sentiment.toLowerCase()
  if (s === 'positiv' || s === 'positive') return 'success'
  if (s === 'negativ' || s === 'negative') return 'error'
  return 'grey'
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text)
  showSuccess('In Zwischenablage kopiert')
}

// Watch for tab changes to load data lazily
watch(activeTab, (tab) => {
  if (tab === 'relations' && !relationsLoaded.value) {
    loadRelations()
  }
  if (tab === 'sources' && dataSources.value.length === 0) {
    loadDataSources()
  }
  if (tab === 'documents' && documents.value.length === 0) {
    loadDocuments()
  }
})

// Watch for route changes
watch([typeSlug, entitySlug], () => {
  // Reset state for new entity
  bulkMode.value = false
  selectedFacetIds.value = []
  facetSearchQuery.value = ''
  loadEntityData()
})

// Init
onMounted(() => {
  loadEntityData()
})
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}

.facet-item {
  transition: all 0.2s ease;
  border: 2px solid transparent;
}

.facet-item:hover {
  border-color: rgba(var(--v-theme-primary), 0.3);
}

.facet-item.selected {
  border-color: rgb(var(--v-theme-primary));
  background-color: rgba(var(--v-theme-primary), 0.08) !important;
}

.bg-primary-lighten-5 {
  background-color: rgba(var(--v-theme-primary), 0.1);
}
</style>
