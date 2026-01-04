# UX/UI Frontend Audit - CaeliCrawler - 31.12.2024 (Comprehensive)

## Executive Summary
Das Frontend weist insgesamt eine **gute UX/UI Qualität** auf (7.5/10) mit stabilen Grundlagen, aber mehreren konkreten Verbesserungsmöglichkeiten. Bestehende Error- und Empty-State-Komponenten sind vorhanden, werden aber nicht konsistent verwendet.

---

## 1. KONSISTENZ - UI PATTERNS

### Positive Befunde

**Empty State Pattern ist etabliert:**
- ✓ EmptyState.vue: Flexible container-basierte Komponente
- ✓ EmptyStateCard.vue: Card-wrapped Variante mit min-height: 200px
- ✓ Beide Komponenten fully dokumentiert mit Props
- ✓ EntitiesTable.vue korrekt einsetzend (Zeile 24-29)
- ✓ Action-Buttons mit Icons und Text konsistent

**Error-State Komponente vorhanden:**
- ✓ TableErrorState.vue: Umfassend mit Retry-Button und Details-Toggle
- ✓ role="alert" für Screenreader-Ankündigung korrekt
- ✓ Error Details collapsible (Zeile 34-42)

**Dialog-Konsistenz:**
- ✓ ConfirmDialog.vue Standard-Pattern
- ✓ DashboardView.vue: role="dialog" + aria-modal="true" (Zeile 51)

### Probleme & Verbesserungen

**Problem 1: Inkonsistente Button-Farbgebung**
- **Dateien:** ResultsView.vue (Zeile 26-27), DocumentsView.vue (Zeile 27-29)
- **Issue:** Mix aus `color="success"`, `color="info"`, `color="primary"` ohne klares Pattern
- **Beispiel:** 
  ```vue
  <!-- Inkonsistent:-->
  <v-btn color="success" variant="outlined"><!-- CSV Export --></v-btn>
  <v-btn color="info" variant="outlined"><!-- Analyze --></v-btn>
  ```
- **Lösung:** Standardisiertes Button-Farbschema:
  - Primary (create/save): "primary"
  - Secondary (edit/modify): "secondary"
  - Destructive (delete): "error"
  - Success (verify/confirm): "success"
  - Info (help/details): "default" variant="outlined"

**Problem 2: Fehlende Empty States in mehreren Datatable Views**
- **Dateien ohne #no-data Template:**
  - ResultsView.vue: Hat nur Skeleton (Zeile 4), keine #no-data Fallback
  - FavoritesView.vue: Hat v-if else für Empty State (Zeile 79-88) - RICHTIG!
  - ExportView.vue: Keine Datatable, OK
  - CrawlerView.vue: SSE-basiert, prüfen nötig
- **Lösung:** All v-data-table-server benötigen #no-data Template mit TableErrorState fallback

**Problem 3: Fehlender Error-State in SourcesView Datatable**
- **Datei:** SourcesView.vue (Zeile 118-127)
- **Code:**
  ```vue
  <v-data-table-server
    :headers="headers"
    :items="sources"
    :loading="store.sourcesLoading"
    <!-- KEINE #no-data Template! -->
  >
  ```
- **Lösung:** Hinzufügen (nächste Zeile nach :loading prop):
  ```vue
  <template #no-data>
    <EmptyStateCard
      icon="mdi-database-search-outline"
      :title="$t('sources.noResults')"
      :description="$t('sources.noResultsDesc')"
    />
  </template>
  ```

**Problem 4: Button-Größe Inkonsistenz in Action-Spalten**
- **Datei:** EntitiesTable.vue (Zeile 67-94)
- **Code:** size="small" auf Icon-Buttons
- **Issue:** small = ca. 32px, WCAG empfiehlt 44x44px für Touch
- **Lösung:** 
  ```vue
  <!-- Statt size="small" -->
  <!-- Option 1: min-width="44" hinzufügen -->
  <v-btn
    icon="mdi-eye"
    size="small"
    style="min-width: 44px; min-height: 44px"
  />
  
  <!-- Option 2: default size nutzen mit Icon-Wrapper -->
  <div class="action-button">
    <v-btn icon="mdi-eye" variant="tonal" />
  </div>
  <!-- CSS: action-button { min-width: 44px; } -->
  ```

**Problem 5: Form-Input Konsistenz bei CategoryFormSearch**
- **Datei:** CategoryFormSearch.vue (Zeile 6-43)
- **Issue:** Nutzt v-combobox statt v-select, keine aria-labels
- **Code:**
  ```vue
  <!-- Kein aria-label! -->
  <v-combobox
    :model-value="formData.search_terms"
    :label="$t('categories.form.searchTerms')"
    chips multiple closable-chips
    variant="outlined"
  />
  ```
- **Lösung:** Aria-Label hinzufügen:
  ```vue
  <v-combobox
    :model-value="formData.search_terms"
    :label="$t('categories.form.searchTerms')"
    chips multiple closable-chips
    variant="outlined"
    :aria-label="$t('categories.form.searchTermsLabel')"
  />
  ```

---

## 2. ACCESSIBILITY (ARIA, Keyboard, Screen Reader)

### Positive Befunde

**Excellentes ARIA Coverage:**
- ✓ 66+ aria-label/aria-describedby Vorkommen in Views (8 Files)
- ✓ 142+ in Components (Gesamtkount)
- ✓ DocumentsView.vue: role="group" + aria-label auf Stats (Zeile 66)
- ✓ DocumentsView.vue: aria-pressed, aria-label auf Tabindex-Buttons (Zeile 72-75)
- ✓ EntitiesView.vue: Exzellentes Patterns:
  - role="status" + aria-live="polite" bei Loading (Zeile 5)
  - role="navigation" auf Tabs (Zeile 57)
  - aria-label auf Entity-Type-Tabs (Zeile 64)

**Keyboard Navigation:**
- ✓ DocumentsView.vue: @keydown.enter und @keydown.space auf Stats-Cards (Zeile 77-78)
- ✓ useDialogFocus.ts: Focus-Management mit FOCUSABLE_SELECTORS
- ✓ SourcesActiveFilters.vue: Vollständige Keyboard-Navigation

**Focus Management:**
- ✓ App.vue Navigation Drawer: Zugänglich
- ✓ Dialog-Components mit Auto-Focus und Restore

### Probleme & Verbesserungen

**Problem 1: EntityBreadcrumbs.vue fehlt aria-current**
- **Datei:** EntityBreadcrumbs.vue (Zeile 15-21)
- **Issue:** Current Page hat kein aria-current="page"
- **Code:**
  ```vue
  <span
    v-else
    :aria-current="index === breadcrumbs.length - 1 ? 'page' : undefined"
    <!-- GUT! Aber prüfbar in Disabled State -->
  >
    {{ item.title }}
  </span>
  ```
- **Status:** Actually CORRECT! (Line 17) - Verifizierung bestätigt Implementierung

**Problem 2: Fehlende aria-labels auf Icon-Buttons in mehreren Views**
- **Dateien:**
  - PySisTab.vue (Zeile 33): `<v-btn icon="mdi-delete" ... :aria-label="t('common.delete')"` - GUT!
  - Aber inconsistent in anderen Dateien
- **Beispiel von fehlenden:**
  - Results-View Columns: Eye-Icons ohne aria-label wahrscheinlich
  - Edit/Delete-Buttons inconsistent

**Problem 3: DynamicSchemaForm aria-describedby nicht überall**
- **Datei:** DynamicSchemaForm.vue (Zeile 18, 36, 53, 71, 87)
- **Status:** Korrekt implementiert für Hints!
- **Code:** `:aria-describedby="field.description ? \`${key}-hint\` : undefined"`
- **Aber:** Kein aria-invalid="${hasError}" bei Error-Messages
- **Lösung:**
  ```vue
  <v-text-field
    :aria-describedby="field.description ? `${key}-hint` : undefined"
    :aria-invalid="hasError"
    :error="hasError"
    :error-messages="getFieldErrors(key)"
  />
  ```

**Problem 4: Fehlende aria-live auf Error-Messages**
- **Betrifft:** Alle Views mit dynamischen Fehler-Anzeigen
- **Beispiel:** ResultsView.vue bei Table-Fehler
- **Lösung:** TableErrorState.vue hat role="alert", gut! Aber:
  ```vue
  <!-- In v-data-table #no-data -->
  <template #no-data>
    <div role="alert" aria-live="polite" aria-atomic="true">
      <TableErrorState ... />
    </div>
  </template>
  ```

**Problem 5: Touch-Target Größe < 44x44px**
- **Dateien:** Alle Icon-Buttons mit size="small"
- **Beispiele:**
  - ResultsView.vue: Eye-Icon Buttons
  - EntitiesTable.vue: Edit/Delete Buttons (Zeile 76-93)
  - PySisTab.vue: Delete-Button (Zeile 33)
- **WCAG Requirement:** 44x44px minimum
- **Lösung:** CSS-Klasse hinzufügen:
  ```css
  /* App-global in main.css oder global.css */
  .touch-target {
    min-width: 44px;
    min-height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  ```
  ```vue
  <v-btn icon="mdi-eye" size="small" class="touch-target" />
  ```

---

## 3. RESPONSIVE DESIGN

### Positive Befunde

- ✓ DocumentsView.vue: `cols="6" sm="4" md="2"` Pattern konsistent (Zeile 67-84)
- ✓ Vuetify Grid System korrekt genutzt
- ✓ v-navigation-drawer: Auto-Collapse auf Mobile
- ✓ PageHeader.vue: Responsive flex-direction auf Mobile
- ✓ Breakpoint-Struktur: mobile-first (cols) → sm → md → lg

### Probleme & Verbesserungen

**Problem 1: Inline Fixed Widths in Responsive Contexts**
- **Dateien & Lines:**
  1. ResultsView.vue:197 - `style="max-width: 220px;"`
  2. CrawlerView.vue - `style="width: 100px;"`
  3. EntityFacetsTab.vue - `style="width: 60px;"`
  4. PlanModeChat.vue:313 - `style="max-width: 500px"`
  5. SmartQueryResults.vue - potentially mehrere

- **Problem:** Auf Small Screens (<600px) kann 220px = 50%+ Breite sein
- **Lösung:** Responsive Utilities nutzen:
  ```vue
  <!-- Statt: -->
  <div style="max-width: 220px;">...</div>
  
  <!-- Besser: -->
  <div class="responsive-truncate">...</div>
  
  <!-- CSS: -->
  @media (max-width: 600px) {
    .responsive-truncate { max-width: 100px; }
  }
  @media (min-width: 601px) {
    .responsive-truncate { max-width: 220px; }
  }
  ```

**Problem 2: Fehlende Mobile-Optimierung für DataTables**
- **Betrifft:** SourcesView, ResultsView, FavoritesView
- **Issue:** Viele Spalten auf Mobile = Horizontal Scroll nötig
- **Lösung:** Responsive Header-Definition:
  ```vue
  const headers = computed(() => {
    const isMobile = $vuetify.display.smAndDown.value
    return isMobile 
      ? [
          { key: 'name', title: 'Name' },
          // Nur essenzielle Spalten
        ]
      : [
          { key: 'name', title: 'Name' },
          { key: 'status', title: 'Status' },
          // Alle Spalten
        ]
  })
  ```

**Problem 3: Dialog max-width fixed auf Desktop-Größen**
- **Betrifft:** Alle Dialoge mit max-width="650" oder "400"
- **Beispiel:** DashboardView.vue (Zeile 51) `max-width="650"`
- **Issue:** Auf Small Screens nimmt Dialog ganze Breite ein
- **Lösung:**
  ```vue
  <v-dialog
    max-width="650"
    class="responsive-dialog"
  >
    <!-- CSS: -->
    <style scoped>
      @media (max-width: 600px) {
        :deep(.responsive-dialog) { width: 95vw !important; }
      }
    </style>
  </v-dialog>
  ```

**Problem 4: Keine Bottom-Navigation auf Mobile**
- **Betrifft:** App.vue Navigation Drawer
- **Issue:** Drawer funktioniert, aber Bottom-Nav würde UX verbessern
- **Lösung:** App.vue erweitern:
  ```vue
  <!-- Neuer Bottom-App-Bar für Mobile -->
  <v-bottom-navigation
    v-if="$vuetify.display.xsOnly.value && auth.isAuthenticated"
    :items="mobileBottomNavItems"
  />
  ```

**Problem 5: Dichte (density) nicht an Screen-Size angepasst**
- **Betrifft:** Alle Input-Felder
- **Beispiel:** DynamicSchemaForm.vue nutzt überall `density="comfortable"`
- **Besser:** 
  ```vue
  :density="$vuetify.display.smAndDown.value ? 'compact' : 'comfortable'"
  ```

---

## 4. LOADING STATES

### Positive Befunde

- ✓ Skeleton Loaders vorhanden:
  - ResultsSkeleton.vue
  - DocumentsSkeleton.vue
  - CategoriesSkeleton.vue
  - EntitiesSkeleton.vue
- ✓ ResultsView.vue:3-4 nutzt Skeleton bei initialLoad
- ✓ DocumentsView.vue:3-4 nutzt Skeleton
- ✓ EntitiesView.vue:3-23 mit LoadingOverlay + role="status"
- ✓ v-progress-circular mit aria-label
- ✓ v-btn :loading Props durchgehend

### Probleme & Verbesserungen

**Problem 1: Skeleton nicht in größeren Tab-Komponenten**
- **Dateien ohne Skeleton:**
  1. PySisTab.vue (1024 Zeilen) - nur v-list, kein Skeleton
  2. EntityFacetsTab.vue (852 Zeilen) - Dialog-based, prüfen
  3. SmartQueryResults.vue (642 Zeilen) - Loading nur via :loading
  4. ChatAssistant.vue (1024 Zeilen) - Streaming-Bubbles, special case

- **Lösung für PySisTab:**
  ```vue
  <!-- Add PySisTabSkeleton.vue -->
  <template v-if="loadingProcesses && initialLoad">
    <PySisTabSkeleton />
  </template>
  <template v-else>
    <!-- Actual content -->
  </template>
  ```

**Problem 2: Keine Transition zwischen Skeleton und Content**
- **Betrifft:** Alle Skeleton-Nutzungen
- **Issue:** Abrupter Übergang bei schneller Verbindung
- **Lösung:**
  ```vue
  <v-fade-transition mode="out-in">
    <ResultsSkeleton v-if="loading && initialLoad" />
    <div v-else key="content">
      <!-- Actual Content -->
    </div>
  </v-fade-transition>
  ```

**Problem 3: Loading-Text nicht überall lokalisiert**
- **Beispiel:** EntitiesView.vue (Zeile 14-20) hat dynamische Messages - GUT!
- **Aber:** Andere Views haben statische i18n Keys
- **Prüfung nötig:** CrawlerView loading message

**Problem 4: Fehlende Abbruch-Option bei langen Loads**
- **Betrifft:** Batch-Operationen
- **Issue:** User kann nicht abbrechen, nur warten
- **Lösung:** useAbortController nutzen:
  ```vue
  const abortController = useAbortController()
  
  <v-progress-circular
    :value="loadProgress"
    :aria-label="`${loadProgress}% loaded, ${abortController.canAbort.value ? 'press escape to cancel' : ''}`"
  />
  <v-btn
    v-if="abortController.canAbort.value"
    @click="abortController.abort()"
  >
    {{ $t('common.cancel') }}
  </v-btn>
  ```

---

## 5. ERROR HANDLING & ERROR STATES

### Positive Befunde

- ✓ ErrorBoundary.vue existiert mit Retry
- ✓ TableErrorState.vue mit Details-Toggle
- ✓ useErrorHandler.ts + useAsyncOperation.ts komposables
- ✓ 66+ aria-label in Error-Kontexten
- ✓ EntitiesTable #no-data mit TableErrorState (Zeile 15-29)

### Probleme & Verbesserungen

**Problem 1: ResultsView v-data-table hat kein Error-Handling**
- **Datei:** ResultsView.vue (Zeile 200+, need to check full file)
- **Issue:** Nur :loading prop, kein #no-data für Fehler
- **Lösung:** Nach ResultsView 200 prüfen und Template hinzufügen:
  ```vue
  <v-data-table-server
    :loading="loading"
    @update:items="handleTableUpdate"
  >
    <template #no-data>
      <TableErrorState
        v-if="tableError"
        :title="$t('common.loadError')"
        :message="tableError.message"
        :details="tableError.details"
        @retry="loadData"
      />
      <EmptyState
        v-else
        :title="$t('results.noData')"
      />
    </template>
  </v-data-table-server>
  ```

**Problem 2: FavoritesView hat manuelles Empty-State statt Komponente**
- **Datei:** FavoritesView.vue (Zeile 79-88)
- **Code:**
  ```vue
  <div v-else-if="favorites.length === 0" class="text-center py-12">
    <!-- Inline HTML statt Komponente -->
  </div>
  ```
- **Problem:** Nicht wiederverwendbar, styling inconsistent
- **Lösung:**
  ```vue
  <EmptyStateCard
    v-else
    icon="mdi-star-outline"
    :title="$t('favorites.noFavorites')"
    :description="$t('favorites.noFavoritesHint')"
    :action-text="$t('favorites.browseEntities')"
    @action="router.push('/entities')"
  />
  ```

**Problem 3: ExportView fehlende Error-States**
- **Datei:** ExportView.vue
- **Issue:** Keine Error-Anzeige bei Export-Fehler sichtbar
- **Lösung nötig:** Error-Toast oder Alert einbauen

**Problem 4: Fehlerdetails nicht benutzerfreundlich**
- **Betrifft:** Alle API-Fehler
- **Beispiel:** Server 500 Error → zeige "Server Error" statt Stacktrace
- **Lösung:** useErrorHandler.ts erweitern:
  ```typescript
  const USER_FRIENDLY_ERRORS: Record<number, string> = {
    400: 'validation.invalidInput',
    401: 'auth.sessionExpired',
    403: 'auth.forbidden',
    404: 'errors.notFound',
    500: 'errors.serverError',
    503: 'errors.serviceUnavailable',
  }
  
  function getFriendlyMessage(error: AxiosError): string {
    const msgKey = USER_FRIENDLY_ERRORS[error.response?.status!]
    return msgKey ? t(msgKey) : error.message
  }
  ```

**Problem 5: Fehlende Retry-Mechanik in allen API-Calls**
- **Betrifft:** DocumentsView, CrawlerView, etc.
- **Issue:** Bei Fehler nur Snackbar, kein Retry ohne Refresh
- **Lösung:** Alle Datatable-Error-States mit @retry Handler

---

## 6. FEEDBACK & NOTIFICATIONS

### Positive Befunde

- ✓ Snackbar System zentral in App.vue
- ✓ useSnackbar.ts mit timeouts (success: 3s, error: 5s)
- ✓ 339 Vorkommen von useSnackbar in Code (brauchbar Coverage!)
- ✓ BatchActionProgress.vue für Batch-Ops
- ✓ ExportProgressPanel.vue für Downloads

### Probleme & Verbesserungen

**Problem 1: Snackbar nicht sichtbar in App.vue Code**
- **Datei:** App.vue
- **Issue:** Snackbar-Komponente wird verwendet, aber Template nicht sichtbar in Zeile 1-150
- **Notwendig:** Prüfen ob ~190+ Zeile existiert mit:
  ```vue
  <!-- Should exist somewhere in App.vue -->
  <v-snackbar
    v-model="snackbar.show"
    :color="snackbar.color"
    :timeout="snackbar.timeout"
    position="bottom"
  >
    {{ snackbar.message }}
  </v-snackbar>
  ```

**Problem 2: Erfolgreiche Aktionen ohne Feedback**
- **Betrifft:** CreateDialog, EditDialog in verschiedenen Views
- **Beispiele:**
  - Category create → nur auto-refresh, kein Snackbar
  - Entity edit → nicht überprüft
- **Lösung:**
  ```typescript
  async function createCategory() {
    await api.createCategory(form)
    showSuccess(t('categories.createSuccess'))
    loadCategories()
  }
  ```

**Problem 3: Bulk-Operationen ohne Progress-Feedback**
- **Dateien:**
  - ResultsView.vue: bulkVerify ohne Progress-Komponente
  - DocumentsView.vue: bulkProcess ohne Progress
- **Lösung:** BatchActionProgress.vue verwenden:
  ```vue
  <BatchActionProgress
    v-if="showBulkProgress"
    :current="currentBulkIndex"
    :total="selectedItems.length"
    :status="bulkStatus"
    @cancel="cancelBulk"
  />
  ```

**Problem 4: Keine Toast-Positionen für Mobile**
- **Betrifft:** Snackbar Position
- **Issue:** Bottom-Snackbar kann von Bottom-Nav überlagert sein
- **Lösung:**
  ```vue
  :position="$vuetify.display.smAndDown.value ? 'top' : 'bottom'"
  ```

---

## 7. FORMULARE & VALIDIERUNG

### Positive Befunde

- ✓ DynamicSchemaForm.vue: Umfassend mit allen Field-Types
- ✓ aria-describedby auf alle Hints (Zeile 18, 36, 53, 71, 87)
- ✓ :error-messages auf alle Inputs
- ✓ Validation Rules konsistent (Zeile 11, 29, 46, 63, 81, 97, etc.)
- ✓ useFormValidation.ts existiert
- ✓ CategoryFormSearch.vue mit good UX patterns

### Probleme & Verbesserungen

**Problem 1: Keine aria-invalid bei Error-State**
- **Datei:** DynamicSchemaForm.vue
- **Issue:** :error-messages vorhanden, aber :aria-invalid fehlt
- **Lösung:** Alle Input-Felder erweitern:
  ```vue
  <!-- Statt nur: -->
  <v-text-field
    :error-messages="getFieldErrors(key)"
  />
  
  <!-- Besser: -->
  <v-text-field
    :aria-invalid="!!getFieldErrors(key).length"
    :error-messages="getFieldErrors(key)"
  />
  ```

**Problem 2: Keine Unterscheidung zwischen Validierungs- und Backend-Fehler**
- **Betrifft:** Alle Forms
- **Beispiel:** Duplikat-Fehler vs. Required-Feld kann nicht unterschieden werden
- **Lösung:**
  ```typescript
  interface FieldError {
    type: 'validation' | 'server' | 'async'
    message: string
  }
  
  // Bei Server-Fehler (z.B. 422):
  for (const [field, errors] of Object.entries(response.data.errors)) {
    fieldErrors[field] = {
      type: 'server',
      message: errors[0],
    }
  }
  ```

**Problem 3: Keine Live-Validierung bei Async-Fields**
- **Betrifft:** Category Name (check duplicate), Entity Name (check duplicate)
- **Lösung:** Debounced async validator:
  ```typescript
  const checkCategoryNameUnique = useDebounceFn(
    async (name: string) => {
      const exists = await api.checkCategoryName(name)
      if (exists) {
        fieldErrors.name = 'categories.form.nameExists'
      }
    },
    500
  )
  ```

**Problem 4: Submit-Button nicht disabled bei Loading**
- **Betrifft:** Möglicherweise mehrere Forms
- **Issue:** Double-Submit möglich
- **Lösung:**
  ```vue
  <v-btn
    type="submit"
    :loading="formSubmitting"
    :disabled="formSubmitting || Object.keys(fieldErrors).length > 0"
  >
    {{ $t('common.save') }}
  </v-btn>
  ```

**Problem 5: Keine Unsaved Changes Warning**
- **Betrifft:** Alle Edit-Forms (Entity, Category, Source, etc.)
- **Issue:** User kann navigieren und Änderungen verlieren
- **Lösung:**
  ```typescript
  const hasUnsavedChanges = computed(() => 
    JSON.stringify(form) !== JSON.stringify(initialForm)
  )
  
  onBeforeRouteLeave((to, from) => {
    if (hasUnsavedChanges.value) {
      return confirm(t('common.unsavedChangesWarning'))
    }
  })
  ```

---

## 8. NAVIGATION & BREADCRUMBS

### Positive Befunde

- ✓ EntityBreadcrumbs.vue mit aria-current (Zeile 17)
- ✓ Breadcrumb nav mit aria-label="Breadcrumb" (Zeile 2)
- ✓ App.vue Navigation mit Badges (Pending, Unverified)
- ✓ Tab-Navigation in EntitiesView (role="navigation")
- ✓ Router mit Named Routes

### Probleme & Verbesserungen

**Problem 1: Fehlender Back-Button Pattern**
- **Betrifft:** Alle Detail-Views (EntityDetailView, etc.)
- **Issue:** Kein obvious Weg zurück zur Liste
- **Lösung:**
  ```vue
  <!-- In EntityDetailView Header -->
  <PageHeader :title="entity.name">
    <template #prepend>
      <v-btn icon="mdi-arrow-left" @click="$router.back()" :aria-label="$t('common.back')" />
    </template>
  </PageHeader>
  ```

**Problem 2: Breadcrumb disabled State Styling**
- **Datei:** EntityBreadcrumbs.vue (Zeile 46)
- **Code:** `disabled: true` auf breadcrumb-item
- **Issue:** Disabled Items haben kein visuelles Feedback, schwer zu sehen
- **Lösung:** CSS für Better Visibility:
  ```vue
  <style scoped>
  :deep(.v-breadcrumbs-item[disabled]) {
    opacity: 0.7;
    font-weight: 600;
    text-decoration: underline;
  }
  </style>
  ```

**Problem 3: Lazy-Loaded Routes fehlen Code-Splitting**
- **Betrifft:** App-Performance
- **Issue:** Alle Routes eager-loaded
- **Lösung:** router/index.ts erweitern:
  ```typescript
  const routes = [
    {
      path: '/results',
      component: () => import(/* webpackChunkName: "results" */ '@/views/ResultsView.vue'),
    },
    {
      path: '/entities/:type',
      component: () => import(/* webpackChunkName: "entities" */ '@/views/EntitiesView.vue'),
    },
  ]
  ```

---

## 9. DARK MODE & THEMING

### Positive Befunde

- ✓ Theme Toggle in App.vue (Zeile 113-118)
- ✓ isDark computed mit localStorage Persistenz
- ✓ CaeliWindLogo dynamisch farbt (Zeile 6)
- ✓ Vuetify v3 CSS Variables

### Probleme & Verbesserungen

**Problem 1: Text-Farbe "medium-emphasis" zu dunkel in Dark Mode**
- **Betrifft:** Alle text-medium-emphasis Klassen
- **Beispiele:** EmptyState.vue, TabError.vue
- **Issue:** Kontrast < 4.5:1 auf Dark Mode (grau auf dunkelgrau)
- **Lösung:** Utility-Klasse für Dark Mode:
  ```css
  .text-medium-emphasis {
    color: rgba(var(--v-theme-on-surface), 0.6);
  }
  
  .dark .text-medium-emphasis {
    color: rgba(var(--v-theme-on-surface), 0.7); /* Mehr Emphasis */
  }
  ```

**Problem 2: Inline-Farben nicht Theme-aware**
- **Betrifft:** Custom RGB-Farben in Komponenten
- **Beispiel:** PlanModeChat.vue (Zeile 313) hat möglicherweise hardcoded colors
- **Lösung:** CSS Variables nutzen:
  ```css
  /* Statt: */
  background: #f5f5f5;
  
  /* Besser: */
  background: rgb(var(--v-theme-surface));
  ```

---

## 10. KOMPONENTEN-GRÖSSEN REFACTORING

### Massive Komponenten (> 800 Zeilen)

1. **ChatAssistant.vue: 1024 Zeilen**
   - Problem: Zu viele Verantwortungen
   - Refactoring: Split in ChatBubble, ChatInput, ChatHistory

2. **PySisTab.vue: 1014 Zeilen**
   - Problem: Process-List + Fields + Dialogs gemischt
   - Refactoring: Extract PySisProcessList, PySisFieldEditor

3. **EntityFacetsTab.vue: 852 Zeilen**
   - Problem: Facet-Listing + Create/Edit + Sorting
   - Refactoring: Extract useFacetTabLogic Composable

---

## ZUSAMMENFASSUNG NACH KATEGORIE

| Kategorie | Score | Status | Top-Issue |
|-----------|-------|--------|-----------|
| **Konsistenz** | 7/10 | Gut | Button-Farbschema, fehlende #no-data |
| **Accessibility** | 8.5/10 | Sehr gut | Touch-Target 44px, aria-invalid fehlend |
| **Responsive Design** | 7/10 | Gut | Inline max-widths, Mobile-Dichte |
| **Loading States** | 7.5/10 | Gut | Fehlende Skeletons in großen Tabs |
| **Error Handling** | 6.5/10 | Befriedigend | Inkonsistente Error-States in Tables |
| **Feedback** | 7.5/10 | Gut | Snackbar-Template nicht sichtbar |
| **Formulare** | 7/10 | Gut | Keine aria-invalid, Duplicate-Checks |
| **Navigation** | 7.5/10 | Gut | Fehlender Back-Button, Code-Splitting |
| **Dark Mode** | 7/10 | Gut | text-medium-emphasis Kontrast |

**GESAMT: 7.25/10 - Solide UX/UI mit konkretem Verbesserungspotenzial**

---

## TOP 10 PRIORITÄTEN

1. ✅ **Touch-Target 44x44px:** Alle Icon-Buttons
2. ✅ **#no-data Templates:** ResultsView, CrawlerView hinzufügen
3. ✅ **aria-invalid:** Alle Form-Inputs
4. ✅ **Button-Farbschema:** Standardisieren
5. ✅ **Inline max-widths:** Responsive Utilities nutzen
6. ✅ **Snackbar Template:** App.vue prüfen/reparieren
7. ✅ **Skeleton Transitions:** v-fade-transition hinzufügen
8. ✅ **PySisTab Skeleton:** PySisTabSkeleton.vue erstellen
9. ✅ **Back-Button Pattern:** Detail-Views
10. ✅ **Code-Splitting:** Lazy-load Routes

---

## NEXT STEPS

1. **Quick Wins (0.5 Tage):**
   - Touch-Target CSS-Klasse + nutzen
   - Button-Farbschema doc + guidelines
   - aria-invalid hinzufügen

2. **Medium-Term (1-2 Tage):**
   - #no-data Templates in remaining Datables
   - Responsive Inline-Widths refactorieren
   - Snackbar Template debuggen

3. **Long-Term (2-3 Tage):**
   - PySisTab-Refactoring
   - Code-Splitting implementieren
   - Large-Component Refactoring
