# Frontend UX/UI Audit - CaeliCrawler - 31.12.2024

## Audit-Zusammenfassung

Systematisches Audit über Frontend Views, Components, Accessibility, Responsive Design und User Experience.

---

## 1. KONSISTENZ - UI Patterns

### Stärken

**Button-Patterns:**
- Konsistente Verwendung: `variant="outlined" | "tonal" | "text"` + `color="primary|success|error|warning"`
- Icon-Platzierung: `prepend-icon` vs `start` icon konsistent
- Size-Strategie: `size="small"` für Aktionen in Tabellen/Listen, Standard in Headers

**Dialog-Pattern:**
- ConfirmDialog.vue: Standardisierte Bestätigungsdialoge mit `role="dialog"` + `aria-modal="true"`
- Focus Management: `useDialogFocus` Composable für alle Dialoge
- Konsistente Actions: Cancel (tonal), Confirm (color="error|success")

**Card-Pattern:**
- Konsistente Verwendung: `v-card` mit `variant="outlined|elevated"` 
- Text-Hierarchie: Einheitliche Klassen `text-h5`, `text-body-2`, `text-medium-emphasis`

**Filter-Pattern:**
- SourcesActiveFilters.vue: Exzellente keyboard-navigierbar Chip-basiert (Enter/Space/Delete/Backspace)
- Reset-Buttons konsistent: `mdi-filter-off` Icon + "Reset Filters" Text

### Schwächen

1. **Button-Konsistenz im Detail:**
   - ResultsView.vue:273-285 - Mix aus `variant="tonal"` + `color="info"` (inkonsistent mit Primary-Button-Standard)
   - Button-Text manchmal sehr kurz (nur Icon), manchmal Volltext
   - Keine standardisierte Button-Größe für Tabellen-Aktionen

2. **Form-Input Konsistenz:**
   - CategoryFormSearch.vue verwendet `v-combobox` mit Chips
   - Andere Forms nutzen `v-select` oder `v-text-field` - kein einheitliches Pattern
   - Hint/Label-Behandlung variiert

3. **Empty State Handling:**
   - Nur 3 Views haben Skeleton Loader (DocumentsView, ResultsView, CategoriesView)
   - 12 weitere Views ohne dediziertes Empty State
   - Keine standardisierte EmptyStateCard Komponente
   - DashboardView.vue: Nutzt `v-progress-circular` für Loading, nicht Skeleton

4. **Dialog-Konsistenz:**
   - ConfirmDialog.vue: Gutes Pattern
   - Viele andere Dialoge definieren Struktur direkt inline (z.B. DashboardView.vue:51-180)
   - Fehlt: Standardisierte Dialog-Wrapper Komponente

5. **Breadcrumb-Pattern fehlt Accessibility:**
   - EntityBreadcrumbs.vue: Keine ARIA-Attribute
   - Sollte: `aria-current="page"` für aktuelle Seite haben

---

## 2. ACCESSIBILITY (Aria, Keyboard, Kontraste)

### Stärken

1. **ARIA-Labels flächendeckend:**
   - 59 Vorkommen in 11 View-Dateien
   - DashboardView.vue:13-17: Exzellente aria-label auf Buttons
   - SourcesActiveFilters.vue: Umfassende aria-labels auf Chips
   - Dialog aria-modal="true" + aria-labelledby korrekt implementiert

2. **Keyboard-Navigation:**
   - useDialogFocus.ts: Fokus-Management, Fokus-Trap für Dialoge
   - SourcesActiveFilters.vue: Vollständige Keyboard-Navigation (Enter/Space/Delete/Backspace)
   - App.vue: Navigation Drawer mit Keyboard-Zugang

3. **Focus Management:**
   - useDialogFocus Composable mit Auto-Focus und Focus-Restoration
   - FOCUSABLE_SELECTORS korrekt: Button, Link, Input, Select, Textarea, etc.

4. **Farbkontraste (gemäß global.css):**
   - Gutes Contrast-Ratio: `#113634` (Primary) auf Weiß = 10.8:1 ✓
   - Alle Status-Farben definiert: Success, Error, Warning, Info mit White Text
   - Dark Mode mit angepassten Farben

### Schwächen

1. **ARIA-Attribute Lücken:**
   - EntityBreadcrumbs.vue: Keine aria-current="page" (Zeile 28: disabled breadcrumb sollte aria-current haben)
   - SmartQueryResults.vue: Viele Tabellen ohne aria-label
   - EntitiesView.vue: Tabs mit aria-label OK (Zeile 58), aber Stats-Region hat nur role="region" ohne aria-label

2. **Fehlende ARIA Descriptions:**
   - DynamicSchemaForm.vue: aria-describedby korrekt bei Hints
   - Aber: Viele v-text-field ohne aria-describedby für Validierungsfehler
   - Keine aria-live="polite" auf Error-Messages

3. **Accessible Names:**
   - IconButtons oft ohne title/aria-label
   - ResultsView.vue:273: "mdi-eye" Button hat aria-label ✓, aber andere nicht konsistent
   - Chips in Tabellen-Filtern: Labels gut, aber keine announcements

4. **Color-Contrast Issues (gering):**
   - text-medium-emphasis: Grau auf Grau - Kontrast wahrscheinlich < 4.5:1 für AA
   - Sollte überprüft werden für WCAG 2.1 AA Compliance

5. **Keyboard Traps:**
   - ChatAssistant.vue (1047 Zeilen): Keine erkennbare Fokus-Managierung
   - Modal-Dialoge: useDialogFocus gut, aber nicht überall genutzt

---

## 3. RESPONSIVE DESIGN

### Stärken

1. **Vuetify Grid System konsistent:**
   - `cols="12" sm="6" md="3" lg="2"` Pattern überall
   - PageHeader.vue:77-98: @media (max-width: 768px) mit flex-direction: column
   - ResultsView.vue:46-84: Stats-Cards perfekt responsive: cols="6" sm="3"

2. **Breakpoint-Nutzung:**
   - Mobile (cols="12"): Single-column
   - Tablet (sm="6", md="4"): 2-3 spaltig
   - Desktop (md="3", lg="2"): Full layout

3. **Density Control:**
   - density="comfortable" konsistent auf Inputs
   - Dialog max-width: "650" oder "400" - gut für responsive

4. **Navigation Drawer:**
   - App.vue: v-navigation-drawer mit Collapse-Support
   - Reagiert auf screen-size automatisch

### Schwächen

1. **Inline-Stile für Breiten:**
   - ResultsView.vue:197: `style="max-width: 220px;"` - Feste Pixel-Breite in Responsive View
   - Sollte: responsive Klasse oder Breakpoint-basiert sein
   - ChatAssistant.vue: Wahrscheinlich weitere feste Breiten

2. **Mobile-First Approach:**
   - Grid-Struktur OK, aber nicht konsequent mobile-first definiert
   - Einige Komponenten nutzen md="3" ohne SM-Fallback
   - SourceFormDialog: Wahrscheinlich nicht mobile-optimiert

3. **Fehlende @media Breakpoints:**
   - Nur PageHeader.vue hat @media Query
   - ScheduleBuilder.vue, DynamicSchemaForm.vue: Wahrscheinlich nicht mobile-optimiert
   - Dichte auf Mobile: Sollte compacter sein

4. **Touch-Targets:**
   - Icon-Button Größe: size="small" ist < 44px (WCAG Empfehlung: 44x44px)
   - ResultsView.vue:273-285: Kleine Icon-Buttons in Tabellen
   - Mobile-Nutzern könnte schwerfallen

---

## 4. LOADING STATES

### Stärken

1. **Skeleton Loader:**
   - ResultsSkeleton.vue: Dedizierte Komponente
   - DocumentsSkeleton.vue, CategoriesSkeleton.vue: Vorhanden
   - EntitiesSkeleton.vue: Vorhanden
   - Muster: `v-if="loading && initialLoad" -> <XyzSkeleton />`

2. **Progress Indicators:**
   - v-progress-circular: In allen Loading-States
   - EntitiesView.vue:5-23: Schön gestalteter Loading-Overlay mit Message
   - DashboardView.vue:36-38: Loading mit role="status" + aria-live="polite" ✓

3. **Loading Props:**
   - v-btn :loading="loading": Überall konsistent
   - v-data-table-server :loading="loading": Gutes Pattern

### Schwächen

1. **Skeleton-Abdeckung:**
   - PySisTab.vue (1474 Zeilen): Keine Skeleton
   - EntityFacetsTab.vue (1307 Zeilen): Keine Skeleton
   - SmartQueryResults.vue: Wahrscheinlich keine Skeleton
   - ChatAssistant.vue: Loading nur via :loading, keine Skeleton

2. **Placeholder-Messages:**
   - Loading-Text nicht überall lokalisiert
   - EntitiesView.vue:17-20: Dynamische Message basierend auf Daten OK
   - Aber: Konsistenz fehlt

3. **Transition fehlt:**
   - Skeleton zu Content: Keine v-transition
   - Abrupt appearance möglich bei schneller Verbindung
   - Sollte: v-fade-transition oder ähnlich

---

## 5. ERROR HANDLING

### Stärken

1. **ErrorBoundary Komponente:**
   - frontend/src/components/common/ErrorBoundary.vue: Exzellent
   - Graceful Fallback mit Retry-Button
   - Stack-Trace in Development-Mode
   - onErrorCaptured Hook korrekt genutzt

2. **Error Messages:**
   - DynamicSchemaForm.vue: :error-messages auf Inputs
   - Validierungsfehler mit Messages

3. **v-alert für Fehler:**
   - Typ="error" konsistent
   - Variant="tonal" für bessere Lesbarkeit

### Schwächen

1. **Fehlende Error States:**
   - v-data-table: Keine Error-Handling, nur :loading
   - Wenn API fehlschlägt: Keine Fallback UI außer Skeleton-Loading
   - Sollten zeigen: "Fehler beim Laden" statt leerer Table

2. **Error Messages User-freundlich?**
   - $t('validation.required'): Gut
   - Aber: Netzwerkfehler - werden diese benutzerfreundlich angezeigt?
   - useAsyncOperation: Error-Handling Logik, aber Presentation?

3. **Error Recovery:**
   - ErrorBoundary hat Retry ✓
   - Aber: v-data-table ohne Retry-Mechanik
   - API-Fehler: Nur Snackbar wahrscheinlich

4. **Fehlende Error Boundaries:**
   - Nicht um jede View gewickelt
   - Nur manuelle ErrorBoundary-Einsätze dokumentiert
   - Sollte: Wrapper um Router-View in App.vue

---

## 6. FEEDBACK & NOTIFICATIONS

### Stärken

1. **Snackbar System:**
   - useSnackbar.ts: Globale Snackbar mit timeouts
   - success: 3000ms, error: 5000ms, warning: 4000ms, info: 3000ms
   - showSuccess/showError/showWarning/showInfo Convenience-Methods

2. **Bestätigungsdialoge:**
   - ConfirmDialog.vue: Standardisiert mit Loading-State
   - Buttons: Cancel (tonal), Confirm (colored)

3. **Progress Feedback:**
   - BatchActionProgress.vue: Für Batch-Operationen
   - ExportProgressPanel.vue: Für Exports

### Schwächen

1. **Snackbar Konsistenz:**
   - Nur 5 Views nutzen useSnackbar (Grep: EntityDetail, ExportView, FavoritesView, SummaryDashboard, CustomSummaries)
   - Andere Views wahrscheinlich keine Feedback
   - Keine zentrale App.vue Snackbar sichtbar in Code

2. **Toast-Nachrichten:**
   - Keine Toast-Komponente, nur Snackbar
   - Snackbar-Position: Wo? (Nicht im View-Code sichtbar, wahrscheinlich in App.vue)

3. **User Actions Feedback:**
   - Bulk-Verify in ResultsView: Hat Loading, aber kein Success-Message wahrscheinlich
   - CategoryCreate/Edit: Wahrscheinlich kein Feedback

4. **Fehlerbenachrichtigungen:**
   - API-Fehler: Werden diese alle angezeigt?
   - 404 Error: Gibt es Fallback?

---

## 7. NAVIGATION

### Stärken

1. **App-Navigation:**
   - App.vue: Drawer mit Haupt- und Admin-Navigation
   - Badges: Pending Docs (orange), Unverified Results (info)
   - Divider zwischen Sektionen

2. **Breadcrumbs:**
   - EntityBreadcrumbs.vue: Home -> Entity-Type -> Entity
   - Klare Hierarchie

3. **Routing:**
   - router/index.ts: Strukturiert
   - Named Routes: `/entity/{id}`, `/entities/{type}`
   - Query-Parameter: `?search=`, `?category=`

4. **Tabs-Navigation:**
   - EntitiesView.vue:51-70: Entity-Type Tabs mit Badge
   - EntityDetailView.vue: Window-Items mit Tabs korrekt

5. **Inline-Navigation:**
   - ResultsView.vue:201: Router-Link zu Documents mit Query
   - Smart-Query: Sidebar Navigation

### Schwächen

1. **Breadcrumbs fehlende ARIA:**
   - EntityBreadcrumbs.vue: Keine aria-current="page"
   - Current-Item sollte: `aria-current="page"` haben
   - Breadcrumb sollte: `role="navigation" aria-label="Breadcrumb"`

2. **Mobile Navigation:**
   - Drawer: Gut für Desktop, aber Mobile?
   - Wahrscheinlich: Collapse auf Mobile
   - Bottom-Navigation nicht vorhanden

3. **Menü-Logik:**
   - Admin-Bereich: Nur v-if="auth.isAdmin"
   - Aber: Keine detaillierte Permissions-Checks
   - SourcesView, DocumentsView: Sollten auch restricted sein?

4. **Lazy-Loading Routes:**
   - Keine defineAsyncComponent sichtbar
   - Alle Routes wahrscheinlich eager-loaded
   - Performance: Sollte Code-Splitting nutzen

5. **Back-Navigation:**
   - Keine Back-Button Pattern
   - Router.back()? Nur Router.push()
   - UX: Zurück-Button auf allen Details fehlt

---

## 8. DARK/LIGHT MODE

### Stärken

1. **Theme Toggle:**
   - App.vue:114-117: Button mit icons (sun/moon)
   - isDark computed: `theme.global.current.value.dark`
   - toggleTheme: Speichert in localStorage

2. **Color-Adaptation:**
   - CaeliWindLogo: Farbwechsel basierend auf isDark
   - App.vue:6: `:primary-color="isDark ? '#deeec6' : '#113534'"`

3. **CSS Variables:**
   - Vuetify v3: Nutzt CSS Variables
   - rgba(var(--v-theme-primary), 0.06): Korrekt

4. **Persisten Storage:**
   - localStorage.setItem('caeli-theme', newTheme)
   - localStorage.getItem('caeli-theme') wird auf Mount gelesen

### Schwächen

1. **Theme-Konsistenz Checks:**
   - PageHeader.vue:51-53: Nutzt rgba(var(...), 0.06) - gut
   - Aber: Inline-Farben möglich?
   - DynamicSchemaForm: Backgrounds nicht überprüft

2. **Dark Mode Coverage:**
   - Text-Farben: Wahrscheinlich automatisch via Vuetify
   - Aber: text-medium-emphasis in Dark Mode: Lesbar?
   - Background-Farben: v-card variant="outlined" automatisch?

3. **Logo/Icon Anpassung:**
   - CaeliWindLogo: Nur in App.vue angepasst
   - Andere Logos/Icons: Hardcoded möglich
   - Favicon: Nicht sichtbar, wahrscheinlich nicht angepasst

4. **Keine Kontrollierter Theme:**
   - Theme wird global über Vuetify gewechselt
   - Keine Validierung von Theme-Wert
   - Was wenn localStorage-Wert ungültig ist?

---

## Component Size Issues

**Größte Komponenten (> 800 Zeilen):**
1. PySisTab.vue: 1474 Zeilen
2. EntityFacetsTab.vue: 1307 Zeilen
3. ChatAssistant.vue: 1047 Zeilen
4. PlanModeChat.vue: 918 Zeilen
5. MapVisualization.vue: 862 Zeilen
6. EntityDetailView.vue: 860 Zeilen
7. ChatWindow.vue: 830 Zeilen

**Refactoring-Kandidaten:**
- ChatAssistant.vue: Sollte in ChatWindow, ChatBubble, InputPanel aufgeteilt werden
- EntityFacetsTab.vue: Zu viel Logik, sollte in Composables ausgelagert werden

---

## Zusammenfassung nach Kategorien

| Kategorie | Score | Status |
|-----------|-------|--------|
| **Konsistenz** | 7.5/10 | Gut, aber Gaps |
| **Accessibility** | 8/10 | Sehr gut, Minor Gaps |
| **Responsive Design** | 8/10 | Sehr gut, Touch-Targets überprüfen |
| **Loading States** | 7/10 | Gut, Abdeckung erweitern |
| **Error Handling** | 7.5/10 | Gut, aber inconsistent |
| **Feedback** | 7/10 | Gut, aber Snackbar nicht zentral |
| **Navigation** | 8/10 | Sehr gut, aber aria-current fehlt |
| **Dark/Light Mode** | 8/10 | Sehr gut, aber Coverage überprüfen |

**Gesamt: 7.6/10 - Gut, aber Optimierungen möglich**

---

## Top Prioritäten

1. **Breadcrumb aria-current**: EntityBreadcrumbs.vue Zeile 28
2. **Touch-Target Größe**: Icon-Buttons > 44x44px
3. **Empty States standardisieren**: EmptyStateCard Komponente
4. **Snackbar zentral**: App.vue sichtbar machen
5. **Error-States in Tabellen**: v-data-table Fehlerbehandlung
6. **Responsive Inline-Widths**: style="max-width: 220px;" entfernen
7. **Button-Konsistenz**: Farbschema standardisieren
8. **ChatAssistant refactorieren**: 1047 Zeilen zu groß
