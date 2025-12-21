"""Admin API endpoints for managing API templates.

Templates store validated API configurations for reuse in KI-First Discovery.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.core.deps import require_editor
from app.core.rate_limit import check_rate_limit
from app.models import User
from app.models.api_template import APITemplate, APIType, TemplateStatus
from services.ai_source_discovery import (
    APISuggestion,
    validate_api_suggestions,
)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class APITemplateCreate(BaseModel):
    """Request to create a new API template."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    api_type: str = Field(default="REST", pattern="^(REST|GRAPHQL|SPARQL|OPARL)$")
    base_url: str = Field(..., min_length=1)
    endpoint: str = Field(..., min_length=1)
    documentation_url: Optional[str] = None
    auth_required: bool = False
    auth_config: Optional[dict] = None
    field_mapping: dict = Field(default_factory=dict)
    keywords: List[str] = Field(default_factory=list)
    default_tags: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class APITemplateUpdate(BaseModel):
    """Request to update an API template."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    api_type: Optional[str] = Field(None, pattern="^(REST|GRAPHQL|SPARQL|OPARL)$")
    base_url: Optional[str] = None
    endpoint: Optional[str] = None
    documentation_url: Optional[str] = None
    auth_required: Optional[bool] = None
    auth_config: Optional[dict] = None
    field_mapping: Optional[dict] = None
    keywords: Optional[List[str]] = None
    default_tags: Optional[List[str]] = None
    status: Optional[str] = Field(None, pattern="^(ACTIVE|INACTIVE|FAILED|PENDING)$")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class APITemplateResponse(BaseModel):
    """API template response."""
    id: UUID
    name: str
    description: Optional[str]
    api_type: str
    base_url: str
    endpoint: str
    full_url: str
    documentation_url: Optional[str]
    auth_required: bool
    field_mapping: dict
    keywords: List[str]
    default_tags: List[str]
    status: str
    last_validated: Optional[datetime]
    last_validation_error: Optional[str]
    validation_item_count: Optional[int]
    usage_count: int
    last_used: Optional[datetime]
    confidence: float
    source: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class APITemplateTestResult(BaseModel):
    """Result of testing an API template."""
    is_valid: bool
    status_code: Optional[int]
    item_count: Optional[int]
    error_message: Optional[str]
    field_mapping: dict
    sample_data: Optional[List[dict]] = None


class SaveFromDiscoveryRequest(BaseModel):
    """Request to save a template from a successful discovery."""
    api_name: str
    base_url: str
    endpoint: str
    description: str = ""
    api_type: str = "REST"
    auth_required: bool = False
    documentation_url: Optional[str] = None
    field_mapping: dict = Field(default_factory=dict)
    keywords: List[str] = Field(default_factory=list)
    default_tags: List[str] = Field(default_factory=list)
    confidence: float = 0.8
    validation_item_count: Optional[int] = None


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=List[APITemplateResponse])
async def list_templates(
    status_filter: Optional[str] = None,
    api_type: Optional[str] = None,
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
):
    """
    List all API templates.

    Parameters:
    - **status_filter**: Filter by status (ACTIVE, INACTIVE, FAILED, PENDING)
    - **api_type**: Filter by API type (REST, GRAPHQL, SPARQL, OPARL)
    - **search**: Search in name and keywords
    """
    query = select(APITemplate).order_by(APITemplate.usage_count.desc())

    if status_filter:
        try:
            status_enum = TemplateStatus(status_filter)
            query = query.where(APITemplate.status == status_enum)
        except ValueError:
            pass

    if api_type:
        try:
            type_enum = APIType(api_type)
            query = query.where(APITemplate.api_type == type_enum)
        except ValueError:
            pass

    if search:
        search_lower = f"%{search.lower()}%"
        query = query.where(
            APITemplate.name.ilike(search_lower)
        )

    result = await session.execute(query)
    templates = result.scalars().all()

    return [
        APITemplateResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            api_type=t.api_type.value,
            base_url=t.base_url,
            endpoint=t.endpoint,
            full_url=t.full_url,
            documentation_url=t.documentation_url,
            auth_required=t.auth_required,
            field_mapping=t.field_mapping,
            keywords=t.keywords,
            default_tags=t.default_tags,
            status=t.status.value,
            last_validated=t.last_validated,
            last_validation_error=t.last_validation_error,
            validation_item_count=t.validation_item_count,
            usage_count=t.usage_count,
            last_used=t.last_used,
            confidence=t.confidence,
            source=t.source,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in templates
    ]


@router.get("/{template_id}", response_model=APITemplateResponse)
async def get_template(
    template_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
):
    """Get a single API template by ID."""
    template = await session.get(APITemplate, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found",
        )

    return APITemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        api_type=template.api_type.value,
        base_url=template.base_url,
        endpoint=template.endpoint,
        full_url=template.full_url,
        documentation_url=template.documentation_url,
        auth_required=template.auth_required,
        field_mapping=template.field_mapping,
        keywords=template.keywords,
        default_tags=template.default_tags,
        status=template.status.value,
        last_validated=template.last_validated,
        last_validation_error=template.last_validation_error,
        validation_item_count=template.validation_item_count,
        usage_count=template.usage_count,
        last_used=template.last_used,
        confidence=template.confidence,
        source=template.source,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.post("", response_model=APITemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    request: APITemplateCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
):
    """
    Create a new API template manually.

    The template will have status=PENDING until validated.
    """
    template = APITemplate(
        name=request.name,
        description=request.description,
        api_type=APIType(request.api_type),
        base_url=request.base_url,
        endpoint=request.endpoint,
        documentation_url=request.documentation_url,
        auth_required=request.auth_required,
        auth_config=request.auth_config,
        field_mapping=request.field_mapping,
        keywords=request.keywords,
        default_tags=request.default_tags,
        confidence=request.confidence,
        source="manual",
        created_by_id=user.id,
        status=TemplateStatus.PENDING,
    )

    session.add(template)
    await session.commit()
    await session.refresh(template)

    return APITemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        api_type=template.api_type.value,
        base_url=template.base_url,
        endpoint=template.endpoint,
        full_url=template.full_url,
        documentation_url=template.documentation_url,
        auth_required=template.auth_required,
        field_mapping=template.field_mapping,
        keywords=template.keywords,
        default_tags=template.default_tags,
        status=template.status.value,
        last_validated=template.last_validated,
        last_validation_error=template.last_validation_error,
        validation_item_count=template.validation_item_count,
        usage_count=template.usage_count,
        last_used=template.last_used,
        confidence=template.confidence,
        source=template.source,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.put("/{template_id}", response_model=APITemplateResponse)
async def update_template(
    template_id: UUID,
    request: APITemplateUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
):
    """Update an existing API template."""
    template = await session.get(APITemplate, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found",
        )

    # Update fields
    if request.name is not None:
        template.name = request.name
    if request.description is not None:
        template.description = request.description
    if request.api_type is not None:
        template.api_type = APIType(request.api_type)
    if request.base_url is not None:
        template.base_url = request.base_url
    if request.endpoint is not None:
        template.endpoint = request.endpoint
    if request.documentation_url is not None:
        template.documentation_url = request.documentation_url
    if request.auth_required is not None:
        template.auth_required = request.auth_required
    if request.auth_config is not None:
        template.auth_config = request.auth_config
    if request.field_mapping is not None:
        template.field_mapping = request.field_mapping
    if request.keywords is not None:
        template.keywords = request.keywords
    if request.default_tags is not None:
        template.default_tags = request.default_tags
    if request.status is not None:
        template.status = TemplateStatus(request.status)
    if request.confidence is not None:
        template.confidence = request.confidence

    await session.commit()
    await session.refresh(template)

    return APITemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        api_type=template.api_type.value,
        base_url=template.base_url,
        endpoint=template.endpoint,
        full_url=template.full_url,
        documentation_url=template.documentation_url,
        auth_required=template.auth_required,
        field_mapping=template.field_mapping,
        keywords=template.keywords,
        default_tags=template.default_tags,
        status=template.status.value,
        last_validated=template.last_validated,
        last_validation_error=template.last_validation_error,
        validation_item_count=template.validation_item_count,
        usage_count=template.usage_count,
        last_used=template.last_used,
        confidence=template.confidence,
        source=template.source,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
):
    """Delete an API template."""
    template = await session.get(APITemplate, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found",
        )

    await session.delete(template)
    await session.commit()


@router.post("/{template_id}/test", response_model=APITemplateTestResult)
async def test_template(
    template_id: UUID,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
):
    """
    Test an API template by making a real HTTP request.

    Updates the template's validation status based on the result.
    """
    await check_rate_limit(http_request, "api_template_test", identifier=str(user.id))

    template = await session.get(APITemplate, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found",
        )

    # Create APISuggestion from template
    suggestion = APISuggestion(
        api_name=template.name,
        base_url=template.base_url,
        endpoint=template.endpoint,
        description=template.description or "",
        api_type=template.api_type.value,
        auth_required=template.auth_required,
        confidence=template.confidence,
    )

    # Validate
    results = await validate_api_suggestions([suggestion])
    result = results[0] if results else None

    if result and result.is_valid:
        # Update template on success
        template.status = TemplateStatus.ACTIVE
        template.last_validated = datetime.utcnow()
        template.last_validation_error = None
        template.validation_item_count = result.item_count

        # Update field mapping if detected
        if result.field_mapping and not template.field_mapping:
            template.field_mapping = result.field_mapping

        await session.commit()

        return APITemplateTestResult(
            is_valid=True,
            status_code=result.status_code,
            item_count=result.item_count,
            error_message=None,
            field_mapping=result.field_mapping,
            sample_data=result.sample_data,
        )
    else:
        # Update template on failure
        template.status = TemplateStatus.FAILED
        template.last_validated = datetime.utcnow()
        template.last_validation_error = result.error_message if result else "Validation failed"

        await session.commit()

        return APITemplateTestResult(
            is_valid=False,
            status_code=result.status_code if result else None,
            item_count=None,
            error_message=result.error_message if result else "Validation failed",
            field_mapping={},
            sample_data=None,
        )


@router.post("/save-from-discovery", response_model=APITemplateResponse, status_code=status.HTTP_201_CREATED)
async def save_from_discovery(
    request: SaveFromDiscoveryRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
):
    """
    Save a template from a successful KI-First discovery.

    Called by the frontend after a successful API validation.
    The template is immediately marked as ACTIVE since it was just validated.
    """
    # Check if template with same URL already exists
    existing = await session.execute(
        select(APITemplate).where(
            APITemplate.base_url == request.base_url,
            APITemplate.endpoint == request.endpoint,
        )
    )
    if existing.scalar():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A template with this API URL already exists",
        )

    template = APITemplate(
        name=request.api_name,
        description=request.description,
        api_type=APIType(request.api_type),
        base_url=request.base_url,
        endpoint=request.endpoint,
        documentation_url=request.documentation_url,
        auth_required=request.auth_required,
        field_mapping=request.field_mapping,
        keywords=request.keywords,
        default_tags=request.default_tags,
        confidence=request.confidence,
        source="ai_generated",
        created_by_id=user.id,
        # Already validated
        status=TemplateStatus.ACTIVE,
        last_validated=datetime.utcnow(),
        validation_item_count=request.validation_item_count,
    )

    session.add(template)
    await session.commit()
    await session.refresh(template)

    return APITemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        api_type=template.api_type.value,
        base_url=template.base_url,
        endpoint=template.endpoint,
        full_url=template.full_url,
        documentation_url=template.documentation_url,
        auth_required=template.auth_required,
        field_mapping=template.field_mapping,
        keywords=template.keywords,
        default_tags=template.default_tags,
        status=template.status.value,
        last_validated=template.last_validated,
        last_validation_error=template.last_validation_error,
        validation_item_count=template.validation_item_count,
        usage_count=template.usage_count,
        last_used=template.last_used,
        confidence=template.confidence,
        source=template.source,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.get("/match/{prompt}", response_model=List[APITemplateResponse])
async def match_templates(
    prompt: str,
    min_score: float = 0.3,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
):
    """
    Find templates that match a user prompt.

    Used by KI-First discovery to check for saved templates before
    generating new API suggestions.

    Parameters:
    - **prompt**: The user's search prompt
    - **min_score**: Minimum match score (0.0-1.0)
    """
    # Get all active templates
    result = await session.execute(
        select(APITemplate).where(APITemplate.status == TemplateStatus.ACTIVE)
    )
    templates = result.scalars().all()

    # Calculate match scores
    matches = []
    for template in templates:
        score = template.matches_prompt(prompt)
        if score >= min_score:
            matches.append((template, score))

    # Sort by score descending
    matches.sort(key=lambda x: x[1], reverse=True)

    return [
        APITemplateResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            api_type=t.api_type.value,
            base_url=t.base_url,
            endpoint=t.endpoint,
            full_url=t.full_url,
            documentation_url=t.documentation_url,
            auth_required=t.auth_required,
            field_mapping=t.field_mapping,
            keywords=t.keywords,
            default_tags=t.default_tags,
            status=t.status.value,
            last_validated=t.last_validated,
            last_validation_error=t.last_validation_error,
            validation_item_count=t.validation_item_count,
            usage_count=t.usage_count,
            last_used=t.last_used,
            confidence=t.confidence,
            source=t.source,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t, score in matches
    ]
