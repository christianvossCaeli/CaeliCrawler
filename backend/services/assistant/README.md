# Assistant Service Module

## Übersicht

Das Assistant Service Modul ist ein KI-gestützter Chat-Assistent für die CaeliCrawler-App. Die ursprüngliche 2229 Zeilen große Datei wurde in kleinere, fokussierte Module aufgeteilt, um die Wartbarkeit und Verständlichkeit zu verbessern.

## Module-Struktur

### 1. `common.py` (197 LOC, 5.6K)
Gemeinsame Utilities und Client-Initialisierung

**Exports:**
- `get_openai_client()` - Azure OpenAI Client Factory
- `validate_entity_context()` - Entity ID Validierung
- `build_suggestions_list()` - Smart Suggestions Builder
- `format_count_message()` - Count Message Formatter
- `get_entity_with_context()` - Entity Context Loader
- Custom Exceptions: `EntityNotFoundException`, `AIServiceNotAvailableException`

**Zweck:** Zentralisiert die Azure OpenAI Client-Verwaltung und bietet wiederverwendbare Utility-Funktionen für Entity-Validierung und Suggestion-Building.

### 2. `context_builder.py` (305 LOC, 8.1K)
Kontext-Building und Entity-Daten-Sammlung

**Exports:**
- `build_entity_context()` - Vollständiger Entity-Kontext
- `build_facet_summary()` - Facet-Gruppierung nach Typ
- `build_pysis_context()` - PySIS-Daten-Extraktion
- `count_entity_relations()` - Relations-Counter
- `get_facet_counts_by_type()` - Facet-Counts gruppiert
- `build_app_summary_context()` - App-Level Statistiken
- `build_entity_summary_for_prompt()` - Text-Summary für AI
- `prepare_entity_data_for_ai()` - JSON-Formatter für AI

**Zweck:** Sammelt und aggregiert Entity-Daten aus verschiedenen Quellen (Core Attributes, Facets, PySIS, Relations) für die AI-Verarbeitung.

### 3. `query_handler.py` (506 LOC, 17K)
Query-Processing und Suchanfragen

**Exports:**
- `handle_query()` - Datenbank-Queries via SmartQueryService
- `handle_context_query()` - Queries über aktuelle Entity
- `generate_context_response_with_ai()` - AI-generierte Antworten
- `suggest_corrections()` - Typo-Korrektur und Fuzzy-Matching
- `format_query_result_message()` - Result-Message Formatter
- `build_query_suggestions()` - Query-basierte Suggestions
- `build_context_query_suggestions()` - Context-basierte Suggestions

**Zweck:** Verarbeitet alle Such- und Query-Operationen, inklusive intelligenter Fehlerkorrektur bei leeren Ergebnissen.

### 4. `action_executor.py` (409 LOC, 13K)
Action-Execution und Batch-Operationen

**Exports:**
- `execute_action()` - Single Entity Updates
- `execute_batch_action()` - Batch-Operationen
- `preview_inline_edit()` - Inline-Edit Preview
- `handle_batch_action_intent()` - Chat-basierte Batch Actions
- `parse_batch_filter()` - Filter-Parser
- `parse_action_data()` - Action-Data Parser

**Zweck:** Führt User-Aktionen aus, sowohl einzeln als auch als Batch-Operationen mit Preview/Confirm-Workflow.

### 5. `response_formatter.py` (594 LOC, 18K)
Response-Formatierung und Präsentation

**Exports:**
- `generate_help_response()` - Kontextuelle Hilfe
- `handle_navigation()` - Navigation Requests
- `handle_summarize()` - Entity/App Summaries
- `handle_image_analysis()` - Vision API Integration
- `handle_discussion()` - Dokument/Diskussions-Analyse
- `suggest_smart_query_redirect()` - Smart Query Redirect

**Zweck:** Formatiert verschiedene Response-Typen (Help, Navigation, Summary, Image Analysis, Discussion) für die Präsentation.

### 6. `context_actions.py` (732 LOC, 28K) - Existiert bereits
Context-aware Entity Actions

**Exports:**
- `handle_context_action()` - Haupt-Handler für Context Actions

**Zweck:** Behandelt kontextbezogene Aktionen auf Entities (PySIS-Analyse, Facet-Anreicherung, Crawls, etc.).

### 7. `facet_management.py` (350 LOC, 11K)
Facet-Type Management

**Exports:**
- `handle_facet_management_request()` - Facet-Type Management Handler

**Zweck:** Verwaltung von Facet-Typen (Listen, Erstellen, Zuweisen, AI-Suggestions).

### 8. `prompts.py` (234 LOC, 11K) - Existiert bereits
LLM Prompt Templates

**Exports:**
- Alle Prompt-Templates für verschiedene Intent-Typen

### 9. `utils.py` (62 LOC, 1.8K) - Existiert bereits
Allgemeine Utility-Funktionen

**Exports:**
- `format_entity_link()` - Entity-Link Formatter
- `extract_json_from_response()` - JSON-Extraktor
- `truncate_for_prompt()` - Text-Truncation
- `safe_json_loads()` - Safe JSON Parser
- `format_entity_summary()` - Entity Summary Formatter

### 10. `__init__.py` (161 LOC, 4.3K)
Export-Definitionen

Exportiert alle öffentlichen Funktionen und Klassen der Sub-Module.

## Hauptdatei

### `assistant_service.py` (553 LOC, reduziert von 2229 LOC)
Orchestrierungs-Schicht

**Klasse:** `AssistantService`

**Hauptmethoden:**
- `process_message()` - Haupt-Entry-Point für Message-Processing
- `execute_action()` - Public API für Action-Execution
- `execute_batch_action()` - Public API für Batch-Actions
- `process_message_stream()` - Streaming Response Support

**Zweck:** Schlanke Orchestrierungsschicht, die Intent-Classification durchführt und an spezialisierte Handler delegiert.

## Vorteile der Modularisierung

1. **Wartbarkeit**: Jedes Modul hat eine klare Verantwortlichkeit (Single Responsibility Principle)
2. **Testbarkeit**: Module können einzeln getestet werden
3. **Übersichtlichkeit**: Maximal ~600 LOC pro Modul (statt 2229 LOC monolithisch)
4. **Wiederverwendbarkeit**: Funktionen können in anderen Services genutzt werden
5. **Backward Compatibility**: Alle bestehenden Imports funktionieren weiterhin über `__init__.py`

## Breaking Changes

**Keine** - Die Refaktorierung erhält vollständige Backward-Kompatibilität:
- `AssistantService` Klasse bleibt unverändert exportiert
- Alle öffentlichen Methoden bleiben gleich
- Imports über `services.assistant_service` funktionieren weiterhin

## Migration für neue Entwicklungen

Für neue Features können Entwickler jetzt gezielt das passende Modul wählen:

```python
# Statt alles aus assistant_service zu importieren:
from services.assistant_service import AssistantService

# Kann man jetzt spezifische Module nutzen:
from services.assistant.query_handler import handle_query
from services.assistant.context_builder import build_entity_context
from services.assistant.action_executor import execute_batch_action
```

## Dateigrößen-Vergleich

| Datei | LOC | Größe | Zweck |
|-------|-----|-------|-------|
| **Original** | 2229 | 86K | Monolithisch |
| **Neu: assistant_service.py** | 553 | 19K | Orchestrierung |
| common.py | 197 | 5.6K | Utilities |
| context_builder.py | 305 | 8.1K | Context Building |
| query_handler.py | 506 | 17K | Query Processing |
| action_executor.py | 409 | 13K | Actions |
| response_formatter.py | 594 | 18K | Formatting |
| facet_management.py | 350 | 11K | Facet Management |
| **Gesamt (alle Module)** | 3550 | ~120K | Modular |

## Code-Qualität

- ✅ Alle Module haben umfassende Docstrings
- ✅ Type Hints durchgängig verwendet
- ✅ Klare Verantwortlichkeiten (SRP)
- ✅ Keine zyklischen Abhängigkeiten
- ✅ Syntaktisch valide (geprüft mit py_compile)
- ✅ Logging konsistent über structlog
- ✅ Error Handling standardisiert

## Next Steps

Für weitere Verbesserungen könnten folgende Schritte sinnvoll sein:

1. **Unit Tests**: Tests für jedes Modul erstellen
2. **Integration Tests**: End-to-End Tests für AssistantService
3. **Performance Profiling**: Identifikation von Bottlenecks
4. **Streaming Improvements**: Vollständige Streaming-Implementierung in Handlern
5. **Cache Optimization**: Intelligenteres Caching von Facet Types und Entity Data
