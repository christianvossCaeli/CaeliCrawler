# AI Tasks Module

This directory contains the refactored AI tasks module, split from the monolithic `ai_tasks.py` (2642 LOC) into focused, maintainable sub-modules.

## Module Structure

### `__init__.py` (60 LOC)
- Main package entry point
- Registers all tasks with the Celery app
- Exports all task functions for backward compatibility
- No breaking changes to existing code

### `common.py` (268 LOC)
Shared utilities and helper functions:
- Constants for PySis extraction (`PYSIS_*`)
- Constants for AI API calls (`AI_EXTRACTION_*`)
- `_get_default_prompt()` - Generate default AI prompts
- `_calculate_confidence()` - Calculate confidence scores from AI responses
- `_resolve_entity()` - Resolve entity names to UUIDs
- `_texts_similar()` - Jaccard similarity for text comparison

### `document_analyzer.py` (514 LOC)
Document analysis tasks:
- `analyze_document` - Analyze documents using Azure OpenAI
- `batch_analyze` - Batch analyze multiple documents
- `reanalyze_low_confidence` - Reanalyze low confidence results
- `_process_entity_references()` - Extract entity references from AI content
- `_call_azure_openai()` - Call Azure OpenAI API

### `pysis_processor.py` (1366 LOC)
PySis field processing tasks:
- `extract_pysis_fields` - Extract PySis field values using AI
- `convert_extractions_to_facets` - Convert ExtractedData to FacetValues
- `analyze_pysis_fields_for_facets` - Analyze PySis fields for facets
- `enrich_facet_values_from_pysis` - Enrich FacetValues from PySis data
- Multiple helper functions for PySis processing

### `entity_operations.py` (650 LOC)
Entity-related AI operations:
- `analyze_entity_data_for_facets` - Analyze entity data for facet enrichment
- `analyze_attachment_task` - Analyze entity attachments (images, PDFs)
- Helper functions for entity data analysis

## Migration Notes

### Backward Compatibility
All existing imports continue to work:
```python
from workers.ai_tasks import analyze_document
# Still works exactly as before
```

### Celery Task Names
All task names remain unchanged:
- `workers.ai_tasks.analyze_document`
- `workers.ai_tasks.extract_pysis_fields`
- `workers.ai_tasks.analyze_entity_data_for_facets`
- etc.

### Updated Files
- `backend/workers/celery_app.py` - Updated to include additional critical tasks in error handling
- `backend/workers/ai_tasks.py` - Moved to `ai_tasks.py.backup`

## Benefits

1. **Improved Maintainability**: Each module has a single, focused responsibility
2. **Better Code Organization**: Related functions are grouped together
3. **Easier Testing**: Smaller modules are easier to test in isolation
4. **Reduced Complexity**: Each file is now 500-1400 LOC instead of 2642 LOC
5. **No Breaking Changes**: All existing code continues to work

## File Sizes

| File | Lines of Code | Purpose |
|------|---------------|---------|
| `__init__.py` | 60 | Package initialization and task registration |
| `common.py` | 268 | Shared utilities and constants |
| `document_analyzer.py` | 514 | Document analysis tasks |
| `pysis_processor.py` | 1366 | PySis field processing |
| `entity_operations.py` | 650 | Entity operations |
| **Total** | **2858** | *(includes docstrings and registration code)* |

Original file: **2642 LOC**
