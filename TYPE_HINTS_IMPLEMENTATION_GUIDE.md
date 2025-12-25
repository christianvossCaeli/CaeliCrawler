# Type Hints Implementation Guide

This document provides complete type hint patterns for all FastAPI endpoints in the backend.

## Pattern Overview

### Before
```python
@router.get("/items")
async def list_items(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    ...
```

### After
```python
from typing import Annotated

@router.get("/items", response_model=ItemListResponse)
async def list_items(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
    search: Annotated[Optional[str], Query(description="Search query")] = None,
    session: AsyncSession = Depends(get_session),
) -> ItemListResponse:
    ...
```

## Key Improvements

1. **Annotated Types**: Use `Annotated[Type, Query(...)]` for better OpenAPI documentation
2. **Return Types**: Add explicit return type annotations `-> ResponseModel`
3. **Remove default= from Query**: Use default parameter value instead
4. **Add Descriptions**: Every Query parameter should have a description

## File-by-File Implementation

### backend/app/api/v1/entities.py

Already partially updated. Continue with:

```python
@router.get("/hierarchy/{entity_type_slug}")
async def get_entity_hierarchy(
    entity_type_slug: str,
    root_id: Annotated[Optional[UUID], Query(description="Start from this entity")] = None,
    max_depth: Annotated[int, Query(ge=1, le=10, description="Maximum depth to traverse")] = 3,
    session: AsyncSession = Depends(get_session),
) -> EntityHierarchy:
    ...

@router.get("/filter-options/location", response_model=LocationFilterOptionsResponse)
async def get_location_filter_options(
    country: Annotated[Optional[str], Query(description="Filter admin_level_1 options by country")] = None,
    admin_level_1: Annotated[Optional[str], Query(description="Filter admin_level_2 options by admin_level_1")] = None,
    session: AsyncSession = Depends(get_session),
) -> LocationFilterOptionsResponse:
    ...

@router.get("/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> EntityResponse:
    ...

@router.put("/{entity_id}", response_model=EntityResponse)
async def update_entity(
    entity_id: UUID,
    data: EntityUpdate,
    request: Request,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
) -> EntityResponse:
    ...

@router.delete("/{entity_id}", response_model=MessageResponse)
async def delete_entity(
    entity_id: UUID,
    request: Request,
    force: Annotated[bool, Query(description="Force delete with all facets and relations")] = False,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    ...
```

### backend/app/api/v1/dashboard.py

```python
@router.get("/preferences", response_model=DashboardPreferencesResponse)
async def get_dashboard_preferences(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DashboardPreferencesResponse:
    ...

@router.put("/preferences", response_model=DashboardPreferencesResponse)
async def update_dashboard_preferences(
    update: DashboardPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DashboardPreferencesResponse:
    ...

@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DashboardStatsResponse:
    ...

@router.get("/activity", response_model=ActivityFeedResponse)
async def get_activity_feed(
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum items to return")] = 20,
    offset: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ActivityFeedResponse:
    ...

@router.get("/insights", response_model=InsightsResponse)
async def get_user_insights(
    period_days: Annotated[int, Query(ge=1, le=30, description="Number of days to analyze")] = 7,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InsightsResponse:
    ...

@router.get("/charts/{chart_type}", response_model=ChartDataResponse)
async def get_chart_data(
    chart_type: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChartDataResponse:
    ...
```

### backend/app/api/v1/favorites.py

```python
@router.get("", response_model=FavoriteListResponse)
async def list_favorites(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    entity_type_slug: Annotated[Optional[str], Query(description="Filter by entity type slug")] = None,
    search: Annotated[Optional[str], Query(description="Search in entity name")] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> FavoriteListResponse:
    ...

@router.post("", response_model=FavoriteResponse, status_code=201)
async def add_favorite(
    data: FavoriteCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> FavoriteResponse:
    ...

@router.get("/check/{entity_id}", response_model=FavoriteCheckResponse)
async def check_favorite(
    entity_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> FavoriteCheckResponse:
    ...

@router.delete("/{favorite_id}", response_model=MessageResponse)
async def remove_favorite(
    favorite_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    ...

@router.delete("/entity/{entity_id}", response_model=MessageResponse)
async def remove_favorite_by_entity(
    entity_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    ...
```

### backend/app/api/v1/attachments.py

```python
@router.post("/entities/{entity_id}/attachments")
async def upload_attachment(
    entity_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    description: Annotated[Optional[str], Query(max_length=500, description="File description")] = None,
    auto_analyze: Annotated[bool, Query(description="Start AI analysis immediately")] = False,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    ...

@router.get("/entities/{entity_id}/attachments")
async def list_attachments(
    entity_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    ...

@router.get("/entities/{entity_id}/attachments/{attachment_id}")
async def get_attachment(
    entity_id: UUID,
    attachment_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    ...

@router.delete("/entities/{entity_id}/attachments/{attachment_id}")
async def delete_attachment(
    entity_id: UUID,
    attachment_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    ...
```

### backend/app/api/v1/export.py

```python
@router.get("/json")
async def export_json(
    category_id: Annotated[Optional[UUID], Query(description="Filter by category")] = None,
    source_id: Annotated[Optional[UUID], Query(description="Filter by source")] = None,
    min_confidence: Annotated[Optional[float], Query(ge=0, le=1, description="Minimum confidence score")] = None,
    human_verified_only: Annotated[bool, Query(description="Only include verified items")] = False,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> StreamingResponse:
    ...

@router.get("/csv")
async def export_csv(
    category_id: Annotated[Optional[UUID], Query(description="Filter by category")] = None,
    source_id: Annotated[Optional[UUID], Query(description="Filter by source")] = None,
    min_confidence: Annotated[Optional[float], Query(ge=0, le=1, description="Minimum confidence score")] = None,
    human_verified_only: Annotated[bool, Query(description="Only include verified items")] = False,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> StreamingResponse:
    ...

@router.post("/async", response_model=ExportJobResponse)
async def start_async_export(
    export_request: AsyncExportRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ExportJobResponse:
    ...
```

### backend/app/api/v1/facets.py

```python
@router.get("/types", response_model=FacetTypeListResponse)
async def list_facet_types(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
    is_active: Annotated[Optional[bool], Query(description="Filter by active status")] = None,
    ai_extraction_enabled: Annotated[Optional[bool], Query(description="Filter by AI extraction status")] = None,
    is_time_based: Annotated[Optional[bool], Query(description="Filter by time-based facets")] = None,
    search: Annotated[Optional[str], Query(description="Search in name or slug")] = None,
    session: AsyncSession = Depends(get_session),
) -> FacetTypeListResponse:
    ...

@router.post("/types", response_model=FacetTypeResponse, status_code=201)
async def create_facet_type(
    data: FacetTypeCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
) -> FacetTypeResponse:
    ...

@router.get("/values", response_model=FacetValueListResponse)
async def list_facet_values(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=200, description="Items per page")] = 50,
    entity_id: Annotated[Optional[UUID], Query(description="Filter by entity")] = None,
    facet_type_id: Annotated[Optional[UUID], Query(description="Filter by facet type ID")] = None,
    facet_type_slug: Annotated[Optional[str], Query(description="Filter by facet type slug")] = None,
    category_id: Annotated[Optional[UUID], Query(description="Filter by category")] = None,
    min_confidence: Annotated[float, Query(ge=0, le=1, description="Minimum confidence score")] = 0.0,
    human_verified: Annotated[Optional[bool], Query(description="Filter by verification status")] = None,
    search: Annotated[Optional[str], Query(min_length=2, description="Search in text_representation")] = None,
    time_filter: Annotated[Optional[str], Query(pattern="^(future_only|past_only|all)$", description="Time filter")] = None,
    is_active: Annotated[Optional[bool], Query(description="Filter by active status")] = None,
    session: AsyncSession = Depends(get_session),
) -> FacetValueListResponse:
    ...
```

### backend/app/api/v1/relations.py

```python
@router.get("/types", response_model=RelationTypeListResponse)
async def list_relation_types(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
    is_active: Annotated[Optional[bool], Query(description="Filter by active status")] = None,
    source_entity_type_id: Annotated[Optional[UUID], Query(description="Filter by source entity type")] = None,
    target_entity_type_id: Annotated[Optional[UUID], Query(description="Filter by target entity type")] = None,
    search: Annotated[Optional[str], Query(description="Search in name or slug")] = None,
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> RelationTypeListResponse:
    ...

@router.get("", response_model=EntityRelationListResponse)
async def list_entity_relations(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=200, description="Items per page")] = 50,
    relation_type_id: Annotated[Optional[UUID], Query(description="Filter by relation type ID")] = None,
    relation_type_slug: Annotated[Optional[str], Query(description="Filter by relation type slug")] = None,
    source_entity_id: Annotated[Optional[UUID], Query(description="Filter by source entity")] = None,
    target_entity_id: Annotated[Optional[UUID], Query(description="Filter by target entity")] = None,
    entity_id: Annotated[Optional[UUID], Query(description="Either source or target")] = None,
    min_confidence: Annotated[float, Query(ge=0, le=1, description="Minimum confidence score")] = 0.0,
    human_verified: Annotated[Optional[bool], Query(description="Filter by verification status")] = None,
    is_active: Annotated[Optional[bool], Query(description="Filter by active status")] = None,
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> EntityRelationListResponse:
    ...
```

### backend/app/api/admin/users.py

```python
@router.get("", response_model=UserListResponse)
async def list_users(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    role: Annotated[Optional[UserRole], Query(description="Filter by role")] = None,
    is_active: Annotated[Optional[bool], Query(description="Filter by active status")] = None,
    search: Annotated[Optional[str], Query(description="Search in email or full name")] = None,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> UserListResponse:
    ...

@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    data: UserCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> UserResponse:
    ...

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> UserResponse:
    ...

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> UserResponse:
    ...

@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> MessageResponse:
    ...
```

### backend/app/api/admin/sources.py

```python
@router.get("", response_model=DataSourceListResponse)
@limiter.limit("60/minute")
async def list_sources(
    request: Request,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=10000, description="Items per page")] = 20,
    category_id: Annotated[Optional[UUID], Query(description="Filter by category (N:M)")] = None,
    status: Annotated[Optional[SourceStatus], Query(description="Filter by status")] = None,
    source_type: Annotated[Optional[SourceType], Query(description="Filter by source type")] = None,
    search: Annotated[Optional[str], Query(max_length=200, description="Search in name or URL")] = None,
    tags: Annotated[Optional[List[str]], Query(description="Filter by tags (OR logic)")] = None,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
) -> DataSourceListResponse:
    ...

@router.post("", response_model=DataSourceResponse, status_code=201)
@limiter.limit("20/minute")
async def create_source(
    request: Request,
    data: DataSourceCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
) -> DataSourceResponse:
    ...
```

### backend/app/api/auth.py

```python
@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    ...

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    ...

@router.post("/sse-ticket", response_model=SSETicketResponse)
async def get_sse_ticket(
    current_user: User = Depends(get_current_user),
) -> SSETicketResponse:
    ...

@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    data: PasswordChangeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    ...

@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    ...

@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    data: RefreshRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    ...

@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    current_session_id: Optional[UUID] = Depends(get_current_session_id),
    session: AsyncSession = Depends(get_session),
) -> SessionListResponse:
    ...
```

## Helper Functions

Helper functions should also have complete type hints:

```python
def validate_webhook_url(url: str) -> Tuple[bool, str]:
    """Validate URL for SSRF protection."""
    ...

async def _bulk_load_related_data(
    session: AsyncSession,
    extractions: List[ExtractedData]
) -> Tuple[Dict[UUID, Document], Dict[UUID, DataSource], Dict[UUID, Category]]:
    """Bulk-load all related documents, sources, and categories."""
    ...

def _count_nodes(tree: List[Dict]) -> int:
    """Count total nodes in tree."""
    ...
```

## Implementation Checklist

- [ ] backend/app/api/v1/entities.py
- [ ] backend/app/api/v1/dashboard.py
- [ ] backend/app/api/v1/favorites.py
- [ ] backend/app/api/v1/attachments.py
- [ ] backend/app/api/v1/export.py
- [ ] backend/app/api/v1/facets.py
- [ ] backend/app/api/v1/relations.py
- [ ] backend/app/api/v1/pysis_facets.py
- [ ] backend/app/api/v1/entity_data.py
- [ ] backend/app/api/v1/ai_tasks.py
- [ ] backend/app/api/v1/entity_types.py
- [ ] backend/app/api/v1/smart_query_history.py
- [ ] backend/app/api/v1/assistant.py
- [ ] backend/app/api/v1/summaries.py
- [ ] backend/app/api/admin/users.py
- [ ] backend/app/api/admin/sources.py
- [ ] backend/app/api/admin/versions.py
- [ ] backend/app/api/admin/audit.py
- [ ] backend/app/api/admin/pysis.py
- [ ] backend/app/api/admin/ai_discovery.py
- [ ] backend/app/api/admin/locations.py
- [ ] backend/app/api/admin/external_apis.py
- [ ] backend/app/api/admin/api_templates.py
- [ ] backend/app/api/admin/api_import.py
- [ ] backend/app/api/admin/notifications.py
- [ ] backend/app/api/admin/crawler_jobs.py
- [ ] backend/app/api/admin/crawler_ai.py
- [ ] backend/app/api/admin/crawler_documents.py
- [ ] backend/app/api/admin/categories.py
- [ ] backend/app/api/admin/crawler.py
- [ ] backend/app/api/admin/crawler_sse.py
- [ ] backend/app/api/admin/crawl_presets.py
- [ ] backend/app/api/admin/api_facet_sync.py
- [ ] backend/app/api/admin/sharepoint.py
- [ ] backend/app/api/admin/crawler_control.py
- [ ] backend/app/api/admin/custom_summaries.py
- [ ] backend/app/api/auth.py

## Benefits

1. **Better OpenAPI Documentation**: Annotated types provide rich descriptions in the generated API docs
2. **IDE Support**: Better autocomplete and type checking in IDEs
3. **Runtime Validation**: FastAPI uses these types for request validation
4. **Code Maintainability**: Clear contracts for what each endpoint expects and returns
5. **Error Prevention**: Type checkers (mypy, pyright) can catch type errors before runtime
