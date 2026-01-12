# Entities & Attachments API Audit - 2026-01-05

## Audit Summary
Umfassendes Audit der Entities und Attachments API durchgeführt.
Vergleich zwischen Implementation (_core.py, facets/*, relations.py) und Dokumentation (docs/api/ENTITIES.md, ATTACHMENTS.md).

---

## TEIL 1: ENTITIES API

### 1.1 GET /v1/entities - core_attr_filters Range-Filter

**CODE (backend/app/api/v1/entities/_core.py, Zeilen 116-141):**
- Range-Filter-Implementierung: ✓ VOLLSTÄNDIG
  - Min/Max-Support mit `{"min": X, "max": Y}` Syntax
  - Numeric Cast für DB-Vergleich
  - Kombiniert mit exakten Matches möglich
  - Fehlerbehandlung für invalid JSON

**DOKUMENTATION (docs/api/ENTITIES.md, Zeilen 119-150):**
- ✓ Syntax dokumentiert (Zeilen 126-138)
- ✓ Parameter-Referenz (Zeilen 140-144)
- ✓ Dynamische Schema-Introspection erwähnt (Zeilen 145-150)

**LÜCKE GEFUNDEN:**
- ❌ DOCS FEHLT: Erklärung, dass Range-Filter NUR für numerische Felder funktionieren
- ❌ DOCS FEHLT: Was passiert bei nicht-numerischen Attributen? (Error? Ignoriert?)
- ❌ DOCS FEHLT: Rückgabe bei invalid Range-Werten (z.B. min > max)
- ❌ CODE: Keine Validierung ob min > max (würde leere Resultate geben statt Error)

---

### 1.2 FacetValue Response - target_entity_type_icon und target_entity_type_color

**CODE IMPLEMENTIERUNG:**

**Datei: backend/app/schemas/facet_value.py (Zeilen 101-106)**
```python
target_entity_type_icon: str | None = Field(None, description="Referenced entity type icon")
target_entity_type_color: str | None = Field(None, description="Referenced entity type color")
```

**Datei: backend/app/api/v1/facets/facet_values.py (Zeilen 136-143)**
```python
if fv.target_entity:
    item.target_entity_name = fv.target_entity.name
    item.target_entity_slug = fv.target_entity.slug
    if fv.target_entity.entity_type:
        item.target_entity_type_slug = fv.target_entity.entity_type.slug
        item.target_entity_type_icon = fv.target_entity.entity_type.icon      # ✓ SET
        item.target_entity_type_color = fv.target_entity.entity_type.color    # ✓ SET
```

**DOKUMENTATION (docs/api/ENTITIES.md, Zeilen 417-423):**
```json
{
  "target_entity_type_icon": "mdi-account",
  "target_entity_type_color": "secondary"
}
```
- ✓ Felder dokumentiert
- ✓ Beispiele gegeben
- ✓ Beschreibung für Use-Case (Relation-Facets)

**STATUS: ✓ VOLLSTÄNDIG & SYNCHRONISIERT**
- Code implementiert
- Dokumentation aktuell
- Beispiele aktuell

---

### 1.3 GET /v1/entities/filter-options/attributes Endpoint

**DOKUMENTATION LÜCKE:**
- ❌ In docs/api/ENTITIES.md Zeilen 251-256 erwähnt, aber KEINE PARAMETER/RESPONSE dokumentiert
- ❌ Query-Parameter nicht aufgelistet (entity_type_slug, attribute_key)
- ❌ Response-Schema nicht dokumentiert
- CODE (Zeilen 551-706): Endpoint ist vollständig, aber nicht dokumentiert!

**FEHLENDE DOKUMENTATION:**
```
GET /v1/entities/filter-options/attributes

Query-Parameter:
- entity_type_slug (string, required): Entity type für Attribute
- attribute_key (string, optional): Spezifisches Attribut für Wert-Liste

Response:
{
  "entity_type_slug": "string",
  "entity_type_name": "string",
  "attributes": [
    {
      "key": "string",
      "title": "string",
      "type": "string|number|integer",
      "format": "string",
      "is_numeric": boolean,
      "min_value": number,
      "max_value": number
    }
  ],
  "attribute_values": {
    "attribute_key": ["value1", "value2"]
  }
}
```

---

### 1.4 Sorting Parameter in GET /v1/entities

**CODE (Zeilen 69-71, 173-216):**
- Sort-Felder: name, hierarchy_path, external_id, created_at, updated_at, facet_count, relation_count
- Sortierrichtung: asc, desc

**DOKUMENTATION:**
- ❌ LÜCKE: `sort_by` Parameter in ENTITIES.md nicht dokumentiert!
- ❌ LÜCKE: `sort_order` Parameter nicht dokumentiert!
- ❌ LÜCKE: facet_count und relation_count als sort-Felder nicht erwähnt!

---

### 1.5 GET /v1/entities/geojson Endpoint

**CODE (Zeilen 709-846):**
- GeoJSON FeatureCollection mit Point/Polygon Geometries
- Icons und Colors aus EntityType
- Filter nach entity_type_slug, country, admin_level_1/2

**DOKUMENTATION (ENTITIES.md):**
- ❌ LÜCKE: Endpoint nicht dokumentiert!
- ❌ LÜCKE: Parameter nicht aufgelistet
- ❌ LÜCKE: GeoJSON Response-Schema nicht dokumentiert
- ❌ LÜCKE: Feature Properties nicht dokumentiert

---

### 1.6 Relations Endpoints

**DOKUMENTATION (Zeilen 557-661):**
- Relations dokumentiert: ✓ GET /v1/relations, POST, PUT, DELETE, GET graph
- ✓ Filter-Parameter dokumentiert
- ✓ Response-Schema dokumentiert

**IMPLEMENTIERUNG (backend/app/api/v1/relations.py):**
- ✓ Alle Endpoints implementiert
- ✓ Parameter stimmen überein

**STATUS: ✓ SYNCHRONISIERT**

---

## TEIL 2: ATTACHMENTS API

### 2.1 GET /v1/attachments/search Endpoint

**CODE (backend/app/api/v1/attachments.py, Zeilen 40-153):**
- Search-Implementierung: ✓ VOLLSTÄNDIG
  - Query-Parameter: q, entity_id, content_type, analysis_status, page, per_page
  - PostgreSQL Full-Text Search mit German support
  - Ranking und Highlighting
  - Lazy Loading der Entity-Beziehung

**DOKUMENTATION (docs/api/ATTACHMENTS.md, Zeilen 36-104):**
- ✓ Parameter dokumentiert (Zeilen 41-49)
- ✓ Durchsuchte Felder dokumentiert (Zeilen 51-55)
- ✓ Technische Details dokumentiert (Zeilen 57-62)
- ✓ Response-Schema dokumentiert (Zeilen 63-91)
- ✓ Response-Felder erklärt (Zeilen 93-99)
- ✓ Beispiel-Anfrage (Zeilen 101-104)

**STATUS: ✓ VOLLSTÄNDIG & SYNCHRONISIERT**

---

### 2.2 POST /v1/entities/{entity_id}/attachments Upload

**DOKUMENTATION (Zeilen 108-145):**
- ✓ Endpoint dokumentiert
- ✓ Content-Type dokumentiert
- ✓ Parameter aufgelistet
- ✓ Response-Schema

**CODE (Zeilen 156-266):**
- ✓ auto_analyze Parameter implementiert
- ✓ File Validation
- ✓ Streaming Upload Handler

**LÜCKE GEFUNDEN:**
- ❌ DOCS: Response-Schema zeigt NICHT alle Felder!
  - Docs zeigt: id, entity_id, filename, content_type, file_size, description, analysis_status, is_image, is_pdf, uploaded_by_id, created_at, updated_at
  - CODE gibt zurück (Zeilen 242-251):
    ```python
    "attachment": {
        "id": str(attachment.id),
        "filename": attachment.filename,
        "content_type": attachment.content_type,
        "file_size": attachment.file_size,
        "analysis_status": attachment.analysis_status.value,
        "created_at": attachment.created_at.isoformat(),
    }
    ```
  - ❌ CODE Response ist MINIMAL, DOCS zeigt ausführliches Schema (WIDERSPRUCH!)
  - ❌ CODE hat kein "success" Wrapper, ABER Docs zeigt keinen Wrapper
  - ❌ Rückgabe unterscheidet sich in Struktur

---

### 2.3 GET /v1/entities/{entity_id}/attachments List

**DOKUMENTATION (Zeilen 148-187):**
- ✓ Parameter dokumentiert
- ✓ Response-Schema inkl. analysis_result

**CODE (Zeilen 269-300):**
- Response-Struktur in Code:
  ```python
  {
    "items": [...],
    "total": len(attachments)
  }
  ```
- Keine Pagination! Nur items + total

**LÜCKE GEFUNDEN:**
- ❌ DOCS zeigt pagination (skip/limit), CODE implementiert keine Pagination!
- ❌ DOCS-Parameter "skip" und "limit" sind nicht im CODE vorhanden!
- ❌ CODE gibt alle Attachments zurück, nicht paginiert!

---

### 2.4 GET /v1/entities/{entity_id}/attachments/{attachment_id}

**DOKUMENTATION (Zeilen 191-194):**
- Kurze Erwähnung, Response-Schema in Zeile 194 "wie oben"

**CODE (Zeilen 303-333):**
- ✓ Implementiert mit allen Feldern

**STATUS: ✓ OK aber Docs könnte ausführlicher sein**

---

### 2.5 GET /v1/entities/{entity_id}/attachments/{attachment_id}/download

**DOKUMENTATION (Zeilen 198-206):**
- ✓ Dokumentiert
- ✓ Fehler-Codes aufgelistet

**CODE (Zeilen 336-362):**
- ✓ Implementiert mit StreamingResponse

**STATUS: ✓ SYNCHRONISIERT**

---

### 2.6 GET /v1/entities/{entity_id}/attachments/{attachment_id}/thumbnail

**DOKUMENTATION (Zeilen 209-216):**
- ✓ Dokumentiert
- ✓ Größe erwähnt (256x256)
- ✓ Fehler-Codes

**CODE (Zeilen 365-390):**
- ✓ Implementiert

**STATUS: ✓ SYNCHRONISIERT**

---

### 2.7 PATCH /v1/entities/{entity_id}/attachments/{attachment_id}

**DOKUMENTATION (Zeilen 220-230):**
- ✓ Dokumentiert
- ✓ Request-Body Schema
- ✓ Response erwähnt

**CODE (Zeilen 474-498):**
- ✓ Implementiert

**STATUS: ✓ SYNCHRONISIERT**

---

### 2.8 POST /v1/entities/{entity_id}/attachments/{attachment_id}/analyze

**DOKUMENTATION (Zeilen 248-305):**
- ✓ Detailliert dokumentiert
- ✓ Parameter
- ✓ Funktionsweise
- ✓ Status-Werte
- ✓ Analyse-Ergebnis Schema

**CODE (Zeilen 437-471):**
- ✓ Implementiert

**LÜCKE GEFUNDEN:**
- ❌ DOCS zeigt Response mit "message" und "task_id" (Zeilen 262-268)
- ❌ CODE gibt zurück (Zeilen 465-469):
  ```python
  {
    "success": True,
    "task_id": str(task.id),
    "message": f"Analyse von '{attachment.filename}' gestartet"
  }
  ```
- ✓ Struktur stimmt überein, aber DOCS zeigt NICHT "success" Field!
- ❌ DOCS zeigt NICHT "attachment_id" in Response, CODE hat das auch nicht

---

### 2.9 POST /v1/entities/{entity_id}/attachments/{attachment_id}/apply-facets

**DOKUMENTATION (Zeilen 309-352):**
- ✓ Detailliert dokumentiert
- ✓ Query-Parameter (facet_indices)
- ✓ Voraussetzungen
- ✓ Response-Schema
- ✓ Details zur Facet-Erstellung

**CODE (Zeilen 501-642):**
- ✓ Implementiert

**LÜCKE GEFUNDEN:**
- ❌ DOCS Response (Zeilen 330-340) zeigt:
  ```json
  {
    "success": true,
    "applied_count": 3,
    "facet_value_ids": ["uuid-1", "uuid-2", "uuid-3"],
    "message": "..."
  }
  ```
- ❌ CODE gibt zurück (Zeilen 637-642):
  ```python
  {
    "success": True,
    "created_count": len(created),  # ← ANDERE Feldname!
    "created": created,              # ← ANDERE Feldname!
    "errors": errors if errors else None
  }
  ```
- ❌ WIDERSPRUCH: "applied_count" vs "created_count"
- ❌ WIDERSPRUCH: "facet_value_ids" nicht im Code, dafür "created" mit Details
- ❌ WIDERSPRUCH: Response-Format ist völlig unterschiedlich!

---

### 2.10 DELETE /v1/entities/{entity_id}/attachments/{attachment_id}

**DOKUMENTATION (Zeilen 234-241):**
- ✓ Dokumentiert
- ✓ Response

**CODE (Zeilen 393-434):**
- ✓ Implementiert

**STATUS: ✓ SYNCHRONISIERT**

---

## ZUSAMMENFASSUNG DER LÜCKEN

### KRITISCH (Response-Format Mismatches):
1. **POST /v1/attachments/apply-facets**
   - Docs: `applied_count`, `facet_value_ids`
   - Code: `created_count`, `created` (mit Details statt IDs)
   - Impact: HIGH - API-Clients werden Parsing-Fehler haben

2. **POST /v1/entities/{entity_id}/attachments** (Upload)
   - Docs: Response mit vielen Feldern
   - Code: Minimale Response in "attachment" Wrapper
   - Impact: MEDIUM - Unterschied in erwarteten Feldern

### MAJOR (Fehlende Dokumentation):
3. **GET /v1/entities/filter-options/attributes**
   - Endpoint nicht dokumentiert (Parameter, Response-Schema)
   - Code ist vollständig implementiert

4. **GET /v1/entities/geojson**
   - Endpoint nicht dokumentiert
   - Code ist vollständig implementiert

5. **GET /v1/entities List Sorting**
   - `sort_by` und `sort_order` Parameter nicht dokumentiert
   - `facet_count`, `relation_count` als Sortierfelder nicht erwähnt

6. **GET /v1/entities/{entity_id}/attachments List**
   - Docs zeigt `skip`/`limit` Parameter
   - Code implementiert keine Pagination!
   - WIDERSPRUCH in Implementation

### MINOR (Unvollständige Dokumentation):
7. **core_attr_filters Range-Filter**
   - Syntax dokumentiert, aber Validierung nicht erwähnt
   - Keine Angabe was bei min > max passiert
   - Keine Erklärung dass nur numerische Felder unterstützen

---

## IMPLEMENTATION STATUS BY ENDPOINT

### Entities API
| Endpoint | Code | Docs | Match | Status |
|----------|------|------|-------|--------|
| GET /v1/entities | ✓ | ✓ | ⚠️ | PARTIAL - sort_by/sort_order nicht dokumentiert |
| GET /v1/entities/filter-options/attributes | ✓ | ❌ | ❌ | MISSING DOCS |
| GET /v1/entities/geojson | ✓ | ❌ | ❌ | MISSING DOCS |
| GET /v1/entities/{id} | ✓ | ✓ | ✓ | OK |
| GET /v1/entities/by-slug | ✓ | ✓ | ✓ | OK |
| GET /v1/entities/{id}/children | ✓ | ✓ | ✓ | OK |
| POST /v1/entities | ✓ | ✓ | ✓ | OK |
| PUT /v1/entities/{id} | ✓ | ✓ | ✓ | OK |
| DELETE /v1/entities/{id} | ✓ | ✓ | ✓ | OK |

### Attachments API
| Endpoint | Code | Docs | Match | Status |
|----------|------|------|-------|--------|
| GET /v1/attachments/search | ✓ | ✓ | ✓ | OK |
| POST /v1/entities/{id}/attachments | ✓ | ✓ | ⚠️ | RESPONSE MISMATCH |
| GET /v1/entities/{id}/attachments | ✓ | ✓ | ❌ | PAGINATION MISMATCH |
| GET /v1/entities/{id}/attachments/{aid} | ✓ | ✓ | ✓ | OK |
| GET .../download | ✓ | ✓ | ✓ | OK |
| GET .../thumbnail | ✓ | ✓ | ✓ | OK |
| PATCH /v1/entities/{id}/attachments/{aid} | ✓ | ✓ | ✓ | OK |
| DELETE /v1/entities/{id}/attachments/{aid} | ✓ | ✓ | ✓ | OK |
| POST .../analyze | ✓ | ✓ | ✓ | OK |
| POST .../apply-facets | ✓ | ✓ | ❌ | RESPONSE MISMATCH |

---

## RECOMMENDATIONS

1. **Sofort beheben (API-Breaking):**
   - GET /v1/entities/{id}/attachments: Pagination implementieren oder aus Docs entfernen
   - POST .../apply-facets: Response-Format anpassen (applied_count, facet_value_ids statt created_count, created)

2. **High Priority (Docs-Updates):**
   - GET /v1/entities/filter-options/attributes dokumentieren
   - GET /v1/entities/geojson dokumentieren
   - Sorting-Parameter in GET /v1/entities dokumentieren

3. **Medium Priority:**
   - POST /v1/entities/{id}/attachments Response-Format klären (minimal vs. ausführlich)
   - core_attr_filters Validierungsregeln dokumentieren
