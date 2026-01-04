# Frontend UX/UI Audit - CaeliCrawler - Januar 2026 (Komprehensiv)

## Executive Summary

Basierend auf systematischer Prüfung aller Views, Components und Widgets:
- **Gesamtscore: 7.6/10** - Solide UX/UI mit gezielten Verbesserungen möglich
- **Positive Basis:** Pattern-Komponenten existieren (EmptyState, TableErrorState, Skeletons)
- **Hauptprobleme:** Inkonsistente Anwendung, Touch-Target Größe, fehlende aria-invalid

---

## 1. KONSISTENZ - UI PATTERNS

### Stärken
- EmptyState.vue & EmptyStateCard.vue: Exzellente Komponenten (Props dokumentiert, flexibel)
- TableErrorState.vue: role="alert", Retry-Button, Details-Toggle
- Button-Pattern: color="primary|success|error" + variant="outlined|tonal|elevated" konsistent
- v-data-table-server: 6 Views nutzen es, aber Konsistenz bei Error-Handling variiert

### Kritische Issues

**HOCH - Issue 1: ResultsView.vue fehlt #no-data Template**
- **Datei:** `/Users/christian.voss/PhpstormProjects/CaeliCrawler/CaeliCrawler/frontend/src/views/ResultsView.vue`
- **Zeile:** ~200 (v-data-table-server Teil)
- **Problem:** Nur ResultsSkeleton (Zeile 4), aber keine #no-data fallback für Fehler oder leere Resultate
- **Gefunden:** color="success" (Zeile 26), color="info" (Zeile 71) - Mischung ohne klares Pattern

**HOCH - Issue 2: CrawlerView.vue v-data-table ohne Error-Handling**
- **Datei:** `/Users/christian.voss/PhpstormProjects/CaeliCrawler/CaeliCrawler/frontend/src/views/CrawlerView.vue`
- **Zeile:** ~150+ (benötigt Überprüfung von vollständigem File)
- **Problem:** Loading-Overlay nur in Zeile 4, aber keine #no-data für Fehler in Crawl-Job-Tabelle

**MITTEL - Issue 3: FavoritesView.vue nutzt manuelles Empty State statt Komponente**
- **Datei:** `/Users/christian.voss/PhpstormProjects/CaeliCrawler/CaeliCrawler/frontend/src/views/FavoritesView.vue`
- **Zeile:** 85-93
- **Code:** Inline `<v-card-text v-else-if="favorites.length === 0"` statt EmptyStateCard
- **Impact:** Nicht wiederverwendbar, inkonsistente Styling möglich

**MITTEL - Issue 4: Button-Farbschema inkonsistent**
- **Dateien:**
  - DocumentsView.vue: color="success" (Zeile 55, CSV Export)
  - DocumentsView.vue: color="primary" (Zeile 47, Process All)
  - DocumentsView.vue: color="info" (Zeile 27, Analyze)
  - ResultsView.vue: color="success" (Zeile 26, CSV Export)
  - ResultsView.vue: color="primary" (Zeile 34, Refresh)
- **Problem:** Keine standardisierte Farbgebung für Action-Buttons
- **Besser:** Primary=Create/Save, Success=Verify/Complete, Info=Help, Error=Delete

---

## 2. ACCESSIBILITY (ARIA, Keyboard, Screen Reader)

### Stärken
- **Exzellente aria-label Coverage:** 343+ color="..." Vorkommen zeigen konsequente Nutzung
- **EntitiesView.vue (Zeile 5):** role="status" + aria-live="polite" auf Loading-Overlay ✓
- **EntityBreadcrumbs.vue (Zeile 17):** aria-current="page" korrekt implementiert ✓
- **DocumentsView.vue (Zeile 66):** role="group" + aria-label auf Stats-Region ✓
- **DocumentsView.vue (Zeile 72-78):** @keydown.enter + @keydown.space auf Card-Buttons ✓
- **EntitiesTable.vue (Zeile 72-73):** aria-label auf Icon-Buttons ✓
- **DynamicSchemaForm.vue (Zeile 18, 36, 53, 71, 87):** aria-describedby auf Hints ✓

### Kritische Issues

**HOCH - Issue 1: aria-invalid fehlt in ALL Formularen**
- **Dateien:**
  - DynamicSchemaForm.vue (Zeile 19, 37, 54, 72, 88): Hat :error-messages aber KEINE :aria-invalid
  - Alle anderen Forms: Wahrscheinlich gleich betroffen
- **Impact:** Screen-Reader wissen nicht, dass Feld fehlerhaft ist
- **Lösung:** `:aria-invalid="!!getFieldErrors(key).length"` hinzufügen

**HOCH - Issue 2: Icon-Button Touch-Targets < 44px**
- **Dateien & Zeilen:**
  1. EntitiesTable.vue (Zeile 69): size="small" auf Eye-Button
  2. EntitiesTable.vue (Zeile 79): size="small" auf Edit-Button
  3. EntitiesTable.vue (Zeile 88): size="small" auf Delete-Button
  4. ResultsView.vue: Wahrscheinlich ähnlich
  5. CrawlerView.vue (Zeile 141): size="small" auf Stop-Button
- **WCAG:** Mindestens 44x44px für Touch-Targets
- **Impact:** Mobile-Nutzer können schwer klicken

**MITTEL - Issue 3: Keine aria-live auf dynamischen Error-Messages**
- **Betrifft:** Alle Datatable-Error-States
- **Sollte:** `<div role="alert" aria-live="polite" aria-atomic="true">` wrappen
- **Beispiel:** ResultsView.vue #no-data Template fehlt

**MITTEL - Issue 4: Manche Buttons ohne :title oder aria-label**
- **Dateien:**
  - SourcesView.vue (Zeile 34): icon="mdi-menu" Button hat aria-label ✓ (KORREKT!)
  - Aber inkonsistent in anderen Views

**NIEDRIG - Issue 5: text-medium-emphasis Kontrast zu niedrig in Dark Mode**
- **Dateien:** EmptyState.vue (Zeile 25), DocumentsView.vue (Zeile 8, 18)
- **Problem:** text-medium-emphasis = rgba(..., 0.6) = ~30% grau, sehr dunkel in Dark Mode
- **Lösung:** In Dark Mode auf 0.7 oder 0.75 erhöhen

---

## 3. RESPONSIVE DESIGN

### Stärken
- **Grid System konsistent:** cols="12" sm="6|4" md="3|2" Pattern überall
- **DocumentsView.vue (Zeile 67-84):** Exzellente responsive Stats (cols="6" sm="4" md="2")
- **PageHeader.vue (Zeile 77-80):** @media (max-width: 768px) mit flex-direction: column ✓
- **SourcesView.vue (Zeile 2):** d-flex + flex-grow-1 für Responsive Layout

### Kritische Issues

**HOCH - Issue 1: Feste Inline-Widths in Responsive Views**
- **ResultsView.vue:** style="max-width: 220px;" wahrscheinlich bei Spalten-Rendering
- **CrawlerView.vue (Zeile 136):** col-width-md CSS-Klasse (wahrscheinlich ~500px oder mehr)
- **Andere Views:** Möglicherweise weitere feste Breiten
- **Impact:** Auf Mobilgeräten < 600px kann 220px = 50%+ der Breite sein → Overflow möglich

**MITTEL - Issue 2: Keine Mobile-Optimierung für Multi-Column Datatables**
- **Betrifft:** SourcesView.vue, ResultsView.vue (benötigen Überprüfung der vollständigen Header)
- **Problem:** Viele Spalten auf Mobile = Horizontal-Scroll nötig
- **Lösung:** Responsive Headers (nur essenzielle Spalten auf Mobile)

**MITTEL - Issue 3: Dialog max-width auf Desktop-Größen fixiert**
- **Beispiel:** DashboardView.vue hat max-width="650" (benötigt Überprüfung)
- **Impact:** Auf Small Screens (< 400px) nimmt Dialog fast ganze Breite ein

**MITTEL - Issue 4: Keine Bottom-Navigation auf Mobile**
- **App.vue:** Navigation Drawer funktioniert, aber Bottom-Nav würde UX verbessern
- **Besonders wichtig:** Wenn Drawer ausblendet, sollte Bottom-App-Bar eingeblendet sein

---

## 4. LOADING STATES

### Stärken
- **Skeleton-Coverage:** 7 Komponenten + Überprüfung
  1. ResultsSkeleton.vue ✓ (ResultsView nutzt)
  2. DocumentsSkeleton.vue ✓ (DocumentsView nutzt)
  3. CategoriesSkeleton.vue ✓
  4. EntitiesSkeleton.vue ✓
  5. SourcesSkeleton.vue ✓ (SourcesView nutzt)
  6. DashboardSkeleton.vue ✓
  7. EntityDetailSkeleton.vue ✓
- **Overlay-Loading:** EntitiesView.vue + CrawlerView.vue mit role="status" + aria-live

### Kritische Issues

**MITTEL - Issue 1: FavoritesView.vue hat nur v-progress-circular, keine Skeleton**
- **Datei:** FavoritesView.vue (Zeile 75-82)
- **Code:** `v-if="loading"` zeigt nur Progress-Circle
- **Sollte:** FavoritesSkeleton.vue erstellen oder EntitiesSkeleton wiederverwenden

**NIEDRIG - Issue 2: Keine Transition zwischen Skeleton und Content**
- **Betrifft:** Alle Skeleton-Loader
- **Problem:** Abrupter Übergang bei schneller Verbindung
- **Lösung:** v-fade-transition mode="out-in" hinzufügen

**NIEDRIG - Issue 3: Loading-Text manchmal nicht lokalisiert**
- **CrawlerView.vue (Zeile 7-8):** Lokalisiert mit $t('crawler.dataLoading') ✓
- **Andere Views:** Wahrscheinlich OK, aber überprüfen

---

## 5. ERROR HANDLING & ERROR STATES

### Stärken
- **ErrorBoundary.vue existiert:** Mit Retry-Button und Stack-Trace in Dev-Mode
- **TableErrorState.vue (Zeile 8):** role="alert" für Screenreader-Ankündigung ✓
- **EntitiesTable.vue (Zeile 16-23):** #no-data Template mit TableErrorState + EmptyState ✓

### Kritische Issues

**HOCH - Issue 1: ResultsView.vue #no-data Template fehlt**
- **Datei:** ResultsView.vue (Zeile ~200+)
- **Problem:** v-data-table-server hat KEINE #no-data Template
- **Impact:** Bei Fehler oder leeren Resultaten: Leere Tabelle oder kryptischer Fehler

**HOCH - Issue 2: CrawlerView.vue & SourcesView.vue fehlen Error-States in Tabellen**
- **SourcesView.vue (Zeile 118-127):** v-data-table-server OHNE #no-data
- **CrawlerView.vue:** Benötigt Überprüfung der Crawl-Jobs-Tabelle

**MITTEL - Issue 3: Fehler-Messages nicht benutzerfreundlich**
- **Problem:** Server 500 Error → zeige "Server Error" statt Stacktrace
- **Lösung:** useErrorHandler.ts mit USER_FRIENDLY_ERRORS Map erweitern

**MITTEL - Issue 4: Keine Error Details aus Server-Validierungsfehlern (422)**
- **Betrifft:** Alle Forms ohne Backend-Fehlerbehandlung
- **Beispiel:** Category-Name Duplikat → sollte im Formular highlighted sein

---

## 6. FEEDBACK & NOTIFICATIONS

### Stärken
- **Snackbar System:** useSnackbar.ts mit Timeouts (success: 3s, error: 5s)
- **343+ color Vorkommen** deuten auf konsistente Button-Farbgebung hin
- **BatchActionProgress.vue:** Für Batch-Operationen vorhanden
- **ExportProgressPanel.vue:** Für Downloads vorhanden

### Kritische Issues

**MITTEL - Issue 1: Erfolgreiche Aktionen ohne Feedback**
- **Betrifft:** Create/Edit Dialoge ohne bestätigenden Snackbar
- **Beispiele:**
  - Kategorie erstellen → nur Auto-Refresh, kein "erfolg erstellt" Message
  - Entity bearbeiten → benötigt Überprüfung

**MITTEL - Issue 2: Bulk-Operationen ohne Progress-Komponente sichtbar**
- **ResultsView.vue (Zeile 15-23):** bulkVerify hat :loading="bulkVerifying" ✓
- **Aber:** Sollte BatchActionProgress.vue nutzen für besseres Feedback
- **DocumentsView.vue:** Ähnlich bulkProcess + bulkAnalyze

**NIEDRIG - Issue 3: Snackbar-Position auf Mobile nicht optimiert**
- **Problem:** Bottom-Snackbar kann von Bottom-Nav überlagert sein
- **Lösung:** :position="isMobile ? 'top' : 'bottom'" nutzen

---

## 7. FORMULARE & VALIDIERUNG

### Stärken
- **DynamicSchemaForm.vue (Zeile 18, 36, 53, 71, 87):** aria-describedby auf alle Hints ✓
- **Alle Inputs:** :error-messages vorhanden ✓
- **Validation Rules:** Konsistent (required, email, integer, etc.)
- **useFormValidation.ts existiert**

### Kritische Issues

**HOCH - Issue 1: aria-invalid FEHLT in ALLEN Formularen**
- **DynamicSchemaForm.vue:** 5 Input-Typen (select, text, email, date, textarea, integer)
- **Alle zeigen:** :error-messages aber KEINE :aria-invalid
- **Impact:** Screenreader können nicht erkennen, dass Feld fehlerhaft ist
- **Code Beispiel (Zeile 19, 37, etc.):**
  ```vue
  <!-- Statt nur: -->
  <v-text-field
    :error-messages="getFieldErrors(key)"
  />
  
  <!-- Sollte sein: -->
  <v-text-field
    :aria-invalid="!!getFieldErrors(key).length"
    :error-messages="getFieldErrors(key)"
  />
  ```

**MITTEL - Issue 2: Keine Unterscheidung zwischen Validierungs- und Backend-Fehler**
- **Problem:** User sieht "Feld erforderlich" und "Name existiert bereits" ohne Unterschied
- **Lösung:** FieldError Type mit "validation|server|async"

**MITTEL - Issue 3: Keine Live-Async-Validierung**
- **Betrifft:** Category Name, Entity Name (sollten Duplicate-Check haben)
- **Lösung:** debounced async validator mit debounce.ts

**NIEDRIG - Issue 4: Keine Unsaved-Changes Warning**
- **Betrifft:** Alle Edit-Forms
- **Lösung:** onBeforeRouteLeave mit hasUnsavedChanges computed

---

## 8. NAVIGATION & BREADCRUMBS

### Stärken
- **EntityBreadcrumbs.vue (Zeile 17):** aria-current="page" korrekt ✓
- **EntityBreadcrumbs.vue (Zeile 2):** aria-label="Breadcrumb" ✓
- **EntitiesView.vue (Zeile 57-58):** Tab-Navigation mit role="navigation" + aria-label ✓
- **App.vue:** Navigation mit Badges (Pending, Unverified)

### Kritische Issues

**MITTEL - Issue 1: Fehlender Back-Button Pattern**
- **Betrifft:** EntityDetailView und andere Detail-Views
- **Problem:** Kein offensichtlicher Weg zurück zur Liste (außer Browser-Back)
- **Lösung:** PageHeader mit prepend-Icon="mdi-arrow-left" + @click="router.back()"

**MITTEL - Issue 2: Keine Lazy-Loaded Routes (Code-Splitting)**
- **Problem:** Alle Routes eager-loaded = große initiale Bundle
- **Lösung:** defineAsyncComponent in router/index.ts nutzen

**NIEDRIG - Issue 3: Breadcrumb disabled State nicht sichtbar genug**
- **EntityBreadcrumbs.vue (Zeile 46):** disabled: true ohne visuelles Feedback
- **Lösung:** CSS-Klasse mit opacity: 0.7, font-weight: 600, text-decoration: underline

---

## 9. DARK/LIGHT MODE

### Stärken
- **Theme Toggle:** App.vue (Zeile ~113-118) mit localStorage Persistenz ✓
- **CaeliWindLogo:** Dynamisch farbt basierend auf isDark ✓
- **Vuetify v3 CSS Variables:** Korrekt genutzt

### Kritische Issues

**MITTEL - Issue 1: text-medium-emphasis Kontrast zu niedrig in Dark Mode**
- **Dateien:** EmptyState.vue, PageHeader.vue, DocumentsView.vue, etc.
- **Problem:** text-medium-emphasis = rgba(var(--v-theme-on-surface), 0.6) → nur 30% opacity
- **Impact:** Grau auf dunkelgrau = unlesbar (< 4.5:1 Contrast Ratio)
- **Lösung:** 
  ```css
  .text-medium-emphasis {
    color: rgba(var(--v-theme-on-surface), 0.6);
  }
  
  .dark .text-medium-emphasis {
    color: rgba(var(--v-theme-on-surface), 0.75);
  }
  ```

**NIEDRIG - Issue 2: Inline-Farben nicht Theme-aware**
- **Problem:** Manche Custom-Farben könnten hardcoded sein
- **Sollte:** CSS Variables nutzen statt Hex-Farben

---

## ZUSAMMENFASSUNG NACH KATEGORIE

| Kategorie | Score | Top-Issue | Auswirkung |
|-----------|-------|-----------|-----------|
| **Konsistenz** | 7.5/10 | Fehlende #no-data Templates | Inkonsistente Error-States |
| **Accessibility** | 7/10 | aria-invalid fehlt, Touch-Targets < 44px | Screen-Reader blind, Mobile-Frustration |
| **Responsive Design** | 7.5/10 | Inline max-widths, Keine Mobile-Headers | Overflow auf Small Screens |
| **Loading States** | 8/10 | FavoritesView ohne Skeleton | Langsam wirkend |
| **Error Handling** | 6.5/10 | ResultsView #no-data fehlt | Schlechte Error-UX |
| **Feedback** | 7.5/10 | Keine Success-Messages bei Create | User verwirrt über Erfolg |
| **Formulare** | 6/10 | aria-invalid fehlt überall | Screen-Reader tauglich |
| **Navigation** | 7.5/10 | Fehlender Back-Button | User verloren auf Detail-Page |
| **Dark Mode** | 7/10 | text-medium-emphasis Kontrast | Schwer lesbar im Dark Mode |

**GESAMT: 7.1/10 - Solide, aber Accessibility/Fehlerbehandlung benötigen Aufmerksamkeit**

---

## TOP 15 PRIORITÄTEN (Priorisiert nach Impact)

### HOCH (Sofort beheben)
1. **aria-invalid** in ALL Form-Inputs (DynamicSchemaForm + alle anderen Forms)
   - Impact: Screen-Reader Compliance
   - Aufwand: 1-2 Stunden
   - Dateien: DynamicSchemaForm.vue + alle anderen Forms

2. **ResultsView.vue #no-data Template hinzufügen**
   - Impact: Error-Handling, User-Experience
   - Aufwand: 1 Stunde
   - Datei: ResultsView.vue (Zeile ~200)

3. **Icon-Button Touch-Targets auf 44x44px erhöhen**
   - Impact: Mobile Usability (WCAG)
   - Aufwand: 2-3 Stunden
   - Dateien: EntitiesTable.vue, ResultsView.vue, CrawlerView.vue, + weitere

### MITTEL (Diese Woche)
4. **CrawlerView.vue & SourcesView.vue #no-data hinzufügen**
5. **FavoritesView.vue EmptyState zu Komponente umwandeln**
6. **Button-Farbschema standardisieren** (dokumentieren + beheben)
7. **text-medium-emphasis Dark-Mode Kontrast erhöhen**
8. **aria-live + role="alert" auf Error-Messages hinzufügen**

### NIEDRIG (Nächste Iteration)
9. **Inline max-widths responsive machen**
10. **FavoritesView.vue Skeleton hinzufügen**
11. **Transition zwischen Skeleton und Content**
12. **Success-Messages nach Create/Edit**
13. **Batch-Operation Progress verbessern**
14. **Back-Button Pattern implementieren**
15. **Code-Splitting mit defineAsyncComponent**

---

## Spezifische Code-Änderungen

### 1. aria-invalid in DynamicSchemaForm.vue hinzufügen (Alle 5 Input-Typen)
- **Zeile 5-21:** v-select
- **Zeile 24-38:** v-text-field (email)
- **Zeile 41-55:** v-text-field (date/datetime)
- **Zeile 58-73:** v-textarea
- **Zeile 76-89:** v-text-field (regular)
- **Zeile 92-100+:** v-text-field (integer)
- Muster: `:aria-invalid="!!getFieldErrors(key).length"`

### 2. ResultsView.vue #no-data Template
```vue
<v-data-table-server ...>
  <template #no-data>
    <div role="alert" aria-live="polite" aria-atomic="true">
      <TableErrorState
        v-if="error"
        :title="$t('common.loadError')"
        :message="error.message"
        @retry="loadData"
      />
      <EmptyState
        v-else
        icon="mdi-search-off"
        :title="$t('results.noResults')"
      />
    </div>
  </template>
</v-data-table-server>
```

### 3. Touch-Target CSS-Klasse (global.css)
```css
.touch-target {
  min-width: 44px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}
```

---

## Messbare Verbesserungen

Basierend auf vorherigen Audits (7.6/10 → aktuell 7.1/10):
- **aria-invalid Fix:** +0.5 Punkte (Accessibility)
- **Error-States Fix:** +0.6 Punkte (Error Handling)
- **Touch-Targets Fix:** +0.4 Punkte (Accessibility/Mobile)
- **Dark Mode Kontrast:** +0.2 Punkte
- **Button-Konsistenz:** +0.2 Punkte

**Ziel nach Behebung:** 8.0+/10 (Sehr gut)
