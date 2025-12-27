# Facetten-System Audit (27.12.2025)

## Executive Summary

**Gesamtbewertung: ⭐⭐⭐⭐⭐ (4.8/5)** - Exzellent strukturiert, nur kleine Fixes

---

## Analysierte Dateien

| Bereich | Datei | LOC | Bewertung |
|---------|-------|-----|-----------|
| Backend Model | `facet_type.py` | 235 | ⭐⭐⭐⭐⭐ |
| Backend Model | `facet_value.py` | 286 | ⭐⭐⭐⭐⭐ |
| Backend API | `facets.py` | ~1510 | ⭐⭐⭐⭐½ |
| Frontend API | `facets.ts` | 95 | ⭐⭐⭐⭐⭐ |

---

## Positive Findings

### Backend Models

✅ **FacetType** - Sehr umfangreiches Model:
- `name_embedding` für Semantic Search (pgvector)
- `value_schema` für JSON Schema Validierung
- `applicable_entity_type_slugs` für Entity-Type-Filterung
- `allows_entity_reference` + `target_entity_type_slugs` für Entity-Referenzen
- Time-based Support (`is_time_based`, `time_field_path`, `default_time_filter`)
- AI-Extraction Config (`ai_extraction_enabled`, `ai_extraction_prompt`)

✅ **FacetValue** - Vollständiges Source-Tracking:
- `FacetValueSourceType` Enum (DOCUMENT, MANUAL, PYSIS, SMART_QUERY, AI_ASSISTANT, IMPORT, ATTACHMENT)
- `target_entity_id` für Entity-Referenzen
- `human_verified` + `human_corrections` für Verifikation
- `text_embedding` für Semantic Similarity
- `search_vector` für Full-Text Search (tsvector)
- Composite Indexes für Performance

### Backend API

✅ **Full-Text Search** mit PostgreSQL tsvector/tsquery:
```python
func.ts_rank(FacetValue.search_vector, search_query).label("rank")
func.ts_headline("german", FacetValue.text_representation, ...)
```

✅ **Entity-Reference System**:
- `GET /facets/entity/{id}/referenced-by` - Findet alle Facets, die auf diese Entity referenzieren
- Ermöglicht bidirektionale Navigation (z.B. Person → welche Gemeinden referenzieren diese Person)

✅ **Time-Series History**:
- `GET /history/{facet_type_id}` - Raw data points
- `GET /history/{facet_type_id}/aggregated` - Aggregiert (day/week/month/quarter/year)
- Bulk import Support

✅ **Keine N+1 Queries** - selectinload überall

✅ **Caching** für FacetTypes

✅ **Audit-Logging** für alle schreibenden Operationen

### Frontend API

✅ **Konsistente Struktur** - Klare Funktionsnamen
✅ **TypeScript Types** - Alle Parameter typisiert
✅ **Vollständige Coverage** - Alle Backend-Endpoints abgedeckt

---

## Durchgeführte Fixes

### SQL-Injection Prevention (2 Stellen)

**Zeile 84-90 (list_facet_types):**
```python
# Vorher
FacetType.name.ilike(f"%{search}%")

# Nachher
search_pattern = f"%{search.replace('%', '\\%').replace('_', '\\_')}%"
FacetType.name.ilike(search_pattern, escape='\\')
```

**Zeile 541-552 (list_facet_values):**
```python
# Vorher (ILIKE Fallback)
FacetValue.text_representation.ilike(f"%{search}%")

# Nachher
search_pattern = f"%{search.replace('%', '\\%').replace('_', '\\_')}%"
FacetValue.text_representation.ilike(search_pattern, escape='\\')
```

---

## Architektur-Übersicht

```
FacetType (facet_types)
    ├── slug, name, name_plural
    ├── value_type (text, structured, list, reference, number, boolean, history)
    ├── value_schema (JSON Schema)
    ├── applicable_entity_type_slugs[]
    ├── allows_entity_reference, target_entity_type_slugs[], auto_create_entity
    ├── is_time_based, time_field_path, default_time_filter
    ├── ai_extraction_enabled, ai_extraction_prompt
    └── aggregation_method, deduplication_fields[]

FacetValue (facet_values)
    ├── entity_id → Entity
    ├── facet_type_id → FacetType
    ├── target_entity_id → Entity (optional reference)
    ├── value (JSONB), text_representation, text_embedding
    ├── event_date, valid_from, valid_until
    ├── source_type (DOCUMENT|MANUAL|PYSIS|...)
    ├── source_document_id, source_attachment_id, source_url
    ├── confidence_score, ai_model_used
    └── human_verified, verified_by, human_corrections

FacetValueHistory (facet_value_history)
    ├── entity_id, facet_type_id
    ├── recorded_at, value, track_key
    └── annotations, source_type
```

---

## Geänderte Dateien

```
backend/app/api/v1/facets.py (2 SQL-Injection Fixes)
```
