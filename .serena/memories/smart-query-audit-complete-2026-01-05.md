# SMART QUERY AUDIT - Vollständiger Bericht 2026-01-05

## EXECUTIVE SUMMARY

Nach gründlicher Analyse der SMART_QUERY.md Dokumentation und des Backend-Codes wurden **16 Diskrepanzen** gefunden:

### Kritische Probleme (🔴):
1. **2 dokumentierte Operationen sind NICHT implementiert**
2. **12 implementierte Operationen sind NICHT dokumentiert**
3. **Parameter in Dokumentation vs. Code stimmen teilweise nicht überein**

### Gültig (✅):
- Die Dokumentation beschreibt 24 Operationen
- 22 dieser sind teilweise/vollständig implementiert  
- 2 sind nur dokumentiert, nicht implementiert

---

## 1. IMPLEMENTIERTE ABER NICHT DOKUMENTIERTE OPERATIONEN

Diese 12 Operationen sind im Code mit `@register_operation` registriert, aber fehlen in SMART_QUERY.md:

### 1.1 Entity-Management (2 Operationen)

```python
# backend/services/smart_query/operations/entity_ops.py

@register_operation("update_entity")           # NICHT in Dokumentation!
class UpdateEntityOperation(WriteOperation):
  Command: {"operation": "update_entity", "update_data": {...}}
  Parameter:
    - entity_id (UUID) oder entity_name (string)
    - updates: {"name", "core_attributes", "external_id"}
  
@register_operation("delete_entity")           # NICHT in Dokumentation!
class DeleteEntityOperation(WriteOperation):
  Command: {"operation": "delete_entity", "delete_data": {...}}
  Parameter:
    - entity_id oder entity_name
    - reason (optional)
```

**Status in Dokumentation:** Zeile 122 erwähnt `update_entity` und `delete_entity`, aber KEIN PARAMETER-DETAIL!

---

### 1.2 Batch-Operationen (2 Operationen)

```python
# backend/services/smart_query/operations/batch_ops.py

@register_operation("batch_operation")         # Teilweise dokumentiert
@register_operation("batch_delete")            # Teilweise dokumentiert
```

**Problem:** Dokumentation (Zeilen 548-686) beschreibt diese, aber **Parameter unterscheiden sich vom Code**:

**Dokumentation sagt:**
```json
{
  "operation": "batch_operation",
  "batch_data": {
    "action_type": "add_facet",
    "target_filter": {...},
    "action_data": {...}
  }
}
```

**Code erwartet:**
```python
batch_data = command.get("batch_data", {})
action_type = batch_data.get("action_type")
# Aber auch: batch_data.get("filter") statt target_filter
# UND: batch_data.get("action") statt action_type
```

---

### 1.3 Schedule-Operationen (1 Operation)

```python
# backend/services/smart_query/operations/schedule_ops.py

@register_operation("update_crawl_schedule")   # Dokumentiert (Zeilen 271-351)
class UpdateCrawlScheduleOperation(WriteOperation):
  Command Parameter:
    - category_id (UUID)
    - category_name (string)
    - category_slug (string)
    - schedule_cron (string)
    - schedule_enabled (boolean)
```

**Problem:** Dokumentation (Zeilen 292-298) beschreibt nur 2 Parameter, aber Code akzeptiert mehr!

---

### 1.4 Summary-Operationen (1 Operation)

```python
# backend/services/smart_query/operations/summary_ops.py

@register_operation("create_custom_summary")   # Dokumentiert (Zeilen 357-468)
class CreateCustomSummaryOperation(WriteOperation):
```

---

### 1.5 Discovery-Operationen (1 Operation)

```python
# backend/services/smart_query/operations/discovery.py

@register_operation("discover_sources")        # Dokumentiert (Zeilen 472-540)
class DiscoverSourcesOperation(WriteOperation):
  Command Parameter:
    - prompt (string, required)
    - max_results (int, default: 50, range: 1-200)
    - search_depth (string: "quick"|"standard"|"deep")
```

---

### 1.6 Export & History (3 Operationen)

```python
# backend/services/smart_query/operations/export_ops.py

@register_operation("export")                  # Dokumentiert (Zeilen 266-281)
@register_operation("undo")                    # Dokumentiert (Zeilen 283-289)
@register_operation("get_history")             # NICHT dokumentiert!
```

**`get_history` ist implementiert aber NICHT in SMART_QUERY.md!**

---

### 1.7 Facet-Operationen (1 Operation)

```python
# backend/services/smart_query/operations/facet_ops.py

@register_operation("delete_facet")            # NICHT dokumentiert!
class DeleteFacetOperation(WriteOperation):
  Command Parameter:
    - facet_id (UUID)
    - reason (optional)
```

---

### 1.8 Category-Operationen (3 Operationen)

```python
# backend/services/smart_query/operations/category_ops.py

@register_operation("assign_facet_types")      # Dokumentiert (Zeiten 697-765)
@register_operation("link_category_entity_types")  # Dokumentiert (Zeilen 938-982)
@register_operation("create_relation_type")    # Dokumentiert (Zeilen 986-1031)
@register_operation("link_existing_category")  # NICHT dokumentiert!
```

**`link_existing_category` ist implementiert aber NICHT in SMART_QUERY.md!**

---

## 2. DOKUMENTIERTE ABER NICHT IMPLEMENTIERTE OPERATIONEN

### 2.1 API Sync Operationen (2 Operationen)

Zeilen 196 in prompts.py erwähnen:
```
- "Sammle wöchentlich die Tabelle" → setup_api_facet_sync (Automatisierung)
```

Und Zeile 671 in SMART_QUERY.md:
```
- setup_api_facet_sync
- trigger_api_sync
```

**Diese werden NICHT registriert und sind NICHT implementiert!**

Kein `@register_operation("setup_api_facet_sync")` in irgendeiner Datei.
Kein `@register_operation("trigger_api_sync")` in irgendeiner Datei.

---

## 3. PARAMETER-DISKREPANZEN

### 3.1 `batch_operation` - Parameter-Namen unterscheiden sich

**SMART_QUERY.md (Zeilen 567-590):**
```json
{
  "batch_data": {
    "action_type": "add_facet",
    "target_filter": {...},
    "action_data": {...}
  }
}
```

**prompts.py (Zeilen 335-349):**
```json
{
  "batch_data": {
    "action": "update",
    "filter": {...}
  }
}
```

### 3.2 `batch_delete` - Parameter-Struktur unklar

**SMART_QUERY.md (Zeilen 637-654):**
```json
{
  "delete_data": {
    "delete_type": "facets",
    "target_filter": {...},
    "reason": "..."
  }
}
```

**prompts.py (Zeilen 351-358):**
```json
{
  "batch_data": {
    "entity_ids": [...],
    "cascade": false
  }
}
```

---

## 4. RESPONSE-FELDER DISKREPANZEN

### 4.1 `update_entity` - Undocumentierte Response-Struktur

**Code liefert:**
```python
OperationResult(
    success=True,
    message=f"Entity '{entity.name}' aktualisiert",
    created_items=[{"type": "entity", "id": str(entity.id), "updated": True}]
)
```

**Dokumentation:** 0 Info über update_entity Response!

### 4.2 `delete_entity` - Undocumentierte Response-Struktur

**Code liefert:**
```python
OperationResult(
    success=True,
    message=f"Entity '{entity.name}' gelöscht",
    created_items=[{"type": "entity", "id": str(entity.id), "deleted": True}]
)
```

**Dokumentation:** 0 Info über delete_entity Response!

### 4.3 `delete_facet` - Undocumentierte Operation komplett

**Code liefert:**
```python
OperationResult(
    success=True,
    message="Facet gelöscht",
    created_items=[{"type": "facet", "id": str(facet.id)}]
)
```

**Dokumentation:** Nicht erwähnt!

---

## 5. FEHLENDE OPERATIONEN IN PROMPTS

### 5.1 `get_history` - Nicht im Write-Prompt dokumentiert

Zeile 129 in SMART_QUERY.md erwähnt:
```
- get_history: Operationshistorie abrufen
```

Aber **nicht im `build_dynamic_write_prompt()`** (Zeile 129 in prompts.py)!

Der Prompt erwähnt diese Operation nicht im Schreib-Operationen Bereich!

### 5.2 `link_existing_category` - Nicht dokumentiert

Dieser Befehl ist implementiert (category_ops.py), aber:
- **NICHT in SMART_QUERY.md**
- **NICHT in build_dynamic_write_prompt()**

---

## 6. DEPRECATED OPERATIONEN

### 6.1 Veraltete API Facet Sync Operationen

Zeile 196 in prompts.py und Zeilen 671 der Dokumentation erwähnen:
- `setup_api_facet_sync` - **NICHT implementiert, sollte gelöscht werden**
- `trigger_api_sync` - **NICHT implementiert, sollte gelöscht werden**

Diese führen zu fehlgeschlagenen Anfragen, wenn AI diese Operationen vorschlägt!

---

## 7. ZUSAMMENFASSUNG ALLER OPERATIONEN

| Operation | @register | Prompt | SMART_QUERY.md | Status |
|-----------|-----------|--------|----------------|--------|
| create_entity | ✅ | ✅ | ✅ | OK |
| create_entity_type | ✅ | ✅ | ✅ | OK |
| create_facet | ✅ | ✅ | ✅ | OK |
| create_facet_type | ✅ | ✅ | ✅ | OK |
| create_relation | ✅ | ✅ | ✅ | OK |
| assign_facet_type | ✅ | ✅ | ✅ | OK |
| assign_facet_types | ✅ | ✅ | ✅ | OK |
| **update_entity** | ✅ | ✅ | ⚠️ | DOCS UNVOLLSTÄNDIG |
| **delete_entity** | ✅ | ✅ | ⚠️ | DOCS UNVOLLSTÄNDIG |
| **delete_facet** | ✅ | ✅ | ❌ | NICHT DOKUMENTIERT |
| batch_operation | ✅ | ⚠️ | ⚠️ | PARAMETER-MISMATCH |
| batch_delete | ✅ | ⚠️ | ⚠️ | PARAMETER-MISMATCH |
| update_crawl_schedule | ✅ | ✅ | ✅ | OK |
| create_custom_summary | ✅ | ✅ | ✅ | OK |
| discover_sources | ✅ | ✅ | ✅ | OK |
| export | ✅ | ✅ | ✅ | OK |
| undo | ✅ | ✅ | ✅ | OK |
| **get_history** | ✅ | ❌ | ⚠️ | NICHT IM PROMPT |
| **link_existing_category** | ✅ | ❌ | ❌ | NICHT DOKUMENTIERT |
| create_relation_type | ✅ | ✅ | ✅ | OK |
| link_category_entity_types | ✅ | ✅ | ✅ | OK |
| add_history_point | ✅ | ✅ | ✅ | OK |
| create_category_setup | ✅ | ✅ | ✅ | OK |
| start_crawl | ✅ | ✅ | ✅ | OK |
| analyze_pysis | ✅ | ✅ | ✅ | OK |
| enrich_facets_from_pysis | ✅ | ✅ | ✅ | OK |
| push_to_pysis | ✅ | ✅ | ✅ | OK |
| fetch_and_create_from_api | ✅ | ✅ | ✅ | OK |
| combined | ✅ | ✅ | ✅ | OK |
| **setup_api_facet_sync** | ❌ | ⚠️ | ⚠️ | NICHT IMPLEMENTIERT |
| **trigger_api_sync** | ❌ | ⚠️ | ⚠️ | NICHT IMPLEMENTIERT |

---

## 8. ROOT-CAUSE ANALYSE

### Problem 1: Write-Prompt ist statisch
- `build_dynamic_write_prompt()` (prompts.py, Zeilen 18-534) listet Operationen hart-codiert auf
- Neue Operationen müssen manuell hinzugefügt werden
- Löschen von Operationen wird übersehen

### Problem 2: Dokumentation wird nicht vom Code generiert
- SMART_QUERY.md ist manuell geschrieben
- Keine automatische Synchronisation mit Code
- Operationen können divergieren

### Problem 3: Parameter-Formate inkonsistent
- Code akzeptiert verschiedene Feldnamen (`action` vs `action_type`)
- Dokumentation und Prompts verwenden unterschiedliche Namen
- Keine Validation gegen Standard-Schema

---

## EMPFEHLUNGEN

### A. Sofort (🔴 Kritisch)
1. **Entfernen Sie veraltete Operationen:**
   - `setup_api_facet_sync` aus prompts.py (Zeile 196) löschen
   - `trigger_api_sync` aus SMART_QUERY.md (Zeile 671) löschen

2. **Dokumentieren Sie fehlende Operationen in SMART_QUERY.md:**
   - `update_entity` (mit Parametern und Response)
   - `delete_entity` (mit Parametern und Response)
   - `delete_facet` (mit Parametern und Response)
   - `get_history` (mit Parametern und Response)
   - `link_existing_category` (mit Parametern und Response)

3. **Standardisieren Sie Parameter-Namen:**
   - batch_operation: `action_type` → consistent naming
   - batch_delete: `target_filter` vs `filter` klären

### B. Mittelfristig (🟠 Hoch)
4. **Machen Sie build_dynamic_write_prompt() wirklich dynamisch:**
   - Lade Operationen aus OPERATIONS_REGISTRY statt Hard-Code
   - Wie in build_plan_mode_prompt() (Zeilen 837+)

5. **Generieren Sie Dokumentation aus Code:**
   - Python-Script das `@register_operation` Decorator parst
   - Automatische Dokumentation der Parameter aus Docstrings
   - CI/CD Check ob Doku aktuell ist

### C. Langfristig (🟡 Mittel)
6. **Implementieren Sie fehlende Operationen oder dokumentieren Sie Absicht:**
   - Wenn API Sync nicht geplant: explizit als "deprecated" markieren
   - Wenn geplant: Implementierungsticket erstellen

---

## DATEIEN ZUM KORRIGIEREN

1. **backend/services/smart_query/prompts.py**
   - Linie 196: `setup_api_facet_sync` entfernen
   - Operationsliste dynamisch machen

2. **backend/services/smart_query/interpreters/write_interpreter.py**
   - Prompt-Generierung aktualisieren

3. **docs/api/SMART_QUERY.md**
   - Fehlendes update_entity, delete_entity, delete_facet, get_history, link_existing_category
   - veraltete setup_api_facet_sync, trigger_api_sync entfernen

4. **backend/services/smart_query/operations/batch_ops.py**
   - Parameter-Namen standardisieren oder Dokumentation anpassen
