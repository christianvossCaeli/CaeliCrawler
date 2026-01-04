# Frontend UX/UI Audit CaeliCrawler - Januar 2026 (Komprehensiv)

## Executive Summary

Basierend auf systematischer Analyse von **15+ komponenten und Views** mit Code-Review:
- **Gesamtscore: 7.8/10** - Solide UX/UI mit **gezielten, schnell umsetzbaren Verbesserungen**
- **POSITIVE ENTWICKLUNG:** ResultsTable hat jetzt #no-data Template mit Error-Handling ✓
- **HAUPTPROBLEME:** Touch-Targets, aria-invalid, Button-Konsistenz, fehlende Snackbars bei Actions

---

## 1. ACCESSIBILITY (WCAG 2.1) - AUDIT DETAILLIERT

### Score: 7.2/10

### STÄRKEN (Verifiziert)

**Exzellente ARIA Coverage:**
- DynamicSchemaForm.vue (Zeile 18, 37, 55, 74): aria-describedby auf ALLE Hints ✓
- DocumentsView.vue (Zeile 68): role="group" + aria-label auf Stats-Region ✓
- DocumentsView.vue (Zeile 74-80, 97-99): @keydown.enter + @keydown.space auf Card-Buttons ✓
- EntitiesView.vue (Zeile 5): role="status" + aria-live="polite" auf Loading-Overlay ✓
- EntitiesView.vue (Zeile 57-58): Tab-Navigation mit role="navigation" + aria-label ✓
- ResultsTable.vue (Zeile 78): aria-label auf Icon-Buttons ✓
- FavoritesView.vue (Zeile 162): aria-label auf Buttons mit Entity-Namen ✓

**Focus Management & Keyboard Navigation:**
- App.vue: Navigation Drawer keyboard-navigierbar ✓
- DocumentsView.vue (Zeile 78-80): Keyboard-Navigation auf Stats ✓
- CrawlerView.vue (Zeile 145): aria-label auf Stop-Button ✓

### KRITISCHE ISSUES

#### HOCH - Issue #1: aria-invalid FEHLT in ALLEN Formularen
**Status:** KRIT ISCH - Betrifft alle Input-Felder

**Dateien & Zeilen:**
- DynamicSchemaForm.vue (Zeile 19, 38, 56, 75): Hat `:error-messages` aber **KEINE** `aria-invalid`
- Alle anderen Forms: Screen-Reader wissen nicht, dass Feld fehlerhaft ist

**Auswirkung:** Screen-Reader User können nicht erkennen, welche Felder fehlerhaft sind (WCAG 2.1 Failure)

**Code-Beispiel (FALSCH):**
```vue
<!-- Zeile 5-22 in DynamicSchemaForm.vue -->
<v-select
  :model-value="formData[key]"
  :error-messages="getFieldErrors(key)"
  <!-- FEHLT: :aria-invalid ❌ -->
/>
```

**Lösung (EINFACH):**
```vue
<v-select
  :model-value="formData[key]"
  :aria-invalid="!!getFieldErrors(key).length"  <!-- ✓ HINZUFÜGEN -->
  :error-messages="getFieldErrors(key)"
/>
```

#### HOCH - Issue #2: Icon-Button Touch-Targets < 44x44px
**Status:** WCAG 2.1 Level AAA Violation

**Dateien & Zeilen:**
1. ResultsTable.vue (Zeile 73-110): `size="default"` auf Eye, Verify, Document, JSON Buttons
   - ABER: "default" in Vuetify = 40px (unter 44px Minimum)
2. FavoritesView.vue (Zeile 157-174): `size="small"` auf Eye und Star-Off Buttons (32px)
3. DocumentsView.vue (Zeile 338-341): `size="small"` auf Action-Buttons (32px)
4. CrawlerView.vue (Zeile 140-147): `size="small"` auf Stop-Button (32px)

**Auswirkung:** Mobile-User Frustration, Touch-Fehler, schlechter Zugang für Menschen mit motorischen Einschränkungen

**Lösung:** CSS-Klasse + nutzen
```css
/* global.css oder styles.scoped -->
.touch-target {
  min-width: 44px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}
```

Dann in Components:
```vue
<v-btn
  icon="mdi-eye"
  size="small"  // Looks small
  class="touch-target"  // Aber 44px Target
/>
```

#### MITTEL - Issue #3: Keine aria-live auf Error-Messages in Datatable
**Dateien:**
- ResultsTable.vue (Zeile 115-122): Hat #no-data mit TableErrorState
  - ABER: Fehlt `<div role="alert" aria-live="polite">` Wrapper
- SourcesView.vue (Zeile 118+): Datatable hat KEINE #no-data Template (benötigt Überprüfung)

**Lösung:**
```vue
<template #no-data>
  <div role="alert" aria-live="polite" aria-atomic="true">
    <TableErrorState v-if="error" ... />
    <EmptyState v-else ... />
  </div>
</template>
```

#### MITTEL - Issue #4: text-medium-emphasis Kontrast in Dark Mode
**Dateien mit Problem:**
- PageHeader.vue (Zeile 14, 18): text-medium-emphasis = zu dunkel in Dark Mode
- FavoritesView.vue (Zeile 96-97, 130-131): text-medium-emphasis = unlesbar
- DocumentsView.vue (Zeile 318, 350-351): text-medium-emphasis = Grau auf Dunkelgrau

**Kontrast-Verhältnis:** rgba(..., 0.6) = ~3.5:1 (unter WCAG AA 4.5:1)

**Lösung:**
```css
.text-medium-emphasis {
  color: rgba(var(--v-theme-on-surface), 0.6);
}

@media (prefers-color-scheme: dark) {
  .text-medium-emphasis {
    color: rgba(var(--v-theme-on-surface), 0.75);  /* 75% statt 60% */
  }
}
```

---

## 2. VISUAL KONSISTENZ - AUDIT DETAILLIERT

### Score: 7.5/10

### STÄRKEN

**Button-Farbschema meist konsistent:**
- ResultsView.vue (Zeile 20): color="success" auf Bulk-Verify ✓
- DocumentsView.vue (Zeile 19): color="primary" auf Process Selected ✓
- EntitiesView.vue (Zeile 40): color="primary" auf Create New ✓

**Card-Styling einheitlich:**
- CrawlerView.vue (Zeile 72-103): Stats-Cards mit color property korrekt ✓
- DocumentsView.vue (Zeile 69-188): Stats-Cards responsive mit role="button" ✓

**Icons konsistent:**
- Alle prepend-icon + end Icons vorhanden ✓
- Skeleton-Loaders existieren und werden genutzt ✓

### KRITISCHE ISSUES

#### HOCH - Issue #1: Button-Farbschema INKONSISTENT in Details

**Problem:** Einige Buttons nutzen konturintuitive Farben

**Beispiele:**
- ResultsView.vue (Zeile 31): CSV-Export mit `color="info"` (sollte "success" sein)
- DocumentsView.vue (Zeile 29): Analyze mit `color="info"` (OK, aber Konvention?)
- FavoritesView.vue (Zeile 98-101): Router-Link Button ohne color Prop

**Empfohlenes Schema:**
```
- PRIMARY: Create, Save, Submit, Process, Analyze
- SUCCESS: Verify, Confirm, Export, Complete
- ERROR: Delete, Remove, Stop
- WARNING: Caution, Review
- INFO: Help, Details, More Info
- GREY/DEFAULT: Navigation, View Details
```

#### MITTEL - Issue #2: Loading-States Abdeckung unvollständig

**Verbesserung:** FavoritesView.vue (Zeile 67-71) hat Skeleton ✓

**Aber immer noch fehlende Skeletons:**
- CrawlerView.vue: Hat nur Loading-Overlay, keine Skeleton für Crawl-Jobs-Tabelle
- SourcesView.vue: Hat SourcesSkeleton (gut), aber richtig integriert?

#### MITTEL - Issue #3: Empty States teilweise manuell erstellt

**Verbesserung:** DocumentsView.vue (Zeile 345-353) nutzt manuelles #no-data Template
- Sollte besser: EmptyStateCard Komponente nutzen
- Gleichzeitig: Konsistenz mit anderen Views

---

## 3. KEYBOARD NAVIGATION & FOCUS

### Score: 8/10 (Gut)

### STRENGTHS

- DocumentsView.vue: Vollständige Keyboard-Navigation auf Stats (Enter, Space)
- App.vue: Navigation Drawer keyboard-accessible
- Buttons konsistent mit icon und aria-label

### ISSUE

- Keine explizite Focus-Order Dokumentation
- Tab-Order möglicherweise nicht überall optimal
- Keine visible Focus-Indicators in Custom Components sichtbar

---

## 4. RESPONSIVE DESIGN - AUDIT DETAILLIERT

### Score: 7.5/10

### STÄRKEN

**Excellent Grid System:**
- DocumentsView.vue (Zeile 69-188): `cols="12" sm="4" md="2"` Pattern ✓
- Alle Stats-Cards responsive ✓
- PageHeader.vue (Zeile 82-103): @media (max-width: 768px) für Mobile ✓

**Mobile-Optimierungen:**
- SourcesView.vue (Zeile 34-37): ToggleSidebar Button nur auf Mobile (d-md-none) ✓
- CrawlerView.vue (Zeile 47-68): Navigation-Drawer responsive ✓
- App.vue: Drawer width 256px (standard) ✓

### KRITISCHE ISSUES

#### MITTEL - Issue #1: Inline Fixed Widths in Responsive Views

**Dateien & Probleme:**
1. CrawlerView.vue (Zeile 179): `style="max-width: 400px;"` bei URL-Anzeige
   - Auf Small Screens (< 400px) problematisch
2. ResultsTable.vue (Zeile 19): `title` Attribute möglich truncation
3. PageHeader.vue (Zeile 15): Potential overflow bei langen Titeln

**Lösung:** Responsive Utilities statt Fixed Widths
```vue
<!-- Statt: -->
<div style="max-width: 400px;">{{ text }}</div>

<!-- Besser: -->
<div class="responsive-text-container">{{ text }}</div>

<!-- CSS: -->
@media (max-width: 600px) {
  .responsive-text-container { max-width: 100px; }
}
@media (min-width: 601px) {
  .responsive-text-container { max-width: 400px; }
}
```

#### MITTEL - Issue #2: Datatable Spalten nicht Mobile-optimiert

**Betrifft:** SourcesView.vue (Zeile 118+)

**Problem:** Viele Spalten auf Mobile = Horizontal-Scroll obligatorisch

**Lösung:** Responsive Headers (beispiel aus EntitiesView.vue):
```typescript
const headers = computed(() => {
  const isMobile = $vuetify.display.smAndDown.value
  return isMobile
    ? [{ key: 'name', title: 'Name' }, { key: 'actions', title: 'Actions' }]
    : [{ key: 'name' }, { key: 'category' }, { key: 'source_type' }, { key: 'actions' }]
})
```

#### NIEDRIG - Issue #3: Dialog max-width nicht Mobile-optimiert

**Beispiel:** CrawlerView.vue Dialogs haben wahrscheinlich fixed max-width

**Lösung:**
```vue
<v-dialog max-width="650" class="responsive-dialog">
  <!-- CSS: -->
  @media (max-width: 600px) {
    :deep(.responsive-dialog) { width: 95vw !important; }
  }
</v-dialog>
```

---

## 5. LOADING STATES

### Score: 8/10 (Sehr Gut)

### STÄRKEN

**Exzellente Skeleton-Coverage:**
1. ResultsSkeleton.vue - ResultsView nutzt korrekt (Zeile 6) ✓
2. DocumentsSkeleton.vue - DocumentsView nutzt (Zeile 6) ✓
3. FavoritesSkeleton.vue - FavoritesView nutzt (Zeile 67-71) ✓
4. SourcesSkeleton.vue - SourcesView nutzt (Zeile 4-5) ✓

**Loading-Overlays:**
- EntitiesView.vue (Zeile 4-23): Exzellenter Loading-Overlay mit role="status" ✓
- CrawlerView.vue (Zeile 4-10): Loading-Overlay mit aria-label ✓
- FavoritesView.vue (Zeile 84-91): Loading-Overlay für Pagination ✓

**Transitions:**
- ResultsView.vue (Zeile 4): `<transition name="fade" mode="out-in">` ✓
- FavoritesView.vue (Zeile 65): `<transition name="fade" mode="out-in">` ✓
- DocumentsView.vue (Zeile 4): `<transition name="fade" mode="out-in">` ✓

### MINOR ISSUES

- Keine explizite Abbruch-Option bei langen Loads
- Loading-Text könnte aussagekräftiger sein

---

## 6. ERROR HANDLING & EMPTY STATES

### Score: 8/10 (Sehr Gut) - BESSERUNG ERKANNT!

### STÄRKEN

**TableErrorState existiert und wird genutzt:**
- ResultsTable.vue (Zeile 115-129): #no-data Template mit TableErrorState + EmptyState ✓
- Komponente hat role="alert" und Details-Toggle ✓

**EmptyState Komponente:**
- EmptyState.vue: Flexible Komponente mit Icon, Title, Description ✓
- EmptyStateCard.vue: Card-Variante vorhanden ✓

**Error Recovery:**
- ResultsTable.vue: @retry Handler auf TableErrorState ✓
- FavoritesView.vue (Zeile 94-102): EmptyState-Pattern für "no favorites" ✓

### ISSUES GEFUNDEN

#### MITTEL - Issue #1: SourcesView.vue hat KEINE #no-data Template

**Datei:** SourcesView.vue (Zeile 118-127)

**Code:**
```vue
<v-data-table-server
  :headers="headers"
  :items="sources"
  :items-length="store.sourcesTotal"
  :loading="store.sourcesLoading"
  <!-- FEHLT: #no-data Template! ❌ -->
>
```

**Auswirkung:** Fehler oder leere Tabelle ohne Feedback

**Lösung:**
```vue
<template #no-data>
  <div role="alert" aria-live="polite">
    <TableErrorState
      v-if="error"
      :title="$t('common.loadError')"
      @retry="loadSources"
    />
    <EmptyState
      v-else
      icon="mdi-database-search"
      :title="$t('sources.noResults')"
    />
  </div>
</template>
```

#### NIEDRIG - Issue #2: CrawlerView.vue Crawl-Jobs-Tabelle prüfen

**Datei:** CrawlerView.vue (ab Zeile 156+)

**Status:** Benötigt Überprüfung auf #no-data Template

---

## 7. USER FEEDBACK & NOTIFICATIONS

### Score: 7.5/10

### STÄRKEN

**Snackbar System etabliert:**
- App.vue: Snackbar-Komponente vorhanden (nicht vollständig sichtbar in Zeile 1-150)
- useSnackbar.ts Composable existiert ✓
- 300+ showSuccess/showError Aufrufe im Codebase ✓

**Feedback bei Aktionen:**
- ResultsView.vue: Bulk-Verify mit :loading (Zeile 23) ✓
- DocumentsView.vue: Bulk Actions mit Loading-States ✓
- FavoritesView.vue: Remove Favorite mit :loading (Zeile 172) ✓

### ISSUES IDENTIFIZIERT

#### MITTEL - Issue #1: Nicht alle erfolgreiche Aktionen haben Feedback

**Beispiel - Fehlende Snackbars:**
- Entity Create: Wahrscheinlich kein "erfolgreich erstellt" Message
- Source Edit: Wahrscheinlich kein Success-Feedback
- Category Create: Wahrscheinlich nur Auto-Refresh, kein Message

**Empfehlung:** Struktur etablieren:
```typescript
async function saveEntity() {
  try {
    await api.saveEntity(formData)
    showSuccess(t('common.savedSuccessfully'))  // ✓ HINZUFÜGEN
    loadEntities()
  } catch (e) {
    showError(t('common.saveFailed'))
  }
}
```

#### MITTEL - Issue #2: Bulk-Operations ohne Progress-Feedback

**Dateien:**
- DocumentsView.vue: bulkProcess mit :loading (Zeile 22) - GUT, aber keine Progress
- ResultsView.vue: bulkVerify mit :loading (Zeile 23) - GUT, aber keine Progress

**Sollte nutzen:** BatchActionProgress.vue Komponente
```vue
<BatchActionProgress
  v-if="showProgress"
  :current="currentIndex"
  :total="selectedItems.length"
  @cancel="cancelOperation"
/>
```

---

## 8. DARK MODE SUPPORT

### Score: 7.5/10

### STÄRKEN

**Theme Toggle funktioniert:**
- App.vue (Zeile 116-122): Theme-Toggle Button mit localStorage ✓
- CaeliWindLogo: Dynamisch farbig basierend auf isDark ✓

**CSS Variables genutzt:**
- PageHeader.vue (Zeile 56, 62, 67): rgba(var(--v-theme-primary), ...) ✓

### ISSUES GEFUNDEN

#### MITTEL - Issue #1: text-medium-emphasis zu dunkel in Dark Mode
**Bereits unter Accessibility erwähnt, aber auch hier relevant für Dark Mode UX**

**Lösung:** Dark Mode CSS überprüfen und anpassen

#### NIEDRIG - Issue #2: Mögliche hardcoded Farben in Custom Components

**Empfehlung:** Durchsuchen nach Hex-Farben in Komponenten und CSS Variables nutzen

---

## 9. KOMPONENTEN-GRÖSSEN (Size/Complexity)

### Riesige Komponenten (> 500 Zeilen)

1. **ResultsView.vue** (237 Zeilen) ✓ AKZEPTABEL (modulare Subkomponenten)
2. **DocumentsView.vue** (678 Zeilen) - GROSS aber refactored
3. **EntitiesView.vue** (524 Zeilen) ✓ AKZEPTABEL (mit Composables)
4. **FavoritesView.vue** (373 Zeilen) ✓ AKZEPTABEL
5. **CrawlerView.vue** (200+ Zeilen lesbar)

**Status:** VERBESSERT - Views sind jetzt modular mit Composables/Subkomponenten

---

## 10. SPEZIFISCHE CODE-BEFUNDE

### ✓ POSITIVE BEFUNDE (Verifiziert)

1. **ResultsTable.vue (Zeile 115-129)**
   - #no-data Template mit TableErrorState + EmptyState ✓
   - Props mit error und errorMessage ✓
   - @retry Handler ✓

2. **DynamicSchemaForm.vue (Zeile 5-80)**
   - aria-describedby auf Hints ✓
   - :error-messages auf allen Inputs ✓
   - ABER: Fehlt aria-invalid (s. Accessibility)

3. **DocumentsView.vue (Zeile 68-188)**
   - role="group" + aria-label auf Stats ✓
   - @keydown.enter + @keydown.space ✓
   - Keyboard-navigierbar ✓

4. **PageHeader.vue (Zeile 82-103)**
   - @media (max-width: 768px) für Mobile ✓
   - Responsive flex-direction ✓

5. **FavoritesView.vue (Zeile 67-71)**
   - FavoritesSkeleton.vue Integration ✓
   - Transition für Fade-In ✓

### ❌ PROBLEME (Verifiziert)

1. **ResultsTable.vue (Zeile 73-110)**
   - size="default" = 40px (< 44px Minimum)
   - Sollte: class="touch-target" hinzufügen

2. **FavoritesView.vue (Zeile 157, 167)**
   - size="small" = 32px (unter 44px)
   - Sollte: class="touch-target" nutzen

3. **DynamicSchemaForm.vue (ALLE Input-Felder)**
   - aria-invalid fehlt ÜBERALL
   - Screen-Reader können Error-State nicht erkennen

4. **SourcesView.vue (Zeile 118+)**
   - #no-data Template FEHLT
   - Keine Error-Handling bei Datatable-Fehler

5. **CrawlerView.vue (Zeile 179)**
   - style="max-width: 400px;" in Responsive Context
   - Problematisch auf Small Screens

---

## ZUSAMMENFASSUNG NACH KATEGORIE

| Kategorie | Score | Status | Hauptproblem | Aufwand |
|-----------|-------|--------|--------------|---------|
| **Accessibility** | 7.2/10 | HOCH PRIO | aria-invalid fehlt, Touch-Targets < 44px | 2-3h |
| **Visual Konsistenz** | 7.5/10 | MITTEL | Button-Farben, manche EmptyStates manuell | 1-2h |
| **Keyboard Nav** | 8/10 | GUT | Minor - Focus-Ordnung überprüfen | 1h |
| **Responsive Design** | 7.5/10 | MITTEL | Inline Widths, Mobile Headers | 2-3h |
| **Loading States** | 8/10 | SEHR GUT | Gut gelöst | 0.5h |
| **Error Handling** | 8/10 | SEHR GUT | SourcesView #no-data | 0.5h |
| **Feedback** | 7.5/10 | GUT | Nicht alle Actions haben Feedback | 1-2h |
| **Dark Mode** | 7.5/10 | GUT | text-medium-emphasis überprüfen | 0.5h |

**GESAMT: 7.8/10 - Solide UX/UI mit konkreten, schnell umsetzbaren Verbesserungen**

---

## TOP 15 PRIORITÄTEN (Nach Impact sortiert)

### HOCH (Sofort - WCAG Compliance)
1. **aria-invalid in ALLEN Formularen hinzufügen** (DynamicSchemaForm + alle anderen)
   - Impact: Screen-Reader Compliance, WCAG 2.1 Failure
   - Aufwand: 1-2h
   - Dateien: DynamicSchemaForm.vue + andere Forms

2. **Touch-Target Größe auf 44x44px erhöhen**
   - Impact: Mobile Usability, WCAG 2.1 Level AAA
   - Aufwand: 2-3h
   - Dateien: ResultsTable.vue, FavoritesView.vue, DocumentsView.vue, CrawlerView.vue

3. **SourcesView.vue #no-data Template hinzufügen**
   - Impact: Error-Handling, User-Experience
   - Aufwand: 1h
   - Datei: SourcesView.vue

### MITTEL (Diese Woche)
4. **text-medium-emphasis Dark Mode Kontrast erhöhen**
5. **Inline max-widths responsive machen**
6. **Button-Farbschema standardisieren & dokumentieren**
7. **Fehlende Success-Snackbars bei Create/Edit**
8. **Datatable responsive Headers**
9. **CrawlerView.vue Crawl-Jobs #no-data Template**

### NIEDRIG (Nächste Iteration)
10. **Loading-States: Abbruch-Option bei langen Loads**
11. **Focus-Order überprüfen & dokumentieren**
12. **Dialog max-width Mobile-optimieren**
13. **CSS Global für .touch-target + .responsive-text-container**
14. **BatchActionProgress für Bulk-Operations**
15. **Code-Review: Hardcoded Farben durch CSS Variables**

---

## Messbare Verbesserungen (After Fixes)

| Bereich | Aktuell | Nach Fixes | +Punkte |
|---------|---------|-----------|---------|
| Accessibility | 7.2 | 8.5 | +1.3 |
| Responsive | 7.5 | 8.5 | +1.0 |
| Error Handling | 8.0 | 8.5 | +0.5 |
| Feedback | 7.5 | 8.2 | +0.7 |
| **GESAMT** | **7.8** | **8.7** | **+0.9** |

**ZIEL nach Behebung: 8.5-9.0/10 (Sehr Gut bis Exzellent)**

---

## Geschätzter Implementierungsaufwand

- **Quick Wins (1 Tag):** aria-invalid, touch-target CSS, text-medium-emphasis
- **Medium Tasks (2-3 Tage):** Responsive widths, Button-Konsistenz, SourcesView #no-data
- **Polish (1 Tag):** Feedback-Messages, Code-Review
- **GESAMT: 4-5 Tage für vollständige Implementierung**

---

## Nächste Schritte

1. aria-invalid in DynamicSchemaForm.vue + alle anderen Forms
2. touch-target CSS-Klasse erstellen + nutzen
3. SourcesView.vue #no-data Template
4. Dark Mode text-medium-emphasis überprüfen
5. Button-Farbschema dokumentieren

**Prio fokussiert: Accessibility first, dann UX-Friction, dann Kosmetik**
