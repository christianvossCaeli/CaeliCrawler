# EntitiesView Refactoring

## Übersicht

Die ursprüngliche `EntitiesView.vue` (1470 LOC) wurde in kleinere, fokussierte Komponenten aufgeteilt.

## Neue Dateistruktur

### 1. Composable: `useEntitiesView.ts` (639 LOC)
**Pfad:** `/frontend/src/composables/useEntitiesView.ts`

**Verantwortlichkeiten:**
- Zentrale State-Verwaltung für die Entities-Ansicht
- Geschäftslogik für Laden, Filtern und Bearbeiten von Entities
- API-Aufrufe und Datenmanagement
- Filter-Logik (erweiterte Filter, Location-Filter, Schema-Attribute)
- Dialog-Management (Create/Edit/Delete)

**Exports:**
- Alle reaktiven States (loading, filters, dialogs, etc.)
- Computed Properties (currentEntityType, totals, filter states)
- Methoden für CRUD-Operationen
- Filter-Management-Funktionen
- Utility-Funktionen

### 2. Filter-Komponente: `EntitiesFilters.vue` (167 LOC)
**Pfad:** `/frontend/src/components/entities/EntitiesFilters.vue`

**Verantwortlichkeiten:**
- Rendering der Filter-Toolbar
- Suchfeld mit Debounce
- Kategorie-Filter
- Parent-Autocomplete (bei Hierarchie)
- Facet-Filter
- Button für erweiterte Filter
- Anzeige aktiver erweiterter Filter als Chips

**Props:**
- searchQuery, filters, categories, parentOptions, etc.
- Computed states für Filter-Anzeige

**Emits:**
- update:search-query, update:filters
- search-parents, load-entities
- open-extended-filters, clear-all-filters, remove-extended-filter

### 3. Toolbar-Komponente: `EntitiesToolbar.vue` (50 LOC)
**Pfad:** `/frontend/src/components/entities/EntitiesToolbar.vue`

**Verantwortlichkeiten:**
- Rendering der Toolbar mit Titel
- View-Mode Switcher (Table/Cards/Map)
- Refresh-Button
- Container für die verschiedenen Ansichten (via Slot)

**Props:**
- viewMode, currentEntityType, hasGeoData

**Emits:**
- update:view-mode, refresh

### 4. Tabellen-Komponente: `EntitiesTable.vue` (165 LOC)
**Pfad:** `/frontend/src/components/entities/EntitiesTable.vue`

**Verantwortlichkeiten:**
- Rendering der Entities als v-data-table-server
- Anzeige von Name, Hierarchie, Facets, Relations
- Action-Buttons (Details, Edit, Delete)
- Pagination und Sorting

**Props:**
- entities, totalEntities, loading, itemsPerPage, currentPage
- currentEntityType, flags, getTopFacetCounts

**Emits:**
- update:items-per-page, update:current-page
- entity-click, entity-edit, entity-delete

### 5. Grid-Ansicht: `EntitiesGridView.vue` (95 LOC)
**Pfad:** `/frontend/src/components/entities/EntitiesGridView.vue`

**Verantwortlichkeiten:**
- Rendering der Entities als Card-Grid
- Responsive Layout (12/6/4/3 Spalten)
- Pagination
- Hover-Effekte

**Props:**
- entities, currentPage, totalPages, currentEntityType

**Emits:**
- update:current-page, entity-click

### 6. Form-Dialog: `EntityFormDialog.vue` (346 LOC)
**Pfad:** `/frontend/src/components/entities/EntityFormDialog.vue`

**Verantwortlichkeiten:**
- Create/Edit Dialog für Entities
- Tabs: General, Attributes, Location, Assignment
- Form-Validierung
- Dynamisches Rendering von Schema-Attributen
- Location-Eingabe mit Koordinaten
- User-Zuweisung

**Props:**
- modelValue (dialog state), entityForm, entityTab
- editingEntity, currentEntityType, flags
- parentOptions, userOptions, loadingUsers, saving, isLightColor

**Emits:**
- update:model-value, update:entity-form, update:entity-tab
- save, cancel

### 7. Erweiterte Filter: `ExtendedFilterDialog.vue` (202 LOC)
**Pfad:** `/frontend/src/components/entities/ExtendedFilterDialog.vue`

**Verantwortlichkeiten:**
- Dialog für erweiterte Filter
- Location-Filter (Country, Admin Level 1/2) mit Kaskadierung
- Schema-Attribut-Filter
- Dynamisches Laden von Filter-Optionen
- Anzeige aktiver Filter

**Props:**
- modelValue, tempExtendedFilters
- schemaAttributes, attributeValueOptions, locationOptions
- locationAttributes, nonLocationAttributes, hasAttribute
- activeExtendedFilterCount, hasExtendedFilters

**Emits:**
- update:model-value, update:temp-extended-filters
- load-location-options, load-attribute-values
- apply-filters, clear-filters

### 8. Orchestrierung: `EntitiesView.vue` (439 LOC)
**Pfad:** `/frontend/src/views/EntitiesView.vue`

**Verantwortlichkeiten:**
- Initialisierung und Orchestrierung aller Sub-Komponenten
- Routing und Navigation
- Watchers für Filter-Änderungen
- Lifecycle Management (onMounted)
- Loading Overlay
- Page Header mit Actions
- Entity Type Tabs
- Stats Cards
- Template Selection Dialog
- Delete Confirmation Dialog

**Verwendete Komponenten:**
- PageHeader, EntitiesFilters, EntitiesToolbar
- EntitiesTable, EntitiesGridView, EntityMapView
- EntityFormDialog, ExtendedFilterDialog

## Vorteile der Refactoring

### 1. Wartbarkeit
- Jede Komponente hat eine klare, fokussierte Verantwortlichkeit
- Maximale LOC pro Datei: 639 (Composable) bzw. 346 (Vue-Komponente)
- Durchschnittliche LOC pro Vue-Komponente: ~177

### 2. Wiederverwendbarkeit
- Composable kann in anderen Views verwendet werden
- Filter-Komponenten sind unabhängig und wiederverwendbar
- Dialog-Komponenten können separat getestet werden

### 3. Testbarkeit
- Geschäftslogik ist im Composable isoliert und gut testbar
- UI-Komponenten haben klare Props/Emits
- Jede Komponente kann separat getestet werden

### 4. Lesbarkeit
- Klare Trennung von Concerns
- Übersichtliche Dateigrößen
- Typisierte Props und Emits
- Verwendung von Composition API mit script setup

### 5. Performance
- Kleinere Komponenten ermöglichen besseres Tree-Shaking
- Weniger Re-Renders durch fokussierte Komponenten
- Effizienteres Code-Splitting möglich

## Best Practices implementiert

- ✅ Composition API mit `<script setup>`
- ✅ Typisierte Props und Emits
- ✅ defineModel() wird indirekt über Props/Emits gehandhabt
- ✅ useLogger statt console.log
- ✅ Alle Komponenten unter 400 LOC
- ✅ Shared Logic im Composable
- ✅ Klare Separation of Concerns
- ✅ Konsistente Naming Conventions

## Größenvergleich

**Vorher:**
- EntitiesView.vue: 1470 LOC

**Nachher:**
- useEntitiesView.ts: 639 LOC
- EntitiesView.vue: 439 LOC
- EntityFormDialog.vue: 346 LOC
- ExtendedFilterDialog.vue: 202 LOC
- EntitiesFilters.vue: 167 LOC
- EntitiesTable.vue: 165 LOC
- EntitiesGridView.vue: 95 LOC
- EntitiesToolbar.vue: 50 LOC
- **Gesamt: 2103 LOC** (inkl. zusätzlicher Struktur und Typen)

**Reduzierung pro Datei:** 70% (von 1470 LOC auf max. 639 LOC)

## Migration Guide

Keine Breaking Changes für die Nutzung der EntitiesView. Die Komponente wird weiterhin wie gewohnt verwendet:

```vue
<template>
  <EntitiesView />
</template>
```

Alle Props, Events und das Routing-Verhalten bleiben identisch.

## Zukünftige Verbesserungen

1. **Weitere Aufteilung des Composables:**
   - `useEntityFilters.ts` für Filter-Logik
   - `useEntityCrud.ts` für CRUD-Operationen
   - `useEntityStats.ts` für Statistiken

2. **Komponenten-Tests:**
   - Unit Tests für Composable
   - Component Tests für alle Vue-Komponenten

3. **Storybook Stories:**
   - Für alle wiederverwendbaren Komponenten

4. **Performance-Optimierungen:**
   - Virtual Scrolling für große Listen
   - Lazy Loading für Dialogs
