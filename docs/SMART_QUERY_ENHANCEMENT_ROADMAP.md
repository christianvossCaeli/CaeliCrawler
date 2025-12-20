# Smart Query & KI-Assistent Enhancement Roadmap

> Fortschrittsdokumentation für die Erweiterung des Smart Query Systems und KI-Assistenten.
>
> **Legende:** ⬜ Offen | 🔄 In Arbeit | ✅ Abgeschlossen | ⏸️ Pausiert

---

## Meilenstein 1: Basis-Erweiterungen
**Ziel:** Quick Wins ohne Breaking Changes

### 1.1 Datumsbereich-Filter
- [x] `prompts.py`: Neues Feld `date_range: { start, end }` im Output-Schema
- [x] `prompts.py`: Beispiele für Datumsbereich-Queries hinzufügen
- [x] `query_executor.py`: BETWEEN-Clause implementieren
- [x] `query_executor.py`: Fallback auf future/past wenn kein Range
- [x] Tests: Unit-Tests für Datumsbereich-Filter (test_smart_query_advanced.py)
- [x] Dokumentation: API-Docs aktualisiert (API_REFERENCE.md)

### 1.2 Fuzzy-Matching für Geo-Aliase
- [x] `geographic_utils.py`: Levenshtein-Distanz-Funktion hinzufügen
- [x] `geographic_utils.py`: `suggest_correction()` Funktion
- [x] `geographic_utils.py`: Threshold konfigurierbar (default: 2)
- [x] `assistant_service.py`: Integration der Suggestions (_suggest_corrections)
- [x] Tests: Fuzzy-Matching Tests (test_geographic_utils.py)
- [x] Dokumentation: Hilfe-Texte aktualisiert

### 1.3 Query-History (Frontend)
- [x] `useAssistant.ts`: `QueryHistoryItem` Interface definieren
- [x] `useAssistant.ts`: `queryHistory` State hinzufügen
- [x] `useAssistant.ts`: `addToHistory()`, `toggleFavorite()` Funktionen
- [x] `useAssistant.ts`: LocalStorage Persistenz
- [x] `QueryHistoryPanel.vue`: Neue Komponente erstellt (Filter, Favoriten, Rerun)
- [x] `ChatWindow.vue`: History-Panel integriert (Toggle-Button, Slide-Transition)
- [x] Lokalisierung: DE/EN Texte für History-Panel (queryHistory Objekt)

---

## Meilenstein 2: Sprachverständnis erweitern
**Ziel:** Ausdrucksstärke der Queries erhöhen

### 2.1 Boolean-Operatoren (AND/OR)
- [x] `prompts.py`: `filters.logical_operator` zum Schema hinzufügen
- [x] `prompts.py`: OR-Beispiele im Prompt
- [x] `prompts.py`: AND-Beispiele für Facet-Kombinationen
- [x] `query_interpreter.py`: Response-Parsing erweitern
- [x] `query_executor.py`: `_build_filter_conditions()` für OR
- [x] `query_executor.py`: `_build_facet_filter()` für AND/OR
- [x] Tests: Boolean-Operator Tests (test_smart_query_advanced.py)
- [x] Dokumentation: Query-Syntax-Guide (API_REFERENCE.md)

### 2.2 Negation Support (NOT/OHNE)
- [x] `prompts.py`: `negative_facet_types` Feld hinzufügen
- [x] `prompts.py`: `negative_location_filter` Feld hinzufügen
- [x] `prompts.py`: Negations-Beispiele ("OHNE", "NICHT")
- [x] `query_executor.py`: NOT EXISTS Subquery
- [x] `query_executor.py`: NOT IN für Locations
- [x] Tests: Negation Tests (test_smart_query_advanced.py)
- [x] Dokumentation: API_REFERENCE.md aktualisiert

### 2.3 Aggregations-Queries
- [x] `prompts.py`: `query_type: aggregate` hinzufügen
- [x] `prompts.py`: `aggregate_function: COUNT|AVG|SUM|MIN|MAX`
- [x] `prompts.py`: `group_by` optional field
- [x] `query_executor.py`: `_execute_aggregate_query()` implementieren
- [x] `query_executor.py`: Ergebnis-Formatierung mit deutschen Labels
- [x] Tests: Aggregation Tests (test_smart_query_advanced.py)
- [x] Dokumentation: Aggregations-Beispiele (API_REFERENCE.md)

---

## Meilenstein 3: Neue Operationen
**Ziel:** Feature-Set vervollständigen

### 3.1 Delete-Operationen
- [x] `prompts.py`: `delete_entity`, `delete_facet`, `batch_delete` Operationen
- [x] `prompts.py`: Trigger-Phrasen ("Lösche", "Entferne", "Delete")
- [x] `prompts.py`: JSON-Schema für delete_entity_data, delete_facet_data, batch_delete_data
- [x] `write_executor.py`: `execute_delete_entity()` (Soft-Delete)
- [x] `write_executor.py`: `execute_delete_facet()`
- [x] `write_executor.py`: `execute_batch_delete()` mit dry_run
- [x] Frontend: ActionPreview für Delete-Bestätigung erweitert (rote Styling, Warning-Alert)
- [x] Tests: Delete-Operation Tests (test_smart_query_advanced.py)
- [x] Dokumentation: API_REFERENCE.md aktualisiert

### 3.2 Export aus Query
- [x] `prompts.py`: `export_query_result` Operation
- [x] `prompts.py`: `format: csv|json|excel` und export_data Schema
- [x] `write_executor.py`: `execute_export()` mit JSON, CSV, Excel Support
- [x] Facet-Bulk-Loading für Performance
- [x] Async Job für große Exports (>5000 Datensätze) - Celery Task + ExportJob Model
- [x] Frontend: Export-Progress anzeigen (ExportProgressPanel.vue)
- [x] Tests: Export Tests (test_smart_query_advanced.py)
- [x] Dokumentation: API_REFERENCE.md aktualisiert

### 3.3 UNDO-System
- [x] EntityVersion Model nutzen (kein neues Model nötig - nutzt Diff-basiertes Tracking)
- [x] `services/change_tracker.py`: ChangeTracker Service erstellt
- [x] `change_tracker.py`: `record_entity_change()` implementiert
- [x] `change_tracker.py`: `record_facet_change()` implementiert
- [x] `change_tracker.py`: `undo_last_change()` implementiert
- [x] `change_tracker.py`: `get_change_history()` implementiert
- [x] `change_tracker.py`: `get_recent_changes()` implementiert
- [x] `write_executor.py`: `execute_undo()` Handler
- [x] `write_executor.py`: `execute_get_history()` Handler
- [x] `prompts.py`: UNDO Intent-Erkennung (undo_change, get_change_history)
- [x] Frontend: UNDO-Button in ActionPreview (blaues Info-Styling, Info-Alert)
- [x] Tests: UNDO Tests (test_smart_query_advanced.py)
- [x] Dokumentation: API_REFERENCE.md aktualisiert

---

## Meilenstein 4: Multi-Hop Relationen
**Ziel:** Komplexe Abfragen über mehrere Entity-Beziehungen

### 4.1 Relation Resolver
- [x] `relation_resolver.py`: Neue Datei erstellt (RelationResolver, RelationHop, RelationChain)
- [x] `relation_resolver.py`: Recursive Query Builder (resolve_relation_chain)
- [x] `relation_resolver.py`: Max Depth Konfiguration (MAX_RELATION_DEPTH = 3)
- [x] `relation_resolver.py`: Caching für Relation/Facet/EntityTypes (CACHE_TTL = 300s)
- [x] `relation_resolver.py`: resolve_entities_with_related_facets() für komplexe Queries
- [x] `relation_resolver.py`: get_relation_path_details() für Pfad-Erklärungen
- [x] Performance-Tests mit großen Datenmengen (TestMultiHopPerformance - 8 Tests)

### 4.2 Integration
- [x] `query_interpreter.py`: Extended `relation_chain` Format mit Filtern pro Hop
- [x] `query_interpreter.py`: Multi-Hop Beispiele im Prompt
- [x] `query_interpreter.py`: target_facets_at_chain_end, negative_facets_at_chain_end
- [x] `query_executor.py`: RelationResolver Integration
- [x] `query_executor.py`: Multi-Hop Support für COUNT, LIST, AGGREGATE queries
- [x] `query_executor.py`: parse_relation_chain_from_query() Helper
- [x] Tests: Multi-Hop Query Tests (test_smart_query_advanced.py)
- [x] Dokumentation: Multi-Hop Beispiele (API_REFERENCE.md)

---

## Meilenstein 5: UX-Verbesserungen
**Ziel:** Benutzererfahrung optimieren

### 5.1 Intelligente Fehlerbehandlung
- [x] `assistant_service.py`: `_suggest_corrections()` Methode implementiert
- [x] `assistant_service.py`: Integration mit Fuzzy-Geo (geographic_utils)
- [x] `assistant_service.py`: Entity-Type und Facet-Type Vorschläge
- [x] `schemas/assistant.py`: QuerySuggestion Schema
- [x] `schemas/assistant.py`: suggestions Feld in QueryResultData
- [x] `_handle_query()`: Automatische Vorschläge bei leeren Ergebnissen
- [x] `ChatMessage.vue`: Suggestion-Chips UI mit Icons
- [x] `ChatMessage.vue`: "Meinten Sie...?" Anzeige
- [x] `ChatWindow.vue`: handleSuggestionClick Handler
- [x] Lokalisierung: DE/EN Texte (didYouMean, suggestion*)
- [x] Tests: Suggestion Tests (test_smart_query_advanced.py)

### 5.2 Kontextuelle Hilfe-Hints
- [x] `InputHints.vue`: Neue Komponente erstellt
- [x] `InputHints.vue`: Dynamische Tipps basierend auf Eingabe (13 Kategorien)
- [x] `InputHints.vue`: Trigger-Word Highlighting
- [x] `ChatWindow.vue`: Integration
- [x] Lokalisierung: DE/EN Texte (hintsTitle, hintClickToUse)
- [x] Tests: Implizit durch TypeScript-Check

### 5.3 Smart Query Redirect (Bonus)
- [x] `ChatAssistant.vue`: queryContextStore Integration
- [x] `ChatMessage.vue`: smart-query-redirect Event
- [x] `ChatWindow.vue`: handleSmartQueryRedirect Handler
- [x] `queryContextStore.ts`: prefilled_query Weitergabe

---

## Meilenstein 6: Dokumentation
**Ziel:** Vollständige und aktuelle Dokumentation

### 6.1 API-Dokumentation
- [x] `docs/API_REFERENCE.md`: Query-Syntax-Referenz
- [x] `docs/API_REFERENCE.md`: Boolean-Operatoren Sektion
- [x] `docs/API_REFERENCE.md`: Aggregations-Sektion
- [x] `docs/API_REFERENCE.md`: Delete-Operationen Sektion
- [x] `docs/API_REFERENCE.md`: Export-Sektion
- [x] `docs/API_REFERENCE.md`: UNDO-Sektion
- [x] `docs/API_REFERENCE.md`: Multi-Hop Relationen Sektion

### 6.2 Frontend-Hilfe
- [x] `locales/de/help/features.json`: Smart Query Features
- [x] `locales/en/help/features.json`: Smart Query Features
- [x] Query-Syntax Beispiele in Help-Files
- [x] Boolean-Operatoren Erklärung in Help-Files
- [x] Tipps & Tricks in Help-Files
- [ ] Video/GIF Tutorials (optional, niedrige Priorität)

### 6.3 Inline-Dokumentation
- [x] Python: Docstrings für alle neuen Funktionen
- [x] Python: Type-Hints vollständig
- [x] TypeScript: Interfaces dokumentiert
- [x] TypeScript: defineEmits/defineProps typisiert

---

## Fortschritts-Übersicht

| Meilenstein | Status | Fortschritt |
|-------------|--------|-------------|
| 1. Basis-Erweiterungen | ✅ Abgeschlossen | 17/17 |
| 2. Sprachverständnis | ✅ Abgeschlossen | 21/21 |
| 3. Neue Operationen | ✅ Abgeschlossen | 28/28 |
| 4. Multi-Hop Relationen | ✅ Abgeschlossen | 14/14 |
| 5. UX-Verbesserungen | ✅ Abgeschlossen | 22/22 |
| 6. Dokumentation | ✅ Abgeschlossen | 16/17 |
| **Gesamt** | ✅ Abgeschlossen | **118/119** |

---

## Offene Tasks (Niedrige Priorität)

Die folgenden Items sind nice-to-have und haben niedrige Priorität:

1. **Video Tutorials** - Optional (keine technische Abhängigkeit)

---

## Änderungsprotokoll

| Datum | Änderung |
|-------|----------|
| 2025-12-20 | Initial Roadmap erstellt |
| 2025-12-20 | Meilenstein 1.1-1.3 Backend implementiert |
| 2025-12-20 | Meilenstein 2.1-2.3 Backend implementiert (Boolean, Negation, Aggregations) |
| 2025-12-20 | Meilenstein 3.1 Delete-Operationen Backend implementiert |
| 2025-12-20 | Meilenstein 3.2 Export aus Query Backend implementiert |
| 2025-12-20 | Meilenstein 3.3 UNDO-System implementiert (ChangeTracker Service) |
| 2025-12-20 | Meilenstein 4 Multi-Hop Relationen implementiert (RelationResolver) |
| 2025-12-20 | Meilenstein 5.1 Intelligente Fehlerbehandlung Backend implementiert (_suggest_corrections) |
| 2025-12-20 | Meilenstein 5.1 Frontend Suggestion-Chips UI implementiert (ChatMessage.vue, ChatWindow.vue) |
| 2025-12-20 | Meilenstein 5.2 InputHints.vue Komponente erstellt und integriert |
| 2025-12-20 | Meilenstein 6.1 API-Dokumentation aktualisiert (Boolean, Negation, Aggregations, Delete, Export, UNDO, Multi-Hop) |
| 2025-12-20 | Meilenstein 6.2 Frontend-Hilfe erweitert (Smart Query Sektion in DE/EN help files) |
| 2025-12-20 | Meilenstein 6.3 Inline-Dokumentation verifiziert (Docstrings vorhanden) |
| 2025-12-20 | Tests: 46 Unit-Tests für neue Features erstellt (test_smart_query_advanced.py, test_geographic_utils.py) |
| 2025-12-20 | Fix: KI-Assistent → Smart Query Redirect mit prefilled_query Integration (queryContextStore) |
| 2025-12-20 | Audit: Roadmap-Checkboxen aktualisiert, tatsächlichen Stand reflektiert |
| 2025-12-20 | QueryHistoryPanel.vue erstellt mit Filter, Favoriten, Rerun-Funktion |
| 2025-12-20 | ChatWindow.vue: History-Panel integriert mit Toggle-Button und Slide-Transition |
| 2025-12-20 | ActionPreview.vue erweitert für Delete (rot) und UNDO (blau) mit Alerts |
| 2025-12-20 | Lokalisierung: DE/EN Texte für queryHistory und Delete/UNDO UI hinzugefügt |
| 2025-12-20 | **Fortschritt: 115/119 Tasks abgeschlossen (96.6%)** |
| 2025-12-20 | Async Export Job implementiert (workers/export_tasks.py, ExportJob Model) |
| 2025-12-20 | ExportProgressPanel.vue für Frontend Export-Fortschritt erstellt |
| 2025-12-20 | ExportView.vue erweitert mit Async Export UI |
| 2025-12-20 | Performance-Tests für Multi-Hop Relationen (TestMultiHopPerformance - 8 Tests) |
| 2025-12-20 | API-Dokumentation: Async Export Endpoints dokumentiert (API_REFERENCE.md) |
| 2025-12-20 | Frontend-Hilfe: Async Export und Query History Sektion hinzugefügt (DE/EN) |
| 2025-12-20 | **Fortschritt: 118/119 Tasks abgeschlossen (99.2%)** |
