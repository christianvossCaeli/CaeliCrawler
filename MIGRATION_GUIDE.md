# CaeliCrawler Package Migration Guide

## Datum: 2025-12-19

---

## Backend (Python) Updates

### 1. langchain-core 1.2.3 → 1.2.4
- **Typ**: Minor Update
- **Breaking Changes**: Keine
- **Aktion**: Direktes Update

### 2. redis 6.4.0 → 7.1.0
- **Typ**: Major Update
- **Breaking Changes**: Minimal - API ist weitgehend kompatibel
- **Aktion**: Direktes Update, Tests durchführen

### 3. pip 25.0.1 → 25.3
- **Typ**: Minor Update
- **Aktion**: `pip install --upgrade pip`

---

## Frontend (npm) Updates

### 1. date-fns 3.6.0 → 4.1.0
**Quelle**: [date-fns v4.0 Blog](https://blog.date-fns.org/v40-with-time-zone-support/)

**Breaking Changes** (minimal):
- ESM-first Package-Struktur (hat jetzt `"type": "module"`)
- Einige TypeScript-Typ-Änderungen bei Funktions-Generics

**Neue Features**:
- First-class Time Zone Support
- Bessere Date Extension Handling

**Migration**: Direktes Update, bei TypeScript-Fehlern Typen anpassen.

---

### 2. Pinia 2.3.1 → 3.0.4
**Quelle**: [Pinia Migration v2-v3](https://pinia.vuejs.org/cookbook/migration-v2-v3.html)

**Breaking Changes**:
1. `PiniaStorePlugin` Typ entfernt → Nutze `PiniaPlugin`
2. `defineStore({ id: 'id' })` entfernt → Nutze `defineStore('id')`
3. TypeScript 5+ erforderlich
4. Vue 2 Support entfernt (nicht relevant für uns)

**Migration**:
```typescript
// Alt (falls verwendet):
import { PiniaStorePlugin } from 'pinia'
// Neu:
import { PiniaPlugin } from 'pinia'

// Alt (falls verwendet):
defineStore({ id: 'myStore', ... })
// Neu:
defineStore('myStore', { ... })
```

---

### 3. vue-i18n 9.14.5 → 11.2.2
**Quelle**: [vue-i18n Breaking Changes v11](https://vue-i18n.intlify.dev/guide/migration/breaking11)

**Breaking Changes**:
1. **Legacy API Mode deprecated** (wird in v12 entfernt)
2. **`tc` und `$tc` entfernt** → Nutze `t`/`$t` mit plural Parameter
3. **Custom `v-t` Directive deprecated**

**Migration**:
```typescript
// Alt:
$tc('message.count', count)
// Neu:
$t('message.count', count)

// Bei Plural-Nachrichten:
// messages.json: "count": "no items | one item | {count} items"
$t('message.count', { count: 5 }, 5)
```

**Prüfen**:
- Keine `tc`/`$tc` Verwendung im Code
- Keine `v-t` Directive Verwendung

---

### 4. Vite 5.4.21 → 7.3.0
**Quelle**: [Vite Migration Guide](https://vite.dev/guide/migration), [Vite 7 Announcement](https://vite.dev/blog/announcing-vite7)

**Voraussetzungen**:
- Node.js 20.19+ oder 22.12+ (Node 18 nicht mehr unterstützt)

**Breaking Changes v5 → v6**:
- CSS Output Filename in Library Mode geändert
- Einige interne API-Änderungen

**Breaking Changes v6 → v7**:
1. **Node.js 20.19+** erforderlich
2. **Browser Target**: `'modules'` → `'baseline-widely-available'`
3. **Sass Legacy API entfernt** → Nur modern API
4. **`splitVendorChunkPlugin` entfernt** → Nutze `build.rollupOptions.output.manualChunks`
5. **`transformIndexHtml` Hook**: `enforce`→`order`, `transform`→`handler`

**Abhängige Updates**:
- `@vitejs/plugin-vue` 4.6.2 → 6.0.3
- `vue-tsc` 1.8.27 → 3.1.8
- `@vue/tsconfig` 0.5.1 → 0.8.1

**Migration**:
```typescript
// vite.config.ts - Falls Sass Legacy API verwendet:
// Entfernen: css.preprocessorOptions.sass.api
// Entfernen: css.preprocessorOptions.scss.api

// Falls splitVendorChunkPlugin verwendet:
// Alt:
import { splitVendorChunkPlugin } from 'vite'
// Neu: Entfernen und manualChunks nutzen falls nötig
```

---

### 5. vue-tsc 1.8.27 → 3.1.8
- Folgt dem Vite 7 Update
- Benötigt kompatible @volar Versionen

### 6. @vitejs/plugin-vue 4.6.2 → 6.0.3
- Folgt dem Vite 7 Update
- API-kompatibel

### 7. @vue/tsconfig 0.5.1 → 0.8.1
- TypeScript-Konfigurationsanpassungen
- Rückwärtskompatibel

### 8. @types/node 20.19.27 → 25.0.3
- TypeScript-Typdefinitionen für Node.js
- Sollte mit Node.js 20+ kompatibel sein

### 9. sass 1.97.0 → 1.97.1
- Patch Update
- Keine Breaking Changes

---

## Migrations-Reihenfolge

1. **Backend zuerst** (weniger riskant)
2. **Frontend Minor/Patch Updates**
3. **date-fns 4** (minimal)
4. **Pinia 3** (minimal)
5. **vue-i18n 11** (Legacy API prüfen)
6. **Vite 7 + Plugins** (größtes Update)
7. **Tests durchführen**

---

## Rollback-Plan

Falls Probleme auftreten:
1. Git commit vor jedem Major-Update
2. Bei Fehlern: `git checkout -- package.json package-lock.json && npm install`
3. Backend: requirements.txt wiederherstellen

---

## Durchgeführte Änderungen (2025-12-19)

### TypeScript Fixes für Vite 7 + vue-tsc 3

1. **vite-env.d.ts erstellt** (`src/vite-env.d.ts`)
   - Vite Client Types für `import.meta.env` Support hinzugefügt

2. **Vuetify DataTable Header Types**
   - `align` Property mit `as const` oder expliziten Union Types annotiert
   - Betrifft: NotificationRules.vue, EntitiesView.vue

3. **Unused Variables entfernt**
   - Diverse unused imports und Variablen entfernt (strict mode compliance)
   - Betrifft: ChatAssistant.vue, CrawlerView.vue, ExportView.vue, LoginView.vue, NotificationsView.vue, usw.

4. **Type Safety Fixes**
   - `null` zu `undefined` Konvertierung mit `??` Operator
   - Non-null Assertions (`!`) für bereits geprüfte Werte
   - Explizite Typisierung für dynamische Arrays

5. **i18n Array Casting**
   - `t()` Rückgabewert mit `as unknown as T[]` für Array-basierte Übersetzungen
   - Betrifft: HelpSmartQuerySection.vue

6. **v-virtual-scroll Typisierung**
   - Interfaces für Log-Einträge definiert
   - Betrifft: CrawlerView.vue

### Status

- **Backend**: 94 Tests erfolgreich
- **Frontend**: Build erfolgreich (vue-tsc && vite build)
- **Dev Server**: Startet ohne Fehler

---

## Durchgeführte Optimierungen (2025-12-20)

### 1. VNumberInput Migration
Alle `v-text-field type="number"` wurden auf `v-number-input` migriert für bessere UX:
- Stepper-Buttons (+/-)
- Bessere Mobile-UX
- Echte Min/Max-Validierung

**Betroffene Dateien (11 Stellen):**
- `SourcesView.vue` - max_depth, max_pages
- `DashboardView.vue` - crawlerFilter.limit
- `CategoriesView.vue` - crawlerFilter.limit
- `NotificationRules.vue` - min_confidence
- `WizardStep.vue` - number input
- `EntityTypesView.vue` - display_order
- `FacetTypesView.vue` - display_order
- `EntitiesView.vue` - core_attributes, latitude, longitude

### 2. date-fns TZDate Integration
Timezone-Support mit `@date-fns/tz` hinzugefügt:
```typescript
import { TZDate } from '@date-fns/tz'

// Verwendung in usePySisHelpers.ts:
const tzDate = new TZDate(dateStr, 'Europe/Berlin')
format(tzDate, 'dd.MM.yyyy HH:mm', { locale: de })
```

### 3. Vite Build-Optimierung
`manualChunks` Konfiguration für besseres Caching:
```typescript
manualChunks: {
  'vue-core': ['vue', 'vue-router', 'pinia'],
  'vuetify': ['vuetify'],
  'charts': ['chart.js', 'vue-chartjs'],
  'i18n': ['vue-i18n'],
  'date-utils': ['date-fns', '@date-fns/tz'],
}
```

---

## Zukünftige Features (Dokumentation)

### Vuetify VFileUpload (ab v3.7.6)
Falls Datei-Upload-Funktionalität benötigt wird (z.B. Dokument-Import):

```vue
<template>
  <v-file-upload
    v-model="files"
    :accept="['application/pdf', 'text/html', 'application/msword']"
    multiple
    show-size
    :max-files="10"
    :max-file-size="10 * 1024 * 1024"
  >
    <template #title>
      Dokumente hochladen
    </template>
    <template #subtitle>
      PDF, HTML, Word (max. 10MB pro Datei)
    </template>
  </v-file-upload>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const files = ref<File[]>([])

// Nach Upload:
async function uploadFiles() {
  const formData = new FormData()
  files.value.forEach(file => formData.append('files', file))
  await api.post('/documents/upload', formData)
}
</script>
```

**Anwendungsfälle:**
- Manueller Dokument-Import
- Batch-Upload von PDFs
- Konfigurationsdateien hochladen

---

### Celery Google Cloud Pub/Sub (ab v5.5)
Falls Migration zu Google Cloud Platform geplant:

**Installation:**
```bash
pip install "celery[gcpubsub]"
```

**Konfiguration:**
```python
# config.py
CELERY_BROKER_URL = "gcpubsub://projects/caeli-crawler-prod"
CELERY_RESULT_BACKEND = "gs://caeli-crawler-results"

# celery_app.py
app = Celery('caeli')
app.conf.update(
    broker_transport_options={
        'queue_name_prefix': 'caeli-',
        'ack_deadline_seconds': 300,
        'expiration_seconds': 86400,  # 24h
    }
)
```

**Vorteile:**
- Serverless Skalierung
- Keine Redis-Infrastruktur nötig
- Integration mit anderen GCP-Services
- Automatische Dead-Letter-Queues

**Hinweise:**
- Erfordert GCP-Projekt und Credentials
- Subscriptions werden nach 24h Inaktivität gelöscht
- Für Flower: `--inspect-timeout=10` Option nötig

---

## Quellen

- [Vite Migration Guide](https://vite.dev/guide/migration)
- [Vite 7 Announcement](https://vite.dev/blog/announcing-vite7)
- [Pinia v2-v3 Migration](https://pinia.vuejs.org/cookbook/migration-v2-v3.html)
- [vue-i18n Breaking Changes v11](https://vue-i18n.intlify.dev/guide/migration/breaking11)
- [date-fns v4.0 Blog](https://blog.date-fns.org/v40-with-time-zone-support/)
