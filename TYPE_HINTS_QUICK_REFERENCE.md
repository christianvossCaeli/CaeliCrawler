# Type Hints Quick Reference

Quick copy-paste patterns for adding type hints to FastAPI endpoints.

## Step-by-Step Process

### 1. Add Import
```python
# Add to top of file if not already present
from typing import Annotated
```

### 2. Update Each Endpoint

#### Pattern for GET List Endpoints
```python
@router.get("", response_model=ItemListResponse)
async def list_items(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
    search: Annotated[Optional[str], Query(description="Search query")] = None,
    session: AsyncSession = Depends(get_session),
) -> ItemListResponse:
    ...
```

#### Pattern for GET Single Item
```python
@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ItemResponse:
    ...
```

#### Pattern for POST (Create)
```python
@router.post("", response_model=ItemResponse, status_code=201)
async def create_item(
    data: ItemCreate,
    request: Request,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
) -> ItemResponse:
    ...
```

#### Pattern for PUT (Update)
```python
@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: UUID,
    data: ItemUpdate,
    request: Request,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
) -> ItemResponse:
    ...
```

#### Pattern for DELETE
```python
@router.delete("/{item_id}", response_model=MessageResponse)
async def delete_item(
    item_id: UUID,
    request: Request,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    ...
```

## Common Parameter Patterns

### Pagination
```python
page: Annotated[int, Query(ge=1, description="Page number")] = 1
per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50
```

### Search/Filter
```python
search: Annotated[Optional[str], Query(description="Search query")] = None
is_active: Annotated[Optional[bool], Query(description="Filter by active status")] = None
```

### UUID Filters
```python
category_id: Annotated[Optional[UUID], Query(description="Filter by category")] = None
```

### Numeric Ranges
```python
min_confidence: Annotated[float, Query(ge=0, le=1, description="Minimum confidence score")] = 0.0
min_value: Annotated[int, Query(ge=0, description="Minimum value")] = 0
max_value: Annotated[int, Query(le=100, description="Maximum value")] = 100
```

### Date/Time
```python
start_date: Annotated[Optional[datetime], Query(description="Start date")] = None
end_date: Annotated[Optional[datetime], Query(description="End date")] = None
```

### Lists
```python
tags: Annotated[Optional[List[str]], Query(description="Filter by tags")] = None
ids: Annotated[Optional[List[UUID]], Query(description="Filter by IDs")] = None
```

### Enums
```python
status: Annotated[Optional[SourceStatus], Query(description="Filter by status")] = None
role: Annotated[Optional[UserRole], Query(description="Filter by role")] = None
```

### Strings with Constraints
```python
search: Annotated[Optional[str], Query(min_length=2, max_length=100, description="Search query")] = None
email: Annotated[EmailStr, Query(description="Email address")] = ...
```

## Common Return Types

```python
-> ItemResponse              # Single item
-> ItemListResponse          # Paginated list
-> MessageResponse           # Simple success message
-> Dict[str, Any]            # Generic dict (use sparingly)
-> List[ItemResponse]        # List without pagination
-> None                      # No return (rare)
```

## Migration Checklist Per File

- [ ] Add `from typing import Annotated` to imports (if not present)
- [ ] For each endpoint:
  - [ ] Convert `Query(default=X, ...)` to `Annotated[Type, Query(...)] = X`
  - [ ] Add description to every Query parameter
  - [ ] Add return type `-> ResponseModel` to function
  - [ ] Remove `default=` from Query() calls
- [ ] Save file
- [ ] Run type checker: `mypy path/to/file.py`
- [ ] Run tests: `pytest tests/test_api/test_filename.py`
- [ ] Check OpenAPI docs at `/docs`

## Common Mistakes to Avoid

❌ **Wrong**: Keeping `default=` in Query
```python
page: Annotated[int, Query(default=1, ge=1)] = 1  # Redundant!
```

✅ **Right**: Use parameter default only
```python
page: Annotated[int, Query(ge=1, description="Page number")] = 1
```

---

❌ **Wrong**: Missing description
```python
page: Annotated[int, Query(ge=1)] = 1
```

✅ **Right**: Always add description
```python
page: Annotated[int, Query(ge=1, description="Page number")] = 1
```

---

❌ **Wrong**: No return type
```python
async def get_item(...):
```

✅ **Right**: Always add return type
```python
async def get_item(...) -> ItemResponse:
```

---

❌ **Wrong**: Incorrect Annotated syntax
```python
page: int = Query(ge=1)  # Old style
```

✅ **Right**: Use Annotated
```python
page: Annotated[int, Query(ge=1, description="...")] = 1
```

## Copy-Paste Templates

### Template 1: Paginated List Endpoint
```python
@router.get("", response_model=ItemListResponse)
async def list_items(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
    search: Annotated[Optional[str], Query(description="Search in name")] = None,
    is_active: Annotated[Optional[bool], Query(description="Filter by active status")] = None,
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> ItemListResponse:
    """List items with pagination and filters."""
    ...
```

### Template 2: CRUD Endpoints
```python
# CREATE
@router.post("", response_model=ItemResponse, status_code=201)
async def create_item(
    data: ItemCreate,
    request: Request,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
) -> ItemResponse:
    """Create a new item."""
    ...

# READ
@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ItemResponse:
    """Get a single item by ID."""
    ...

# UPDATE
@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: UUID,
    data: ItemUpdate,
    request: Request,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
) -> ItemResponse:
    """Update an item."""
    ...

# DELETE
@router.delete("/{item_id}", response_model=MessageResponse)
async def delete_item(
    item_id: UUID,
    request: Request,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Delete an item."""
    ...
```

## Examples from Completed Files

See these files for real examples:
- `/backend/app/api/v1/dashboard.py` - Simple GET endpoints
- `/backend/app/api/v1/favorites.py` - CRUD with user context
- `/backend/app/api/v1/relations.py` - Complex filtering and nested resources
- `/backend/app/api/v1/entities.py` - Advanced filtering with many parameters

## Testing Command Template

```bash
# After updating a file:

# 1. Check syntax
python -m py_compile backend/app/api/v1/your_file.py

# 2. Run type checker
mypy backend/app/api/v1/your_file.py

# 3. Run specific tests
pytest backend/tests/test_api/test_your_file.py -v

# 4. Start server and check /docs
uvicorn app.main:app --reload
# Then visit: http://localhost:8000/docs
```

## Time Estimate

Per file:
- Simple file (3-5 endpoints): **5 minutes**
- Medium file (6-10 endpoints): **10 minutes**
- Complex file (10+ endpoints): **15 minutes**

Total for all remaining files (32 files):
- **Estimated: 3-5 hours** for complete coverage
