# FacetType Configuration Audit - 2026-01-05

## Overview
Comprehensive audit of all FacetType display configurations and AI extraction prompts to ensure facet values display correctly and are populated properly.

## Issues Found & Fixed

### 1. Display Configuration Issues
Many FacetTypes were missing `display` configuration in their `value_schema`, causing the frontend to show unhelpful or empty content.

**Fixed FacetTypes:**
| Slug | Primary Field | Chip Fields | Quote Field |
|------|--------------|-------------|-------------|
| contact | name | role, organisation, sentiment | statement |
| pain_point | description | type, severity | quote |
| positive_signal | description | type | quote |
| planning_status | status | authority, effective_date | next_milestone |
| wind_area_designation | area_type | area_km2, area_count, shape_format | - |
| event_attendance | event_name | role, event_date, event_location | - |
| planungsstand | status | planungsregion, datum | naechste_schritte |
| offenlage | einwendungsfrist | start_datum, ende_datum | ansprechpartner |
| bevoelkerungsentwicklung | value | - | - |
| events | name | date, location | - |
| infrastrukturprojekte | name | status, budget | - |
| summary | text | - | - |
| news | content | - | - |

### 2. Duplicate FacetType Found
- `planning_status` (English, 0 values) - **DEACTIVATED**
- `planungsstand` (German, 26 values) - **KEPT**
- Fixed typo: "Planungßtand" → "Planungsstand"

### 3. AI Prompt vs Schema Mismatches
AI prompts use certain field names that didn't match FacetType schemas:

| AI Prompt Field | FacetType Schema Field | Status |
|-----------------|----------------------|--------|
| text | description | Added 'text' alias + normalization |
| organisation | (missing) | Added to contact schema |
| type enum values | Limited | Extended enum values |

**Extended enum values for `pain_point.type`:**
- Added: "Widerstand", "Planung", "Rechtlich"

**Extended enum values for `positive_signal.type`:**
- Added: "Fortschritt", "Genehmigung", "Unterstuetzung"

### 4. Field Normalization
Added `_normalize_facet_value_fields()` function in `entity_facet_service.py` to:
- Map 'text' → 'description' during facet value creation
- Ensure AI extraction output aligns with schema expectations

## Technical Changes

### Files Modified:
1. **Database: facet_types table**
   - Updated `value_schema` for 17 FacetTypes
   - Added display configurations with primary_field, chip_fields, quote_field
   - Extended property schemas

2. **backend/services/entity_facet_service.py**
   - Added `_normalize_facet_value_fields()` function
   - Called normalization before saving facet values

### Display Configuration Structure
```json
{
  "display": {
    "layout": "card" | "inline" | "list",
    "primary_field": "field_name",
    "chip_fields": ["field1", "field2"],
    "quote_field": "field_name",
    "severity_field": "field_name",
    "severity_colors": {"hoch": "error", "mittel": "warning", "niedrig": "info"}
  }
}
```

## AI Extraction Prompt Best Practices
When creating/updating AI extraction prompts for categories:

1. **Use standard field names** that match FacetType schemas:
   - Use `description` not `text` for main content
   - Use `name` for entity names
   - Use `type` for categorization

2. **Include all required fields** defined in FacetType.value_schema.properties

3. **Use correct enum values** that match the schema

4. **Example prompt structure:**
```
{
  "facet_type_slug": {
    "field1": "value",
    "field2": "value"
  }
}
```

## Verification
- Frontend `GenericFacetValueRenderer` component uses `useFacetTypeRenderer` composable
- Fallback logic tries: primary_field → description → text → name → title → content
- Chip fields render if values are non-null and non-empty
- Quote field renders in styled block if present

## AI-Generated FacetType Display Configuration

The `_infer_value_schema_from_data()` function in `entity_facet_service.py` was enhanced to automatically generate proper display configurations when new FacetTypes are created by AI:

### Field Detection Patterns

**Primary Field Candidates:**
- description, text, name, title, aenderungen, beschreibung, inhalt, content

**Chip Field Candidates:**
- typ, type, ausweisung_typ, status, severity, role, rolle
- organisation, format, shape_format, planungsregion, behoerde
- event_date, event_location, datum, start_datum, ende_datum
- einwendungsfrist, effective_date, authority
- Fields ending with _ha, _km2, or containing "flaeche", "anzahl", "count", "area"

**Quote Field Candidates:**
- quote, statement, aussage, naechste_schritte, next_milestone, ansprechpartner

**Severity Field Candidates:**
- severity, schweregrad, priority, prioritaet

### Key Behaviors
- Primary field is automatically excluded from chip_fields to avoid duplication
- Maximum 4 chip fields are included
- Severity field is automatically added to display config when detected
- Quote field is automatically added when detected

## Follow-up Recommendations
1. Consider consolidating similar FacetTypes (e.g., combine English/German variants)
2. Review other category AI prompts for consistency with FacetType schemas
3. Add validation during facet value creation to ensure required fields
4. Consider adding AI prompt generation based on FacetType schemas
