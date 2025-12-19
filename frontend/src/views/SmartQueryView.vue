<template>
  <div>
    <div class="d-flex justify-space-between align-center mb-6">
      <div>
        <h1 class="text-h4">Smart Query</h1>
        <p class="text-subtitle-1 text-medium-emphasis mt-1">
          Stelle Fragen in natuerlicher Sprache oder erstelle Daten per Kommando
        </p>
      </div>
    </div>

    <!-- Query Input -->
    <v-card class="mb-6">
      <v-card-text>
        <v-textarea
          v-model="question"
          :label="writeMode ? 'Dein Kommando' : 'Deine Frage'"
          :placeholder="writeMode
            ? 'z.B. Erstelle eine Person Max Mueller, Buergermeister von Gummersbach'
            : 'z.B. Zeige mir alle Pain Points von Gemeinden'"
          rows="3"
          variant="outlined"
          hide-details
          class="mb-4"
          :disabled="previewData !== null"
        />
        <div class="d-flex justify-space-between align-center">
          <div class="d-flex align-center">
            <v-switch
              v-model="writeMode"
              color="warning"
              hide-details
              density="compact"
              class="mr-3"
              :disabled="previewData !== null"
            >
              <template v-slot:label>
                <v-icon :color="writeMode ? 'warning' : 'grey'" class="mr-1">
                  {{ writeMode ? 'mdi-pencil-plus' : 'mdi-magnify' }}
                </v-icon>
                {{ writeMode ? 'Schreib-Modus' : 'Lese-Modus' }}
              </template>
            </v-switch>
            <v-chip v-if="writeMode && !previewData" color="info" size="small" variant="tonal">
              <v-icon start size="small">mdi-eye</v-icon>
              Vorschau wird zuerst angezeigt
            </v-chip>
          </div>
          <v-btn
            v-if="!previewData"
            :color="writeMode ? 'warning' : 'primary'"
            size="large"
            :loading="loading"
            :disabled="!question.trim()"
            @click="executeQuery"
          >
            <v-icon left>{{ writeMode ? 'mdi-eye' : 'mdi-magnify' }}</v-icon>
            {{ writeMode ? 'Vorschau' : 'Abfragen' }}
          </v-btn>
        </div>
      </v-card-text>
    </v-card>

    <!-- Example Queries -->
    <v-card class="mb-6" v-if="!results && !previewData">
      <v-card-title class="text-h6">
        <v-icon left>mdi-lightbulb-outline</v-icon>
        {{ writeMode ? 'Beispiel-Kommandos' : 'Beispiel-Fragen' }}
      </v-card-title>
      <v-card-text>
        <v-chip-group>
          <v-chip
            v-for="example in currentExamples"
            :key="example.question"
            @click="useExample(example.question)"
            variant="outlined"
            :color="writeMode ? 'warning' : 'primary'"
            class="ma-1"
          >
            {{ example.question }}
          </v-chip>
        </v-chip-group>
      </v-card-text>
    </v-card>

    <!-- Error -->
    <v-alert v-if="error" type="error" class="mb-6" closable @click:close="error = null">
      {{ error }}
    </v-alert>

    <!-- Preview Mode (Write) -->
    <template v-if="previewData">
      <v-card class="mb-4" color="warning" variant="tonal">
        <v-card-title>
          <v-icon left>mdi-eye-check</v-icon>
          Vorschau - Bitte bestaetigen
        </v-card-title>
        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-4">
            <strong>{{ previewData.preview?.operation_de }}</strong>
            <div class="mt-1">{{ previewData.preview?.description }}</div>
          </v-alert>

          <v-card variant="outlined" class="mb-4">
            <v-card-title class="text-subtitle-1">
              <v-icon left size="small">mdi-format-list-bulleted</v-icon>
              Details
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
            <v-expansion-panel title="Technische Details">
              <v-expansion-panel-text>
                <pre class="text-caption">{{ JSON.stringify(previewData.interpretation, null, 2) }}</pre>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="cancelPreview">
            <v-icon start>mdi-close</v-icon>
            Abbrechen
          </v-btn>
          <v-btn color="success" variant="elevated" :loading="loading" @click="confirmWrite">
            <v-icon start>mdi-check</v-icon>
            Bestaetigen & Erstellen
          </v-btn>
        </v-card-actions>
      </v-card>
    </template>

    <!-- Write Results -->
    <template v-if="results?.mode === 'write'">
      <v-card class="mb-4" :color="results.success ? 'success' : 'error'" variant="tonal">
        <v-card-title>
          <v-icon left>{{ results.success ? 'mdi-check-circle' : 'mdi-alert-circle' }}</v-icon>
          {{ results.success ? 'Erfolgreich erstellt' : 'Fehler' }}
        </v-card-title>
        <v-card-text>
          <div class="text-body-1 mb-3">{{ results.message }}</div>

          <!-- Created Items -->
          <template v-if="results.created_items?.length > 0">
            <div class="text-subtitle-2 mb-2">Erstellte Elemente:</div>
            <v-list density="compact" class="bg-transparent">
              <v-list-item
                v-for="item in results.created_items"
                :key="item.id"
                :title="item.name || item.type"
                :subtitle="`${item.type}${item.entity_type ? ' (' + item.entity_type + ')' : ''} - ID: ${item.id.substring(0, 8)}...`"
              >
                <template v-slot:prepend>
                  <v-icon :color="getItemTypeColor(item.type)">
                    {{ getItemTypeIcon(item.type) }}
                  </v-icon>
                </template>
              </v-list-item>
            </v-list>
          </template>

          <!-- Interpretation -->
          <v-expansion-panels variant="accordion" class="mt-3">
            <v-expansion-panel title="Interpretation">
              <v-expansion-panel-text>
                <pre class="text-caption">{{ JSON.stringify(results.interpretation, null, 2) }}</pre>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-card-text>
        <v-card-actions>
          <v-btn variant="text" @click="resetAll">Neues Kommando</v-btn>
        </v-card-actions>
      </v-card>
    </template>

    <!-- Read Results -->
    <template v-if="results?.mode === 'read' || (!results?.mode && results && !previewData)">
      <!-- Query Interpretation -->
      <v-card class="mb-4">
        <v-card-title class="text-subtitle-1">
          <v-icon left size="small">mdi-brain</v-icon>
          KI-Interpretation
        </v-card-title>
        <v-card-text>
          <v-chip class="mr-2" size="small" color="primary">
            Entity: {{ results.query_interpretation?.primary_entity_type }}
          </v-chip>
          <v-chip
            v-for="facet in results.query_interpretation?.facet_types || []"
            :key="facet"
            class="mr-2"
            size="small"
            color="secondary"
          >
            Facet: {{ facet }}
          </v-chip>
          <v-chip class="mr-2" size="small" :color="getTimeFilterColor(results.query_interpretation?.time_filter)">
            {{ results.query_interpretation?.time_filter || 'all' }}
          </v-chip>
          <div class="text-caption mt-2" v-if="results.query_interpretation?.explanation">
            {{ results.query_interpretation.explanation }}
          </div>
        </v-card-text>
      </v-card>

      <!-- Results Count -->
      <v-card class="mb-4">
        <v-card-text class="d-flex align-center">
          <v-icon class="mr-2" color="success">mdi-check-circle</v-icon>
          <span class="text-h6">{{ results.total }} Ergebnisse</span>
          <v-spacer />
          <v-chip size="small" variant="outlined">
            Gruppierung: {{ results.grouping || 'flat' }}
          </v-chip>
        </v-card-text>
      </v-card>

      <!-- Event-grouped Results -->
      <template v-if="results.grouping === 'by_event'">
        <v-card v-for="event in results.items" :key="event.event_name" class="mb-4">
          <v-card-title>
            <v-icon left color="orange">mdi-calendar-star</v-icon>
            {{ event.event_name }}
          </v-card-title>
          <v-card-subtitle>
            <v-icon size="small">mdi-calendar</v-icon>
            {{ event.event_date || 'Datum unbekannt' }}
            <span class="mx-2">|</span>
            <v-icon size="small">mdi-map-marker</v-icon>
            {{ event.event_location || 'Ort unbekannt' }}
          </v-card-subtitle>
          <v-card-text>
            <v-list density="compact">
              <v-list-subheader>Teilnehmer ({{ event.attendees?.length || 0 }})</v-list-subheader>
              <v-list-item
                v-for="attendee in event.attendees"
                :key="attendee.person_id"
                :title="attendee.person_name"
                :subtitle="formatAttendeeSubtitle(attendee)"
              >
                <template v-slot:prepend>
                  <v-avatar color="primary" size="32">
                    <span class="text-caption">{{ getInitials(attendee.person_name) }}</span>
                  </v-avatar>
                </template>
                <template v-slot:append>
                  <v-chip v-if="attendee.role" size="x-small" color="info">
                    {{ attendee.role }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </template>

      <!-- Flat Results -->
      <template v-else>
        <v-card v-for="item in results.items" :key="item.entity_id" class="mb-4">
          <v-card-title>
            <v-icon left :color="getEntityTypeColor(item.entity_type)">
              {{ getEntityTypeIcon(item.entity_type) }}
            </v-icon>
            {{ item.entity_name }}
          </v-card-title>
          <v-card-subtitle v-if="item.attributes?.position">
            {{ item.attributes.position }}
            <span v-if="item.relations?.works_for">
              @ {{ item.relations.works_for.entity_name }}
            </span>
          </v-card-subtitle>
          <v-card-text v-if="Object.keys(item.facets || {}).length > 0">
            <template v-for="(values, facetType) in item.facets" :key="facetType">
              <div v-if="values.length > 0" class="mb-3">
                <div class="text-subtitle-2 mb-1">{{ facetType }} ({{ values.length }})</div>
                <v-chip
                  v-for="fv in values.slice(0, 5)"
                  :key="fv.id"
                  size="small"
                  class="mr-1 mb-1"
                  variant="outlined"
                >
                  {{ fv.text?.substring(0, 50) }}{{ fv.text?.length > 50 ? '...' : '' }}
                </v-chip>
                <v-chip v-if="values.length > 5" size="small" variant="text">
                  +{{ values.length - 5 }} weitere
                </v-chip>
              </div>
            </template>
          </v-card-text>
        </v-card>
      </template>

      <!-- No Results -->
      <v-card v-if="results.total === 0" class="text-center pa-8">
        <v-icon size="64" color="grey">mdi-database-search</v-icon>
        <div class="text-h6 mt-4">Keine Ergebnisse gefunden</div>
        <div class="text-body-2 text-medium-emphasis">
          Versuche eine andere Formulierung oder pruefe ob die entsprechenden Daten vorhanden sind.
        </div>
      </v-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/services/api'

const question = ref('')
const loading = ref(false)
const error = ref<string | null>(null)
const results = ref<any>(null)
const previewData = ref<any>(null)
const writeMode = ref(false)

const readExamples = ref([
  { question: 'Zeige mir auf welche kuenftige Events wichtige Entscheider-Personen von Gemeinden gehen' },
  { question: 'Welche Buergermeister sprechen auf Events?' },
  { question: 'Zeige mir alle Pain Points von Gemeinden' },
  { question: 'Zeige mir Pain Points von Gummersbach' },
])

const writeExamples = ref([
  { question: 'Erstelle eine Person Max Mueller, Buergermeister' },
  { question: 'Fuege einen Pain Point fuer Muenster hinzu: Personalmangel in der IT' },
  { question: 'Neue Organisation: Caeli Wind GmbH, Windenergie-Entwickler' },
  { question: 'Verknuepfe Max Mueller mit Gummersbach als Arbeitgeber' },
])

const currentExamples = computed(() => writeMode.value ? writeExamples.value : readExamples.value)

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

async function executeQuery() {
  if (!question.value.trim()) return

  loading.value = true
  error.value = null
  results.value = null
  previewData.value = null

  try {
    if (writeMode.value) {
      // Write mode - get preview first
      const response = await api.post('/v1/analysis/smart-write', {
        question: question.value,
        preview_only: true,
        confirmed: false
      })

      if (response.data.mode === 'preview' && response.data.success) {
        previewData.value = response.data
      } else {
        error.value = response.data.message || 'Keine Schreib-Operation erkannt'
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
    error.value = e.response?.data?.detail || e.message || 'Fehler bei der Abfrage'
  } finally {
    loading.value = false
  }
}

async function confirmWrite() {
  if (!question.value.trim()) return

  loading.value = true
  error.value = null

  try {
    const response = await api.post('/v1/analysis/smart-write', {
      question: question.value,
      preview_only: false,
      confirmed: true
    })
    results.value = response.data
    previewData.value = null
  } catch (e: any) {
    error.value = e.response?.data?.detail || e.message || 'Fehler beim Erstellen'
  } finally {
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

function getItemTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    entity: 'mdi-shape',
    facet_value: 'mdi-tag',
    relation: 'mdi-arrow-right-bold',
  }
  return icons[type] || 'mdi-check'
}

function getItemTypeColor(type: string): string {
  const colors: Record<string, string> = {
    entity: 'primary',
    facet_value: 'secondary',
    relation: 'info',
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
  return parts.join(' | ') || 'Keine Details'
}

onMounted(() => {
  loadExamples()
})
</script>
