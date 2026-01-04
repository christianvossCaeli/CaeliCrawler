# Categories/Analysethemen Audit - 2026-01-04

## Gesamtbewertung: 3/5

Das Categories-Feature ist funktional solide, hat aber signifikante Verbesserungsmöglichkeiten in Modularität und Testabdeckung.

## Struktur

### Frontend (~1.500 Zeilen)
- **View:** CategoriesView.vue (704 Zeilen) - verwaltet 7 Dialog-States
- **Komponenten:** 13 in /components/categories/
- **Composables:** 3 (useCategoriesView, useCategoryCrawler, useCategoryDataSources)
- **Types:** /types/category.ts (269 Zeilen)
- **KEIN Pinia Store** - State in Composables verteilt

### Backend (~1.100 Zeilen API)
- **API:** /api/admin/categories.py (1133 Zeilen) - gut strukturiert
- **Schemas:** /schemas/category.py (522 Zeilen) - gute Validierung
- **Model:** /models/category.py (248 Zeilen)

## Hauptprobleme

| Bereich | Problem | Priorität |
|---------|---------|-----------|
| Modularität | CategoriesView.vue zu groß (704 Zeilen, 7 Dialogs) | CRITICAL |
| Types | Duplicate Category Interface in Composable | HIGH |
| API | Categories API gemischt mit Sources in sources.ts | HIGH |
| Validierung | Keine Frontend-Validierung (nur Backend Pydantic) | HIGH |
| Testing | Keine Unit/Component Tests | CRITICAL |
| State | Kein Pinia Store - verteilter State | MEDIUM |

## Positive Aspekte
- Gute TypeScript-Basis in types/category.ts
- Saubere Tab-Struktur in CategoryEditForm
- Backend gut strukturiert mit umfassender Validierung
- AI Setup Preview funktional implementiert
- CategoriesSkeleton.vue für Loading-States

## Empfohlene Maßnahmen

### Phase 1: Types & API
- Types konsolidieren (single source of truth)
- API Client separieren (categories.ts)

### Phase 2: View & Composables
- CategoriesView aufteilen (CategoryDialogsManager)
- Composables reorganisieren (useCategoryDialogs, useCategoryAiSetup)

### Phase 3: State Management
- Pinia Store erstellen (stores/categories.ts)

### Phase 4: Validierung
- VeeValidate für CategoryEditForm

### Phase 5: Testing
- Unit Tests für Composables
- Component Tests für kritische Komponenten

### Phase 6-7: UX & State of the Art
- Accessibility verbessern
- SSE Integration
- defineModel Migration
