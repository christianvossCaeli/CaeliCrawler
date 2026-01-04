# Facets API Refactoring Plan

## Status: Planned

## Current State
- `backend/app/api/v1/facets.py` - 1620 lines, 24 endpoints

## Proposed Structure

```
backend/app/api/v1/facets/
├── __init__.py          # Main router combining all sub-routers
├── types.py             # FacetType CRUD (8 endpoints, ~400 lines)
├── values.py            # FacetValue CRUD (7 endpoints, ~500 lines)
├── entity.py            # Entity-related queries (3 endpoints, ~200 lines)
└── history.py           # History data points (6 endpoints, ~500 lines)
```

## Endpoint Distribution

### types.py (FacetType operations)
- `list_facet_types`
- `get_facet_types_for_category`
- `create_facet_type`
- `get_facet_type`
- `get_facet_type_by_slug`
- `generate_facet_type_schema`
- `update_facet_type`
- `delete_facet_type`

### values.py (FacetValue operations)
- `list_facet_values`
- `create_facet_value`
- `get_facet_value`
- `update_facet_value`
- `verify_facet_value`
- `delete_facet_value`
- `search_facet_values`

### entity.py (Entity-related)
- `get_facets_referencing_entity`
- `get_entity_facets_summary`

### history.py (History data points)
- `get_entity_history`
- `get_entity_history_aggregated`
- `add_history_data_point`
- `add_history_data_points_bulk`
- `update_history_data_point`
- `delete_history_data_point`

## Migration Steps

1. Create `facets/` directory
2. Copy shared imports/schemas to each file
3. Move endpoints to respective files
4. Create sub-routers with appropriate prefixes
5. Combine in `__init__.py`
6. Update main router registration
7. Test all endpoints
8. Remove old `facets.py`

## Notes
- Keep backwards compatibility with existing URL paths
- Shared schemas stay in `app/schemas/facet_*.py`
- Consider creating shared helper module for common queries
