# Facet-Anreicherung - Implementierungs-Fortschritt

## Übersicht

| Phase | Status | Fortschritt |
|-------|--------|-------------|
| Phase 1: Backend-Grundlagen | ✅ Fertig | 4/4 |
| Phase 2: Fix PySIS-Feedback | ✅ Fertig | 3/3 |
| Phase 3: Neuer Service + Celery-Task | ✅ Fertig | 5/5 |
| Phase 4: Frontend - Multi-Checkbox-Dropdown | ✅ Fertig | 5/5 |
| Phase 5: Frontend - Review-Modal | ✅ Fertig | 6/6 |
| Phase 6: Assistant-Integration | ✅ Fertig | 2/2 |

---

## Phase 1: Backend-Grundlagen

- [x] AITaskType erweitern (ENTITY_DATA_ANALYSIS) + Alembic-Migration
- [x] AITask Model: result_data Feld für Preview-Daten prüfen/hinzufügen
- [x] AI-Tasks Status-Endpoint (`backend/app/api/v1/ai_tasks.py`)
- [x] Error-Handling in Workers verbessern (keine silent returns)

---

## Phase 2: Fix PySIS-Feedback

- [x] Frontend API erweitern (getAiTaskStatus)
- [x] Polling-Logik in EntityDetailView
- [x] Progress-Dialog UI

---

## Phase 3: Neuer Service + Celery-Task

- [x] EntityDataFacetService mit `get_enrichment_sources()` (inkl. Zeitstempel)
- [x] EntityDataFacetService mit `analyze_entity_data_for_facets()` (speichert Preview)
- [x] EntityDataFacetService mit `apply_changes()` (wendet ausgewählte Änderungen an)
- [x] Celery-Task `analyze_entity_data_for_facets` (erstellt Preview, speichert nicht direkt)
- [x] API-Endpoints `/v1/entity-data/*` (4 Endpoints)

**Erstellte Dateien:**
- `backend/services/entity_data_facet_service.py` - Neuer Service
- `backend/app/api/v1/entity_data.py` - Neue API-Endpoints
- `backend/workers/ai_tasks.py` - Neuer Celery-Task hinzugefügt

---

## Phase 4: Frontend - Multi-Checkbox-Dropdown

- [x] Bestehenden PySIS-Button durch Multi-Checkbox-Dropdown ersetzen
- [x] `loadEnrichmentSources()` beim Öffnen des Dropdowns
- [x] Zeitstempel-Anzeige pro Datenquelle
- [x] Unified `startEnrichment()` Funktion
- [x] Task-Polling mit Progress-Feedback (Modal bleibt offen)

---

## Phase 5: Frontend - Review-Modal

- [x] Neue Komponente `FacetEnrichmentReview.vue`
- [x] Tabs: Neue Facets / Änderungen
- [x] Vorher/Nachher-Diff-Anzeige für Updates
- [x] Checkboxen für Akzeptieren/Ablehnen pro Eintrag
- [x] Alle auswählen / Keine auswählen Buttons
- [x] `applyChanges()` API-Aufruf mit ausgewählten Änderungen

**Erstellte Dateien:**
- `frontend/src/components/FacetEnrichmentReview.vue` - Review-Modal Komponente

**Besonderheiten:**
- Modal bleibt während der Analyse offen (kein Hintergrund-Task)
- Minimieren-Funktion mit klickbarem Toast zur Rückkehr
- Auto-Select für Vorschläge mit hoher Konfidenz (>70%)
- Diff-Anzeige für Updates mit Vorher/Nachher-Vergleich

---

## Phase 6: Assistant-Integration

- [x] Intent-Classification erweitern
- [x] Handler für analyze_entity_data

**Änderungen:**
- `backend/services/assistant_service.py`:
  - Neuer Context-Action `analyze_entity_data` im Intent-Classification-Prompt
  - Beispiele für Entity-Daten-Analyse hinzugefügt
  - Handler für `analyze_entity_data` implementiert

**Beispiel-Prompts die jetzt funktionieren:**
- "Analysiere die Verknüpfungen für neue Pain Points"
- "Schreibe Facets basierend auf den Relationen"
- "Reichere Facets aus den Dokumenten an"
- "Analysiere alle Daten und erstelle neue Facets"

---

## Zusammenfassung

**Alle 6 Phasen sind abgeschlossen!**

### Erstellte/Geänderte Dateien:

**Backend:**
- `backend/app/models/ai_task.py` - AITaskType + result_data + entity_id
- `backend/alembic/versions/ac1234567917_add_entity_data_analysis_task.py` - Migration
- `backend/app/api/v1/ai_tasks.py` - Task-Status-Endpoints
- `backend/app/api/v1/entity_data.py` - Entity-Daten-Enrichment-Endpoints
- `backend/services/entity_data_facet_service.py` - Neuer Service
- `backend/workers/ai_tasks.py` - Neuer Celery-Task
- `backend/services/assistant_service.py` - Intent-Classification + Handler
- `backend/app/main.py` - Router-Registrierungen

**Frontend:**
- `frontend/src/components/FacetEnrichmentReview.vue` - Review-Modal
- `frontend/src/views/EntityDetailView.vue` - Multi-Checkbox-Dropdown + Integration
- `frontend/src/services/api.ts` - API-Erweiterungen
- `frontend/src/locales/de/entities.json` - Deutsche Übersetzungen
- `frontend/src/locales/en/entities.json` - Englische Übersetzungen

### Features:

1. **Multi-Source Enrichment**: Analyse von PySIS, Relationen, Dokumenten, Extraktionen
2. **Preview-Workflow**: Änderungen werden erst nach Bestätigung angewendet
3. **Visual Progress**: Modal zeigt Fortschritt während der Analyse
4. **Review-UI**: Tabs für neue Facets und Updates, Diff-Anzeige
5. **Confidence Scoring**: Automatische Auswahl von Vorschlägen mit hoher Konfidenz
6. **Minimieren**: Task kann minimiert werden, Toast führt zurück
7. **Assistant-Integration**: Natürlichsprachliche Befehle für Facet-Analyse
