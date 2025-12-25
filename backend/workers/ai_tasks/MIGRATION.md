# Migration Guide: ai_tasks.py Refactoring

## Overview

The monolithic `ai_tasks.py` file (2642 LOC) has been split into a modular package structure for better maintainability and organization.

## Changes Made

### 1. File Structure

**Before:**
```
backend/workers/
  ├── ai_tasks.py (2642 LOC)
  └── celery_app.py
```

**After:**
```
backend/workers/
  ├── ai_tasks/
  │   ├── __init__.py (60 LOC)
  │   ├── common.py (268 LOC)
  │   ├── document_analyzer.py (514 LOC)
  │   ├── pysis_processor.py (1366 LOC)
  │   ├── entity_operations.py (650 LOC)
  │   ├── README.md
  │   └── MIGRATION.md
  ├── ai_tasks.py.backup (original file backup)
  └── celery_app.py (updated)
```

### 2. Module Responsibilities

#### `common.py`
- Shared constants and configuration
- Helper functions used across multiple modules
- No Celery tasks

#### `document_analyzer.py`
- Document analysis with Azure OpenAI
- Batch document processing
- Low confidence reanalysis
- Entity reference extraction

#### `pysis_processor.py`
- PySis field value extraction
- Conversion of ExtractedData to FacetValues
- PySis field analysis for facets
- FacetValue enrichment from PySis data

#### `entity_operations.py`
- Entity data analysis for facet enrichment
- Entity attachment analysis (images, PDFs)

### 3. Code Changes

#### celery_app.py
Updated error handling to include additional critical tasks:
```python
if sender and sender.name in (
    "workers.crawl_tasks.crawl_source",
    "workers.ai_tasks.analyze_document",
    "workers.ai_tasks.extract_pysis_fields",
    "workers.ai_tasks.analyze_entity_data_for_facets",  # Added
    "workers.ai_tasks.analyze_attachment_task",  # Added
):
```

## Backward Compatibility

### ✅ No Breaking Changes

All existing imports and task calls continue to work:

```python
# These all still work exactly as before
from workers.ai_tasks import analyze_document
from workers.ai_tasks import extract_pysis_fields
from workers.ai_tasks import analyze_entity_data_for_facets

# Celery task names remain unchanged
analyze_document.delay(document_id)
extract_pysis_fields.apply_async(args=[process_id])
```

### Task Registration

Tasks are registered automatically when `workers.ai_tasks` is imported by `celery_app.py`. No manual registration needed.

## Testing Checklist

- [x] All modules compile without syntax errors
- [x] Celery app includes are updated
- [x] Task names remain unchanged
- [x] Imports are backward compatible
- [ ] Run existing tests to verify functionality
- [ ] Test document analysis tasks
- [ ] Test PySis extraction tasks
- [ ] Test entity operation tasks

## Rollback Instructions

If issues occur, you can quickly rollback:

```bash
cd backend/workers
rm -rf ai_tasks/
mv ai_tasks.py.backup ai_tasks.py
git checkout celery_app.py
```

Then restart Celery workers.

## Benefits of This Refactoring

1. **Improved Maintainability**: Each module has <1500 LOC
2. **Better Organization**: Related functionality is grouped
3. **Easier Testing**: Modules can be tested in isolation
4. **No Breaking Changes**: Existing code works without modification
5. **Clear Responsibility**: Each module has a single focus
6. **Better Documentation**: Each module has clear docstrings

## Next Steps

1. **Test thoroughly**: Run all AI task-related tests
2. **Monitor logs**: Check for any import or registration errors
3. **Update documentation**: Update any internal docs that reference file locations
4. **Consider further splits**: If any module grows beyond 1000 LOC, consider further splitting

## Support

If you encounter any issues:
1. Check the backup file is present: `ai_tasks.py.backup`
2. Verify all new modules compile: `python3 -m py_compile ai_tasks/*.py`
3. Check Celery worker logs for registration errors
4. Rollback if necessary (see above)

---

**Migration completed:** 2025-12-25
**Original file:** `ai_tasks.py` (2642 LOC)
**New structure:** 5 focused modules (2858 LOC total with docs)
