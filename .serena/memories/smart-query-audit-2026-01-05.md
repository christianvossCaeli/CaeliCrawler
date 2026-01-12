# Smart Query System Audit - 2026-01-05

## Übersicht

Dieses Audit analysiert die Vollständigkeit und Korrektheit der Read, Write und Plan Modi im Smart Query System.

---

## 1. READ MODE

### Datei: `interpreters/read_interpreter.py`

**Funktion:** `interpret_query()` + `build_dynamic_query_prompt()`

### Unterstützte Features ✅

| Feature | Status | Beschreibung |
|---------|--------|--------------|
| Query Types | ✅ | `list`, `count`, `aggregate` |
| Entity Type Filter | ✅ | Dynamisch aus DB geladen |
| Facet Type Filter | ✅ | Dynamisch aus DB geladen |
| Time Filter | ✅ | `future_only`, `past_only`, `all` |
| Date Range | ✅ | `start`, `end` für spezifische Zeiträume |
| Multi-Hop Relations | ✅ | `relation_chain` mit `direction` |
| Boolean Operators | ✅ | `AND`/`OR` für Facets und Locations |
| Negation | ✅ | `negative_facet_types`, `negative_locations` |
| Aggregate Functions | ✅ | `COUNT`, `SUM`, `AVG`, `MIN`, `MAX` |
| Group By | ✅ | `entity_type`, `admin_level_1`, `country`, `facet_type` |
| Regional Filter | ✅ | `country` (ISO), `admin_level_1` (Bundesländer) |

### Visualisierungen ✅

| Typ | Status | Trigger |
|-----|--------|---------|
| `table` | ✅ | Standard, Listen |
| `bar_chart` | ✅ | Kategorievergleiche |
| `line_chart` | ✅ | Zeitverläufe |
| `pie_chart` | ✅ | Anteile/Prozente |
| `stat_card` | ✅ | Einzelwerte |
| `map` | ✅ | Geografische Daten |
| `comparison` | ✅ | 2-3 Entities vergleichen |
| `text` | ✅ | Textuelle Antworten |

### Relation Types im Prompt

- `works_for` ✅
- `attends` ✅
- `located_in` ✅
- `member_of` ✅

**HINWEIS:** Relation Types sind statisch im Prompt hardcoded. Sollten dynamisch aus DB geladen werden!

---

## 2. WRITE MODE

### Datei: `interpreters/write_interpreter.py` + `write_executor.py`

### Operationen Vergleich

#### ✅ Dokumentiert UND Implementiert

| Operation | Im Prompt | Implementiert | Handler |
|-----------|-----------|---------------|---------|
| `create_entity_type` | ✅ | ✅ | write_executor (direkt) |
| `create_entity` | ✅ | ✅ | write_executor (direkt) |
| `create_facet` | ✅ | ✅ | write_executor (direkt) |
| `create_relation` | ✅ | ✅ | write_executor (direkt) |
| `create_facet_type` | ✅ | ✅ | facet_ops.py |
| `assign_facet_type` | ✅ | ✅ | facet_ops.py |
| `add_history_point` | ✅ | ✅ | facet_ops.py |
| `fetch_and_create_from_api` | ✅ | ✅ | api_import_ops.py |
| `create_category_setup` | ✅ | ✅ | write_executor (direkt) → category_setup.py |
| `start_crawl` | ✅ | ✅ | write_executor (direkt) |
| `analyze_pysis` | ✅ | ✅ | pysis_ops.py |
| `enrich_facets_from_pysis` | ✅ | ✅ | pysis_ops.py |
| `push_to_pysis` | ✅ | ✅ | pysis_ops.py |
| `combined` | ✅ | ✅ | write_executor (direkt) |
| `query_data` | ✅ | ✅ | query_executor.py |
| `query_external` | ✅ | ✅ | query_executor.py |
| `query_facet_history` | ✅ | ✅ | query_executor.py |

#### ❌ Implementiert aber NICHT Dokumentiert

| Operation | Implementiert | Handler | Problem |
|-----------|---------------|---------|---------|
| `update_entity` | ✅ | entity_ops.py | Nicht im Write-Prompt! |
| `delete_entity` | ✅ | entity_ops.py | Nicht im Write-Prompt! |
| `update_crawl_schedule` | ✅ | schedule_ops.py | Nicht im Write-Prompt! |
| `batch_operation` | ✅ | batch_ops.py | Nicht im Write-Prompt! |
| `batch_delete` | ✅ | batch_ops.py | Nicht im Write-Prompt! |
| `export` | ✅ | export_ops.py | Nicht im Write-Prompt! |
| `undo` | ✅ | export_ops.py | Nicht im Write-Prompt! |
| `get_history` | ✅ | export_ops.py | Nicht im Write-Prompt! |
| `discover_sources` | ✅ | discovery.py | Nicht im Write-Prompt! |
| `link_category_entity_types` | ✅ | category_ops.py | Nicht im Write-Prompt! |
| `link_existing_category` | ✅ | category_ops.py | Nicht im Write-Prompt! |
| `create_relation_type` | ✅ | category_ops.py | Nicht im Write-Prompt! |
| `assign_facet_types` | ✅ | category_ops.py | Nicht im Write-Prompt! |
| `delete_facet` | ✅ | facet_ops.py | Nicht im Write-Prompt! |

#### ⚠️ Dokumentiert aber NICHT Implementiert

| Operation | Im Prompt | Problem |
|-----------|-----------|---------|
| `setup_api_facet_sync` | ✅ | **NICHT IMPLEMENTIERT!** |
| `trigger_api_sync` | ✅ | **NICHT IMPLEMENTIERT!** |

---

## 3. PLAN MODE

### Datei: `interpreters/plan_interpreter.py` + `prompts.py:build_plan_mode_prompt()`

### Status nach Refactoring ✅

Der Plan-Mode Prompt wurde auf **dynamische Generierung** umgestellt:

- `get_operations_documentation()` - Lädt Operationen aus OPERATIONS_REGISTRY
- `get_query_operations_documentation()` - Dokumentiert Query-Operationen

### Dynamisch geladen

| Komponente | Quelle |
|------------|--------|
| Entity Types | DB (dynamisch) |
| Facet Types | DB (dynamisch) |
| Relation Types | DB (dynamisch) |
| Categories | DB (dynamisch) |
| Write Operations | OPERATIONS_REGISTRY (dynamisch) |
| Query Operations | Statisch (aber korrekt) |

### Tests vorhanden ✅

- `TestDynamicOperationsDocumentation` in `test_plan_mode.py`
- Prüft ≥80% Coverage der Registry

---

## 4. AKTIONSPUNKTE

### Kritisch 🔴

1. **`setup_api_facet_sync` entfernen oder implementieren**
   - Im Write-Prompt dokumentiert aber nicht implementiert
   - Führt zu Fehlern wenn AI diese Operation vorschlägt

2. **`trigger_api_sync` entfernen oder implementieren**
   - Im Write-Prompt dokumentiert aber nicht implementiert

### Hoch 🟠

3. **Write-Prompt dynamisch machen** (wie Plan-Mode)
   - 14 Operationen sind implementiert aber nicht dokumentiert
   - Nutzer können diese Funktionen nicht per Smart Query nutzen

4. **Relation Types im Read-Prompt dynamisch laden**
   - Aktuell hardcoded: `works_for`, `attends`, `located_in`, `member_of`
   - Sollte aus DB geladen werden

### Mittel 🟡

5. **Konsistenz zwischen Modi herstellen**
   - Plan-Mode ist dynamisch ✅
   - Write-Mode ist statisch ❌
   - Read-Mode ist teilweise statisch ❌

---

## 5. EMPFOHLENE LÖSUNG

### Write-Prompt dynamisch machen

```python
def get_write_operations_documentation() -> str:
    """Generate documentation from OPERATIONS_REGISTRY for Write prompt."""
    from services.smart_query.operations import OPERATIONS_REGISTRY
    # Ähnlich wie get_operations_documentation() im Plan-Mode
    ...
```

### Read-Prompt Relation Types dynamisch laden

```python
def build_dynamic_query_prompt(..., relation_types: list[dict] = None):
    # relation_types aus DB laden statt hardcoded
```

---

## 6. ZUSAMMENFASSUNG

| Modus | Vollständigkeit | Dynamisch | Tests |
|-------|-----------------|-----------|-------|
| Read | 95% | Teilweise | ✅ |
| Write | 60% | ❌ | ✅ |
| Plan | 100% | ✅ | ✅ |

**Gesamtbewertung:** Der Plan-Mode ist nach dem Refactoring vollständig und dynamisch. Read- und Write-Mode benötigen ähnliche Anpassungen für vollständige Synchronisation.
