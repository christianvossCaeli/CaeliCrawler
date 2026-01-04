# Audit: Datenquellen-Modul (Data Sources)

**Datum:** 04.01.2026  
**Bereich:** Sources-Verwaltung (Frontend & Backend)  
**Scope:** UX/UI, Best Practices, Modularität, Code-Qualität, State of the Art

---

## 1. Executive Summary

Das Datenquellen-Modul ist **sehr gut strukturiert** und folgt modernen Best Practices. Die Architektur ist modular, der Code gut dokumentiert und typisiert. Es gibt nur wenige Verbesserungsmöglichkeiten.

### Bewertung

| Kategorie | Bewertung | Anmerkungen |
|-----------|-----------|-------------|
| **UX/UI** | ⭐⭐⭐⭐½ (4.5/5) | Excellente Accessibility, responsive Design |
| **Best Practices** | ⭐⭐⭐⭐⭐ (5/5) | Composition API, TypeScript, Debouncing |
| **Modularität** | ⭐⭐⭐⭐⭐ (5/5) | Hervorragende Komponenten-Aufteilung |
| **Code-Qualität** | ⭐⭐⭐⭐½ (4.5/5) | Sauberer Code, gute Typisierung |
| **State of the Art** | ⭐⭐⭐⭐⭐ (5/5) | Vue 3.5+, Pinia, VueUse |

---

## 2. Architektur-Übersicht

### 2.1 Frontend-Struktur

```
frontend/src/
├── views/
│   └── SourcesView.vue              # Hauptview
├── components/sources/
│   ├── index.ts                     # Barrel-Export
│   ├── SourceFormDialog.vue         # Erstellen/Bearbeiten
│   ├── SourcesSidebar.vue           # Filter-Navigation
│   ├── SourcesBulkImportDialog.vue  # CSV-Import
│   ├── ApiImportDialog.vue          # API-Import
│   ├── AiDiscoveryDialog.vue        # KI-Discovery
│   ├── SharePointConfig.vue         # SharePoint-Integration
│   ├── SourcesActiveFilters.vue     # Aktive Filter
│   ├── SourcesTableActions.vue      # Tabellen-Aktionen
│   ├── SourcesSkeleton.vue          # Loading-State
│   ├── SourcesDeleteDialog.vue      # Lösch-Dialog
│   ├── CategoryInfoDialog.vue       # Kategorie-Info
│   ├── chips/                       # Wiederverwendbare Chips
│   │   ├── SourceTypeChip.vue
│   │   ├── SourceStatusChip.vue
│   │   ├── TagChip.vue
│   │   └── ConfidenceChip.vue
│   ├── source-form/                 # Formular-Sektionen
│   │   ├── SourceFormBasicInfo.vue
│   │   ├── SourceFormCategories.vue
│   │   ├── SourceFormEntityLinking.vue
│   │   ├── SourceFormCrawlSettings.vue
│   │   └── SourceFormTags.vue
│   └── ai-discovery/                # KI-Discovery-Phasen
│       ├── AiDiscoveryInputPhase.vue
│       ├── AiDiscoverySearchingPhase.vue
│       ├── AiDiscoveryWebResults.vue
│       ├── AiDiscoveryApiResults.vue
│       └── AiDiscoveryValidations.vue
├── stores/
│   └── sources.ts                   # Pinia Store (~790 Zeilen)
├── composables/
│   └── useSourceHelpers.ts          # Helper-Composable
├── types/
│   └── sources.ts                   # TypeScript-Definitionen (~730 Zeilen)
├── config/
│   └── sources.ts                   # Zentralisierte Konfiguration
└── services/api/
    └── sources.ts (in admin.ts)     # API-Client
```

### 2.2 Backend-Struktur

```
backend/
├── app/api/admin/
│   └── sources.py                   # API-Endpoints (~600 Zeilen)
├── app/models/
│   ├── data_source.py               # SQLAlchemy Model
│   └── data_source_category.py      # N:M Junction Table
└── app/schemas/
    └── data_source.py               # Pydantic Schemas
```

---

## 3. Stärken (Best Practices)

### 3.1 Moderne Vue 3.5+ Features

✅ **defineModel()** für Two-Way-Binding (SourceFormDialog.vue:414-418)
```typescript
const dialogOpen = defineModel<boolean>({ default: false })
const formData = defineModel<DataSourceFormData>('formData', { required: true })
```

✅ **Composition API** durchgehend verwendet
✅ **Script Setup** für alle Komponenten
✅ **Storetoref** für reaktive Store-Referenzen

### 3.2 State Management (Pinia)

✅ **Zentralisierter Store** mit klarer Struktur:
- State
- Computed Properties
- Actions (gruppiert nach Domäne)
- Utility Functions

✅ **Optimistic Updates** bei CRUD-Operationen
✅ **Error Handling** via `withApiErrorHandling` Utility
✅ **Loading States** pro Action/Ressource

### 3.3 Performance-Optimierungen

✅ **Lazy Loading** für schwere Dialog-Komponenten:
```typescript
const SourceFormDialog = defineAsyncComponent({
  loader: () => import('@/components/sources/SourceFormDialog.vue'),
  delay: 200,
})
```

✅ **Debouncing** mit VueUse:
```typescript
const debouncedSearch = useDebounceFn(() => {
  store.fetchSources(1)
}, SEARCH.DEBOUNCE_MS)
```

✅ **Bulk-Loading** im Backend zur Vermeidung von N+1 Queries:
```python
categories_by_source = await get_categories_for_sources_bulk(session, source_ids)
```

### 3.4 Accessibility (A11y)

✅ **ARIA-Attribute** durchgehend:
```vue
<v-navigation-drawer
  role="navigation"
  :aria-label="$t('sources.sidebar.navigation')"
>
```

✅ **Keyboard-Navigation**:
```typescript
if (e.key === 'Escape') close()
if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) save()
```

✅ **Semantische HTML-Struktur** mit korrekten Rollen

### 3.5 TypeScript-Integration

✅ **Vollständige Typisierung** aller Interfaces
✅ **Type Guards** für Runtime-Validierung:
```typescript
export function isSourceType(value: unknown): value is SourceType
export function isSourceStatus(value: unknown): value is SourceStatus
```

✅ **Re-Exports** für zentrale Error-Handling-Utils

### 3.6 Zentralisierte Konfiguration

✅ **Magic Numbers vermieden** durch `config/sources.ts`:
```typescript
export const SOURCES_PAGINATION = {
  ITEMS_PER_PAGE: 50,
  CATEGORIES_PER_PAGE: 100,
}
export const ENTITY_SEARCH = {
  MIN_QUERY_LENGTH: 2,
  DEBOUNCE_MS: 300,
}
```

### 3.7 Internationalisierung

✅ **vue-i18n** für alle Texte
✅ **Separate Locale-Dateien** (de/en)
✅ **Fallback-Strategien** bei fehlenden Übersetzungen

---

## 4. UX/UI-Bewertung

### 4.1 Positive Aspekte

✅ **Responsive Sidebar** mit Collapse-Funktion
✅ **Filter-Persistenz** via URL-Query-Parameter
✅ **Empty States** mit kontextabhängigen Actions
✅ **Error Boundaries** für Dialog-Fehlerbehandlung
✅ **Snackbar-Feedback** für User-Aktionen
✅ **Loading Skeletons** für bessere perceived Performance
✅ **Progressive Disclosure** (Show More/Less für Kategorien/Tags)

### 4.2 Feature-Highlights

| Feature | Implementierung |
|---------|-----------------|
| Multi-Select Kategorien | N:M Relationship, Chips mit Primary-Marker |
| Tag-System | Autocomplete, farbcodierte Tags |
| Entity-Linking | Debounced Search, N:M |
| Bulk Import | CSV-Parser, Preview, Duplikat-Erkennung |
| AI Discovery | Mehrstufiger Wizard, Template-Speicherung |
| SharePoint | Connection Test, Drive-Auswahl |

### 4.3 Verbesserungsmöglichkeiten (Minor)

⚠️ **Sidebar Keyboard-Focus**: Tab-Fokus könnte optimiert werden
⚠️ **Table Column Resizing**: Wäre nice-to-have
⚠️ **Drag & Drop** für Prioritäten-Sortierung fehlt

---

## 5. Modularität

### 5.1 Komponenten-Aufteilung: ⭐⭐⭐⭐⭐

Die Aufteilung ist **exemplarisch**:

- **Smart Components** (Container): `SourcesView.vue`
- **Presentational Components**: Sidebar, TableActions, Chips
- **Form Components**: Aufgeteilt nach Sektionen
- **Dialog Components**: Separate Files mit Lazy Loading

### 5.2 Wiederverwendbarkeit

✅ **Chip-Komponenten** werden projektübergreifend genutzt
✅ **Composables** (`useSourceHelpers`) kapseln wiederverwendbare Logik
✅ **Zentrale Error-Handling-Utils** werden re-exportiert

### 5.3 Barrel-Exports

✅ Saubere `index.ts` Dateien für alle Unterordner

---

## 6. Code-Qualität

### 6.1 Positiv

✅ **JSDoc-Kommentare** für komplexe Funktionen
✅ **Klare Strukturierung** mit Sektions-Kommentaren
✅ **Konsistente Namenskonventionen**
✅ **Error Messages** sind lokalisiert
✅ **Security**: LIKE-Escape im Backend für SQL-Injection-Schutz:
```python
escaped_search = search.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
```

### 6.2 Verbesserungswürdig (Minor)

⚠️ `sources.ts` Store ist mit ~790 Zeilen am oberen Ende - könnte in Module aufgeteilt werden:
- `sourcesCrudStore`
- `sourcesBulkImportStore`  
- `sourcesEntityLinkStore`

⚠️ Einige computed Properties in `SourcesSidebar.vue` könnten in ein Composable extrahiert werden

---

## 7. Backend-Qualität

### 7.1 API-Design

✅ **RESTful** Struktur
✅ **Pagination** mit flexiblen Parametern
✅ **Bulk-Endpoints** für Massenoperationen
✅ **Meta-Endpoints** für Counts/Stats
✅ **URL-Validierung** gegen Crawler-Missbrauch:
```python
BLOCKED_CRAWLER_IP_RANGES = [...]
BLOCKED_HOSTNAMES = ['localhost', '127.0.0.1', ...]
```

### 7.2 Datenmodell

✅ **N:M Beziehungen** korrekt implementiert mit Junction Table
✅ **JSONB** für flexible Konfiguration
✅ **Indizes** auf häufig abgefragten Spalten
✅ **Unique Constraints** für base_url

---

## 8. Empfehlungen

### 8.1 Kurzfristig (Quick Wins)

1. ~~Keine kritischen Issues gefunden~~

### 8.2 Mittelfristig

1. **Store-Splitting**: Den `sources.ts` Store in kleinere Module aufteilen
2. **Virtual Scrolling**: Für sehr große Tabellen (>1000 Einträge)
3. **Optimistic UI**: Für Bulk-Operationen erweitern

### 8.3 Langfristig

1. **GraphQL**: Für komplexe verschachtelte Abfragen evaluieren
2. **Real-time Updates**: WebSocket für Crawler-Status

---

## 9. Fazit

Das Datenquellen-Modul ist **production-ready** und folgt modernen Best Practices. Die Architektur ist sauber, der Code gut wartbar. Es dient als **Referenzimplementierung** für andere Module.

### Gesamtbewertung: ⭐⭐⭐⭐⭐ (4.8/5)

**Stärken:**
- Excellente Modularität
- Moderne Vue 3.5+ Features
- Gute Accessibility
- Umfassende TypeScript-Integration
- Performante Implementierung

**Verbesserungspotenzial:**
- Store-Größe optimieren
- Einige Minor UX-Verbesserungen

---

## 10. Dateiliste

### Frontend (Wichtigste)
- `frontend/src/views/SourcesView.vue` (815 Zeilen)
- `frontend/src/stores/sources.ts` (788 Zeilen)
- `frontend/src/types/sources.ts` (730 Zeilen)
- `frontend/src/components/sources/SourceFormDialog.vue` (586 Zeilen)
- `frontend/src/components/sources/SourcesSidebar.vue` (374 Zeilen)
- `frontend/src/composables/useSourceHelpers.ts` (346 Zeilen)
- `frontend/src/config/sources.ts` (159 Zeilen)

### Backend (Wichtigste)
- `backend/app/api/admin/sources.py` (~600 Zeilen)
- `backend/app/models/data_source.py` (201 Zeilen)
- `backend/app/schemas/data_source.py` (308 Zeilen)
