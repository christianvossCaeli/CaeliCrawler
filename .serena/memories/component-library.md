# Component Library Dokumentation

## Datum: December 2024

## Übersicht

Das Frontend nutzt eine modulare Component-Architektur mit klarer Trennung zwischen wiederverwendbaren und domain-spezifischen Komponenten.

## Verzeichnisstruktur

```
frontend/src/components/
├── common/          # Wiederverwendbare UI-Komponenten
├── sources/         # Datenquellen-Management
│   ├── chips/       # Status/Type Chips
│   ├── source-form/ # Formular-Komponenten
│   └── ai-discovery/# AI-Discovery Wizard
├── entity/          # Entity-Detail Komponenten
├── entities/        # Entity-Listen Komponenten
├── categories/      # Kategorien-Management
├── assistant/       # AI Chat-Assistent
├── smartquery/      # Smart Query System
│   └── visualizations/
├── summaries/       # Dashboard Widgets
├── help/            # Hilfe-Dokumentation
└── [Standalone]     # Top-Level Komponenten
```

## Common Components (`/common`)

### PageHeader
Einheitlicher Seiten-Header mit Icon, Titel und Action-Buttons.

```vue
<PageHeader
  title="Entities"
  subtitle="Alle gespeicherten Entitäten"
  icon="mdi-database"
  :count="total"
>
  <template #actions>
    <v-btn>Action</v-btn>
  </template>
</PageHeader>
```

**Props:**
- `title: string` - Haupttitel
- `subtitle?: string` - Untertitel
- `icon: string` - MDI Icon
- `count?: number | string` - Anzahl-Anzeige
- `avatarColor?: string` - Avatar-Farbe (default: primary)

### ConfirmDialog
Modaler Bestätigungsdialog mit anpassbarem Stil.

```vue
<ConfirmDialog
  v-model="showDialog"
  title="Löschen bestätigen"
  message="Wirklich löschen?"
  subtitle="Kann nicht rückgängig gemacht werden"
  confirm-color="error"
  :loading="deleting"
  @confirm="handleDelete"
/>
```

**Props:**
- `title: string` - Dialog-Titel
- `message: string` - Hauptnachricht
- `subtitle?: string` - Zusatzinfo
- `icon?: string` - Icon (default: mdi-alert)
- `confirmText?: string` - Button-Text
- `confirmColor?: string` - Button-Farbe (default: error)
- `loading?: boolean` - Ladezustand

### FilterCard
Container für Suchfelder und Filter-Optionen.

```vue
<FilterCard
  v-model:search="searchQuery"
  :has-active-filters="hasFilters"
  :loading="loading"
  @reset="clearFilters"
  @refresh="loadData"
>
  <template #filters>
    <v-select ... />
  </template>
  <template #actions>
    <v-btn>Export</v-btn>
  </template>
</FilterCard>
```

**Props:**
- `search?: string` - Suchbegriff (v-model)
- `hasActiveFilters?: boolean` - Reset-Button anzeigen
- `showSearch?: boolean` - Suchfeld anzeigen
- `showRefresh?: boolean` - Refresh-Button anzeigen
- `loading?: boolean` - Ladezustand

### ErrorBoundary
Fängt Fehler in Child-Komponenten ab und zeigt Error-UI.

```vue
<ErrorBoundary>
  <SomeComponent />
</ErrorBoundary>

<!-- Custom Error Slot -->
<ErrorBoundary>
  <template #error="{ error, reset }">
    <div>{{ error.message }}</div>
    <v-btn @click="reset">Retry</v-btn>
  </template>
  <SomeComponent />
</ErrorBoundary>
```

### ScheduleBuilder
Cron-Schedule Builder für wiederkehrende Tasks.

```vue
<ScheduleBuilder
  v-model="schedule"
  :disabled="false"
/>
```

**Modes:** Interval, Daily, Weekly, Monthly, Custom Cron

### AsyncWrapper
Wrapper für async-geladene Komponenten mit Loading/Error States.

## Source Chips (`/sources/chips`)

### SourceTypeChip
Zeigt Quelltyp mit Icon und Farbe.

```vue
<SourceTypeChip type="website" />
<!-- Typen: website, api, sharepoint, rss, manual -->
```

### SourceStatusChip
Status-Badge mit Farbe und Icon.

```vue
<SourceStatusChip status="active" />
<!-- Status: active, inactive, error, processing -->
```

### ConfidenceChip
Konfidenz-Anzeige als Chip.

```vue
<ConfidenceChip :score="0.85" />
```

### TagChip
Tag-Anzeige mit optionaler Lösch-Funktion.

```vue
<TagChip tag="wichtig" closable @close="removeTag" />
```

## Standalone Components

### DynamicSchemaForm
Generiert Formulare aus JSON-Schema.

```vue
<DynamicSchemaForm
  v-model="formData"
  :schema="jsonSchema"
/>
```

**Features:**
- Automatische Feldtyp-Erkennung (string, number, boolean, enum, array)
- Email/URL/Date Format-Unterstützung
- Required-Feld Validierung
- i18n-Unterstützung

### FavoriteButton
Star-Toggle für Favoriten.

```vue
<FavoriteButton
  :favorited="isFav"
  :loading="saving"
  @toggle="toggleFavorite"
/>
```

### LanguageSwitcher
Sprachwechsel-Dropdown.

### PasswordStrengthIndicator
Zeigt Passwort-Stärke während Eingabe.

## Entity Components (`/entity`)

### EntityDialogsManager
Zentraler Dialog-Container für Entity-Detail-Seite.
Verwaltet alle Dialoge (Add Facet, Edit, Export, etc.).

### EntityDetailHeader
Header mit Entity-Info, Actions und Quick-Stats.

### EntityTabsNavigation
Tab-Navigation für Entity-Detail-Bereiche.

### EntityFacetsTab / EntityConnectionsTab / EntitySourcesTab
Spezialisierte Tab-Inhalte.

## SmartQuery Visualizations (`/smartquery/visualizations`)

### Verfügbare Typen:
- `TableVisualization` - Tabellen-Ansicht
- `BarChartVisualization` - Balkendiagramm
- `LineChartVisualization` - Liniendiagramm
- `PieChartVisualization` - Kreisdiagramm
- `MapVisualization` - Kartenansicht
- `StatCardVisualization` - Kennzahlen-Karten
- `TextVisualization` - Textausgabe
- `CalendarVisualization` - Kalender-Ansicht
- `ComparisonVisualization` - Vergleichsansicht

## Best Practices

### 1. Barrel Exports nutzen
```typescript
// Import aus index.ts
import { PageHeader, FilterCard } from '@/components/common'
import { SourceTypeChip, TagChip } from '@/components/sources/chips'
```

### 2. Props mit withDefaults
```vue
<script setup lang="ts">
withDefaults(defineProps<{
  title: string
  loading?: boolean
}>(), {
  loading: false
})
</script>
```

### 3. v-model mit defineModel (Vue 3.4+)
```vue
<script setup lang="ts">
const modelValue = defineModel<boolean>()
</script>
```

### 4. Composables für Logik
Component-Logik in Composables auslagern, wenn sie:
- > 100 Zeilen Script hat
- Wiederverwendbar sein soll
- Unit-Tests braucht

### 5. Slots für Flexibilität
```vue
<template>
  <div class="wrapper">
    <slot name="header" />
    <slot />
    <slot name="footer" />
  </div>
</template>
```

## Index-Dateien

Jedes Komponenten-Verzeichnis sollte eine `index.ts` haben:

```typescript
// components/common/index.ts
export { default as PageHeader } from './PageHeader.vue'
export { default as FilterCard } from './FilterCard.vue'
// ...
```

## Styling

- Vuetify 3 als UI-Framework
- Material Design Icons (mdi-*)
- CSS Custom Properties für Theme-Werte
- Scoped Styles in Components
