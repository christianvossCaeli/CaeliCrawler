"""Admin API endpoints for PySis integration."""

import json
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import require_editor, require_admin
from app.core.exceptions import FeatureDisabledError, NotFoundError, ValidationError
from app.database import get_session
from app.models import Entity, User
from app.models.pysis import (
    PySisFieldHistory,
    PySisFieldTemplate,
    PySisProcess,
    PySisProcessField,
    SyncStatus,
    ValueSource,
)
from app.schemas.common import MessageResponse
from app.schemas.pysis import (
    AcceptAISuggestionRequest,
    AcceptAISuggestionResult,
    ApplyTemplateRequest,
    PySisAnalyzeForFacetsRequest,
    PySisAnalyzeForFacetsResult,
    PySisFieldCreate,
    PySisFieldHistoryListResponse,
    PySisFieldHistoryResponse,
    PySisFieldResponse,
    PySisFieldTemplateCreate,
    PySisFieldTemplateListResponse,
    PySisFieldTemplateResponse,
    PySisFieldTemplateUpdate,
    PySisFieldUpdate,
    PySisFieldValueUpdate,
    PySisGenerateRequest,
    PySisGenerateResult,
    PySisProcessCreate,
    PySisProcessDetailResponse,
    PySisProcessListResponse,
    PySisProcessResponse,
    PySisProcessUpdate,
    PySisPullResult,
    PySisSyncResult,
    PySisTestConnectionResult,
)
from services.pysis_facet_service import PySisFacetService
from services.pysis_service import get_pysis_service
from workers.ai_tasks import extract_pysis_fields

router = APIRouter()


def require_templates_feature():
    """Dependency that checks if the PySis field templates feature is enabled."""
    if not settings.feature_pysis_field_templates:
        raise FeatureDisabledError("pysis_field_templates")
    return True


# === Templates ===

@router.get("/templates", response_model=PySisFieldTemplateListResponse)
async def list_templates(
    is_active: Optional[bool] = Query(default=None),
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(require_templates_feature),
    __: User = Depends(require_editor),
):
    """List all field templates."""
    query = select(PySisFieldTemplate)
    if is_active is not None:
        query = query.where(PySisFieldTemplate.is_active == is_active)
    query = query.order_by(PySisFieldTemplate.name)

    result = await session.execute(query)
    templates = result.scalars().all()

    return PySisFieldTemplateListResponse(
        items=[PySisFieldTemplateResponse.model_validate(t) for t in templates],
        total=len(templates),
    )


@router.post("/templates", response_model=PySisFieldTemplateResponse)
async def create_template(
    data: PySisFieldTemplateCreate,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(require_templates_feature),
    __: User = Depends(require_admin),
):
    """Create a new field template."""
    template = PySisFieldTemplate(
        name=data.name,
        description=data.description,
        fields=[f.model_dump() for f in data.fields],
        is_active=True,
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return PySisFieldTemplateResponse.model_validate(template)


@router.get("/templates/{template_id}", response_model=PySisFieldTemplateResponse)
async def get_template(
    template_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(require_templates_feature),
    __: User = Depends(require_editor),
):
    """Get a template by ID."""
    template = await session.get(PySisFieldTemplate, template_id)
    if not template:
        raise NotFoundError("Template", str(template_id))
    return PySisFieldTemplateResponse.model_validate(template)


@router.put("/templates/{template_id}", response_model=PySisFieldTemplateResponse)
async def update_template(
    template_id: UUID,
    data: PySisFieldTemplateUpdate,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(require_templates_feature),
    __: User = Depends(require_admin),
):
    """Update a template."""
    template = await session.get(PySisFieldTemplate, template_id)
    if not template:
        raise NotFoundError("Template", str(template_id))

    if data.name is not None:
        template.name = data.name
    if data.description is not None:
        template.description = data.description
    if data.fields is not None:
        template.fields = [f.model_dump() for f in data.fields]
    if data.is_active is not None:
        template.is_active = data.is_active

    await session.commit()
    await session.refresh(template)
    return PySisFieldTemplateResponse.model_validate(template)


@router.delete("/templates/{template_id}", response_model=MessageResponse)
async def delete_template(
    template_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(require_templates_feature),
    __: User = Depends(require_admin),
):
    """Delete a template."""
    template = await session.get(PySisFieldTemplate, template_id)
    if not template:
        raise NotFoundError("Template", str(template_id))

    await session.delete(template)
    await session.commit()
    return MessageResponse(message="Template deleted")


# === Processes ===

@router.get("/locations/{location_name}/processes", response_model=PySisProcessListResponse)
async def list_location_processes(
    location_name: str,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """List all PySis processes for a location."""
    # Escape SQL wildcards to prevent injection
    safe_name = location_name.replace('%', '\\%').replace('_', '\\_')
    query = select(PySisProcess).where(
        PySisProcess.entity_name.ilike(f"%{safe_name}%", escape='\\')
    ).order_by(PySisProcess.created_at.desc())

    result = await session.execute(query)
    processes = result.scalars().all()

    items = []
    for p in processes:
        item = PySisProcessResponse.model_validate(p)
        item.field_count = len(p.fields) if p.fields else 0
        items.append(item)

    return PySisProcessListResponse(items=items, total=len(items))


@router.post("/locations/{location_name}/processes", response_model=PySisProcessResponse)
async def create_process(
    location_name: str,
    data: PySisProcessCreate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Create a new PySis process link for a location."""
    # Check if template feature is enabled when template_id is provided
    if data.template_id and not settings.feature_pysis_field_templates:
        raise FeatureDisabledError("pysis_field_templates")

    # Find matching Entity by name - entity_id is required
    entity_result = await session.execute(
        select(Entity).where(Entity.name == location_name).limit(1)
    )
    entity = entity_result.scalar_one_or_none()

    if not entity:
        raise HTTPException(
            status_code=404,
            detail=f"Entity '{location_name}' nicht gefunden. PySis-Prozess kann nur mit existierender Entity verknüpft werden."
        )

    process = PySisProcess(
        entity_id=entity.id,
        entity_name=location_name,  # For display purposes
        pysis_process_id=data.pysis_process_id,
        name=data.name,
        description=data.description,
        template_id=data.template_id if settings.feature_pysis_field_templates else None,
        sync_status=SyncStatus.NEVER,
    )
    session.add(process)
    await session.commit()
    await session.refresh(process)

    # If template provided and feature enabled, apply it
    if data.template_id and settings.feature_pysis_field_templates:
        template = await session.get(PySisFieldTemplate, data.template_id)
        if template:
            for field_def in template.fields:
                field = PySisProcessField(
                    process_id=process.id,
                    internal_name=field_def.get("internal_name", ""),
                    pysis_field_name=field_def.get("pysis_field_name", ""),
                    field_type=field_def.get("field_type", "text"),
                    ai_extraction_enabled=True,
                    ai_extraction_prompt=field_def.get("ai_extraction_prompt"),
                    value_source=ValueSource.AI,
                )
                session.add(field)
            await session.commit()
            await session.refresh(process)

    response = PySisProcessResponse.model_validate(process)
    response.field_count = len(process.fields) if process.fields else 0
    return response


@router.get("/processes/{process_id}", response_model=PySisProcessDetailResponse)
async def get_process(
    process_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Get process details with all fields."""
    process = await session.get(PySisProcess, process_id)
    if not process:
        raise NotFoundError("Process", str(process_id))

    response = PySisProcessDetailResponse.model_validate(process)
    response.field_count = len(process.fields) if process.fields else 0
    response.fields = [PySisFieldResponse.model_validate(f) for f in process.fields]
    return response


@router.put("/processes/{process_id}", response_model=PySisProcessResponse)
async def update_process(
    process_id: UUID,
    data: PySisProcessUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Update a process."""
    process = await session.get(PySisProcess, process_id)
    if not process:
        raise NotFoundError("Process", str(process_id))

    if data.name is not None:
        process.name = data.name
    if data.description is not None:
        process.description = data.description

    await session.commit()
    await session.refresh(process)

    response = PySisProcessResponse.model_validate(process)
    response.field_count = len(process.fields) if process.fields else 0
    return response


@router.delete("/processes/{process_id}", response_model=MessageResponse)
async def delete_process(
    process_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """Delete a process and all its fields."""
    process = await session.get(PySisProcess, process_id)
    if not process:
        raise NotFoundError("Process", str(process_id))

    await session.delete(process)
    await session.commit()
    return MessageResponse(message="Process deleted")


@router.post("/processes/{process_id}/apply-template", response_model=PySisProcessResponse)
async def apply_template_to_process(
    process_id: UUID,
    data: ApplyTemplateRequest,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(require_templates_feature),
    __: User = Depends(require_editor),
):
    """
    Apply a template to a process.

    This enables AI extraction for fields matching the template definitions.
    Fields must already exist (use Pull from PySis first to create them).

    The template defines:
    - pysis_field_name: Which field to enable AI for
    - ai_extraction_prompt: Optional custom prompt for AI extraction
    """
    process = await session.get(PySisProcess, process_id)
    if not process:
        raise NotFoundError("Process", str(process_id))

    template = await session.get(PySisFieldTemplate, data.template_id)
    if not template:
        raise NotFoundError("Template", str(data.template_id))

    # Build lookup of existing fields by pysis_field_name
    existing_fields = {f.pysis_field_name: f for f in process.fields}

    fields_enabled = 0
    fields_not_found = []

    for field_def in template.fields:
        pysis_field_name = field_def.get("pysis_field_name", "")

        if pysis_field_name in existing_fields:
            field = existing_fields[pysis_field_name]
            # Enable AI extraction
            field.ai_extraction_enabled = True
            # Set prompt if provided in template
            if field_def.get("ai_extraction_prompt"):
                field.ai_extraction_prompt = field_def["ai_extraction_prompt"]
            fields_enabled += 1
        else:
            fields_not_found.append(pysis_field_name)

    process.template_id = data.template_id
    await session.commit()
    await session.refresh(process)

    response = PySisProcessResponse.model_validate(process)
    response.field_count = len(process.fields) if process.fields else 0
    response.extra = {
        "fields_enabled": fields_enabled,
        "fields_not_found": fields_not_found,
    }
    return response


# === Fields ===

@router.get("/processes/{process_id}/fields", response_model=List[PySisFieldResponse])
async def list_process_fields(
    process_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """List all fields for a process."""
    process = await session.get(PySisProcess, process_id)
    if not process:
        raise NotFoundError("Process", str(process_id))

    return [PySisFieldResponse.model_validate(f) for f in process.fields]


@router.post("/processes/{process_id}/fields", response_model=PySisFieldResponse)
async def create_field(
    process_id: UUID,
    data: PySisFieldCreate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Create a new field for a process."""
    process = await session.get(PySisProcess, process_id)
    if not process:
        raise NotFoundError("Process", str(process_id))

    field = PySisProcessField(
        process_id=process_id,
        internal_name=data.internal_name,
        pysis_field_name=data.pysis_field_name,
        field_type=data.field_type,
        ai_extraction_enabled=data.ai_extraction_enabled,
        ai_extraction_prompt=data.ai_extraction_prompt,
        value_source=ValueSource.AI,
    )
    session.add(field)
    await session.commit()
    await session.refresh(field)
    return PySisFieldResponse.model_validate(field)


@router.put("/fields/{field_id}", response_model=PySisFieldResponse)
async def update_field(
    field_id: UUID,
    data: PySisFieldUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Update a field."""
    field = await session.get(PySisProcessField, field_id)
    if not field:
        raise NotFoundError("Field", str(field_id))

    if data.internal_name is not None:
        field.internal_name = data.internal_name
    if data.field_type is not None:
        field.field_type = data.field_type
    if data.ai_extraction_enabled is not None:
        field.ai_extraction_enabled = data.ai_extraction_enabled
    if data.ai_extraction_prompt is not None:
        field.ai_extraction_prompt = data.ai_extraction_prompt

    await session.commit()
    await session.refresh(field)
    return PySisFieldResponse.model_validate(field)


@router.put("/fields/{field_id}/value", response_model=PySisFieldResponse)
async def update_field_value(
    field_id: UUID,
    data: PySisFieldValueUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Update a field's value."""
    field = await session.get(PySisProcessField, field_id)
    if not field:
        raise NotFoundError("Field", str(field_id))

    if data.source.upper() == "MANUAL":
        field.manual_value = data.value
        field.value_source = ValueSource.MANUAL
    else:
        field.ai_extracted_value = data.value
        field.value_source = ValueSource.AI

    field.current_value = data.value
    field.needs_push = True

    await session.commit()
    await session.refresh(field)
    return PySisFieldResponse.model_validate(field)


@router.delete("/fields/{field_id}", response_model=MessageResponse)
async def delete_field(
    field_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """Delete a field."""
    field = await session.get(PySisProcessField, field_id)
    if not field:
        raise NotFoundError("Field", str(field_id))

    await session.delete(field)
    await session.commit()
    return MessageResponse(message="Field deleted")


# === Sync Operations ===

@router.post("/processes/{process_id}/sync/pull", response_model=PySisPullResult)
async def pull_from_pysis(
    process_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """
    Pull current values from PySis API.

    This will:
    1. Fetch all fields from PySis
    2. Create local PySisProcessField records for any new fields (ai_extraction_enabled=False)
    3. Update existing fields with the current PySis values
    """
    process = await session.get(PySisProcess, process_id)
    if not process:
        raise NotFoundError("Process", str(process_id))

    pysis = get_pysis_service()
    if not pysis.is_configured:
        raise ValidationError("PySis API credentials not configured")

    try:
        process_data = await pysis.get_process(process.pysis_process_id)

        # Build lookup of existing fields by pysis_field_name
        existing_fields = {f.pysis_field_name: f for f in process.fields}

        fields_updated = 0
        fields_created = 0

        # Process ALL fields from PySis
        for field_name, value in process_data.items():
            # Skip internal/meta fields (usually start with underscore or are known meta fields)
            if field_name.startswith('_') or field_name in ('id', 'created_at', 'updated_at', 'process_id'):
                continue

            # Convert value to string
            str_value = None
            if value is not None:
                if isinstance(value, (dict, list)):
                    str_value = json.dumps(value, ensure_ascii=False)
                else:
                    str_value = str(value)

            if field_name in existing_fields:
                # Update existing field
                field = existing_fields[field_name]
                field.pysis_value = str_value
                field.last_pulled_at = datetime.now(timezone.utc)

                # Update current value if empty or source is PYSIS
                if field.current_value is None or field.current_value == "" or field.value_source == ValueSource.PYSIS:
                    field.current_value = str_value
                    field.value_source = ValueSource.PYSIS

                fields_updated += 1
            else:
                # Create new field - AI extraction disabled by default
                new_field = PySisProcessField(
                    process_id=process.id,
                    internal_name=field_name.replace('_', ' ').title(),  # Convert snake_case to Title Case
                    pysis_field_name=field_name,
                    field_type=_infer_field_type(value),
                    ai_extraction_enabled=False,  # User must explicitly enable
                    pysis_value=str_value,
                    current_value=str_value,
                    value_source=ValueSource.PYSIS,
                    last_pulled_at=datetime.now(timezone.utc),
                )
                session.add(new_field)
                fields_created += 1

        process.last_synced_at = datetime.now(timezone.utc)
        process.sync_status = SyncStatus.SYNCED
        process.sync_error = None

        await session.commit()

        return PySisPullResult(
            success=True,
            fields_updated=fields_updated,
            fields_created=fields_created,
            process_data=process_data,
            errors=[],
        )

    except Exception as e:
        process.sync_status = SyncStatus.ERROR
        process.sync_error = str(e)
        await session.commit()

        return PySisPullResult(
            success=False,
            fields_updated=0,
            fields_created=0,
            errors=[str(e)],
        )


def _infer_field_type(value) -> str:
    """Infer field type from value."""
    if value is None:
        return "text"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "number"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    # Check for date-like strings
    str_val = str(value)
    if len(str_val) == 10 and str_val[4] == '-' and str_val[7] == '-':
        return "date"
    return "text"


@router.post("/processes/{process_id}/sync/push", response_model=PySisSyncResult)
async def push_to_pysis(
    process_id: UUID,
    field_ids: Optional[List[UUID]] = Body(None, embed=True),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Push field values to PySis API."""
    process = await session.get(PySisProcess, process_id)
    if not process:
        raise NotFoundError("Process", str(process_id))

    pysis = get_pysis_service()
    if not pysis.is_configured:
        raise ValidationError("PySis API credentials not configured")

    try:
        # Collect fields to push
        fields_to_push = {}
        fields_synced = 0

        for field in process.fields:
            # Skip if specific fields requested and this isn't one of them
            if field_ids and field.id not in field_ids:
                continue

            # Skip if no value or doesn't need push
            if field.current_value is None:
                continue

            if not field.needs_push and field_ids is None:
                continue

            fields_to_push[field.pysis_field_name] = field.current_value

        if fields_to_push:
            await pysis.update_process(process.pysis_process_id, fields_to_push)

            # Mark fields as synced
            for field in process.fields:
                if field.pysis_field_name in fields_to_push:
                    field.needs_push = False
                    field.last_pushed_at = datetime.now(timezone.utc)
                    fields_synced += 1

        process.last_synced_at = datetime.now(timezone.utc)
        process.sync_status = SyncStatus.SYNCED
        process.sync_error = None

        await session.commit()

        return PySisSyncResult(
            success=True,
            fields_synced=fields_synced,
            synced_at=datetime.now(timezone.utc),
            errors=[],
        )

    except Exception as e:
        process.sync_status = SyncStatus.ERROR
        process.sync_error = str(e)
        await session.commit()

        return PySisSyncResult(
            success=False,
            fields_synced=0,
            synced_at=datetime.now(timezone.utc),
            errors=[str(e)],
        )


@router.post("/fields/{field_id}/sync/push", response_model=PySisSyncResult)
async def push_field_to_pysis(
    field_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Push a single field value to PySis API."""
    field = await session.get(PySisProcessField, field_id)
    if not field:
        raise NotFoundError("Field", str(field_id))

    process = await session.get(PySisProcess, field.process_id)
    if not process:
        raise NotFoundError("Process", str(field.process_id))

    pysis = get_pysis_service()
    if not pysis.is_configured:
        raise ValidationError("PySis API credentials not configured")

    try:
        if field.current_value is not None:
            await pysis.update_process_field(
                process.pysis_process_id,
                field.pysis_field_name,
                field.current_value,
            )

            field.needs_push = False
            field.last_pushed_at = datetime.now(timezone.utc)

            process.last_synced_at = datetime.now(timezone.utc)
            process.sync_status = SyncStatus.SYNCED
            process.sync_error = None

            await session.commit()

        return PySisSyncResult(
            success=True,
            fields_synced=1,
            synced_at=datetime.now(timezone.utc),
            errors=[],
        )

    except Exception as e:
        process.sync_status = SyncStatus.ERROR
        process.sync_error = str(e)
        await session.commit()

        return PySisSyncResult(
            success=False,
            fields_synced=0,
            synced_at=datetime.now(timezone.utc),
            errors=[str(e)],
        )


# === AI Generation ===

@router.post("/processes/{process_id}/generate", response_model=PySisGenerateResult)
async def generate_fields(
    process_id: UUID,
    data: Optional[PySisGenerateRequest] = None,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Generate field values using AI."""
    process = await session.get(PySisProcess, process_id)
    if not process:
        raise NotFoundError("Process", str(process_id))

    field_ids = [str(f) for f in data.field_ids] if data and data.field_ids else None

    # Queue the extraction task
    extract_pysis_fields.delay(str(process_id), field_ids)

    # Count fields that will be generated
    count = 0
    for field in process.fields:
        if field.ai_extraction_enabled:
            if field_ids is None or str(field.id) in field_ids:
                count += 1

    return PySisGenerateResult(
        success=True,
        fields_generated=count,
        errors=[],
    )


@router.post("/fields/{field_id}/generate", response_model=PySisGenerateResult)
async def generate_single_field(
    field_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Generate a single field value using AI."""
    field = await session.get(PySisProcessField, field_id)
    if not field:
        raise NotFoundError("Field", str(field_id))

    # Queue the extraction task for just this field
    extract_pysis_fields.delay(str(field.process_id), [str(field_id)])

    return PySisGenerateResult(
        success=True,
        fields_generated=1,
        errors=[],
    )


# === Accept/Reject AI Suggestions ===

@router.post("/fields/{field_id}/accept-ai", response_model=AcceptAISuggestionResult)
async def accept_ai_suggestion(
    field_id: UUID,
    data: Optional[AcceptAISuggestionRequest] = None,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """
    Accept the AI-generated suggestion for a field.

    This will:
    1. Copy ai_extracted_value to current_value
    2. Set value_source to AI
    3. Create a history entry
    4. Optionally push to PySis
    """
    field = await session.get(PySisProcessField, field_id)
    if not field:
        raise NotFoundError("Field", str(field_id))

    if not field.ai_extracted_value:
        return AcceptAISuggestionResult(
            success=False,
            field_id=field_id,
            accepted_value=None,
            message="Kein KI-Vorschlag vorhanden",
        )

    # Create history entry for the old value (if any)
    if field.current_value:
        old_history = PySisFieldHistory(
            field_id=field.id,
            value=field.current_value,
            source=field.value_source,
            confidence_score=None,
            action="replaced",
        )
        session.add(old_history)

    # Accept the AI value
    field.current_value = field.ai_extracted_value
    field.value_source = ValueSource.AI
    field.needs_push = True

    # Create history entry for the accepted value
    history = PySisFieldHistory(
        field_id=field.id,
        value=field.ai_extracted_value,
        source=ValueSource.AI,
        confidence_score=field.confidence_score,
        action="accepted",
    )
    session.add(history)

    await session.commit()

    # Optionally push to PySis
    push_error = None
    if data and data.push_to_pysis:
        process = await session.get(PySisProcess, field.process_id)
        if process:
            pysis = get_pysis_service()
            if pysis.is_configured:
                try:
                    await pysis.update_process_field(
                        process.pysis_process_id,
                        field.pysis_field_name,
                        field.current_value,
                    )
                    field.needs_push = False
                    field.last_pushed_at = datetime.now(timezone.utc)
                    await session.commit()
                except Exception as e:
                    # Log error but don't fail - the AI suggestion was still accepted
                    push_error = str(e)
            else:
                push_error = "PySis API nicht konfiguriert"

    message = "KI-Vorschlag übernommen"
    if push_error:
        message += f" (Push fehlgeschlagen: {push_error})"

    return AcceptAISuggestionResult(
        success=True,
        field_id=field_id,
        accepted_value=field.current_value,
        message=message,
    )


@router.post("/fields/{field_id}/reject-ai", response_model=AcceptAISuggestionResult)
async def reject_ai_suggestion(
    field_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """
    Reject the AI-generated suggestion for a field.

    This will:
    1. Create a history entry marking the rejection
    2. Clear the ai_extracted_value
    """
    field = await session.get(PySisProcessField, field_id)
    if not field:
        raise NotFoundError("Field", str(field_id))

    if not field.ai_extracted_value:
        return AcceptAISuggestionResult(
            success=False,
            field_id=field_id,
            accepted_value=None,
            message="Kein KI-Vorschlag vorhanden",
        )

    # Create history entry for the rejection
    history = PySisFieldHistory(
        field_id=field.id,
        value=field.ai_extracted_value,
        source=ValueSource.AI,
        confidence_score=field.confidence_score,
        action="rejected",
    )
    session.add(history)

    # Clear the AI value
    rejected_value = field.ai_extracted_value
    field.ai_extracted_value = None
    field.confidence_score = None

    await session.commit()

    return AcceptAISuggestionResult(
        success=True,
        field_id=field_id,
        accepted_value=rejected_value,
        message="KI-Vorschlag abgelehnt",
    )


# === Field History ===

@router.get("/fields/{field_id}/history", response_model=PySisFieldHistoryListResponse)
async def get_field_history(
    field_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Get the value history for a field."""
    field = await session.get(PySisProcessField, field_id)
    if not field:
        raise NotFoundError("Field", str(field_id))

    result = await session.execute(
        select(PySisFieldHistory)
        .where(PySisFieldHistory.field_id == field_id)
        .order_by(PySisFieldHistory.created_at.desc())
        .limit(limit)
    )
    history_entries = result.scalars().all()

    return PySisFieldHistoryListResponse(
        items=[PySisFieldHistoryResponse.model_validate(h) for h in history_entries],
        total=len(history_entries),
    )


@router.post("/fields/{field_id}/restore/{history_id}", response_model=AcceptAISuggestionResult)
async def restore_from_history(
    field_id: UUID,
    history_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Restore a field value from history."""
    field = await session.get(PySisProcessField, field_id)
    if not field:
        raise NotFoundError("Field", str(field_id))

    history_entry = await session.get(PySisFieldHistory, history_id)
    if not history_entry or history_entry.field_id != field_id:
        raise NotFoundError("History entry", str(history_id))

    # Create history entry for current value before restore
    if field.current_value:
        old_history = PySisFieldHistory(
            field_id=field.id,
            value=field.current_value,
            source=field.value_source,
            confidence_score=field.confidence_score,
            action="replaced",
        )
        session.add(old_history)

    # Restore the value
    field.current_value = history_entry.value
    field.value_source = ValueSource.MANUAL  # Restored values are treated as manual
    field.needs_push = True

    # Create history entry for the restore action
    restore_history = PySisFieldHistory(
        field_id=field.id,
        value=history_entry.value,
        source=ValueSource.MANUAL,
        confidence_score=None,
        action="restored",
    )
    session.add(restore_history)

    await session.commit()

    return AcceptAISuggestionResult(
        success=True,
        field_id=field_id,
        accepted_value=field.current_value,
        message="Wert aus Verlauf wiederhergestellt",
    )


# === Test Connection ===

@router.get("/test-connection", response_model=PySisTestConnectionResult)
async def test_pysis_connection(
    process_id: Optional[str] = Query(default=None, description="Optional process ID to test"),
    _: User = Depends(require_editor),
):
    """Test the PySis API connection."""
    pysis = get_pysis_service()
    result = await pysis.test_connection(process_id)

    return PySisTestConnectionResult(**result)


# === List Available Processes from PySis ===

@router.get("/available-processes")
async def list_available_processes(
    _: User = Depends(require_editor),
):
    """
    List all available processes from PySis API.

    Returns a list of processes that can be linked to locations.
    """
    pysis = get_pysis_service()
    if not pysis.is_configured:
        raise ValidationError("PySis API credentials not configured")

    try:
        processes = await pysis.list_processes()
        return {"items": processes, "total": len(processes)}
    except Exception as e:
        # Return empty list with error info if endpoint doesn't exist
        return {"items": [], "total": 0, "error": str(e)}


# === Analyze for Facets ===

@router.post("/processes/{process_id}/analyze-for-facets", response_model=PySisAnalyzeForFacetsResult)
async def analyze_pysis_for_facets_admin(
    process_id: UUID,
    data: Optional[PySisAnalyzeForFacetsRequest] = None,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """
    Analyze PySis fields and extract Facets for the linked Entity.

    This endpoint:
    1. Loads all field values from the PySis process
    2. Starts an AI task for analysis
    3. Creates FacetValues based on active FacetTypes with AI extraction enabled

    The process must have an entity_id linked.
    """
    process = await session.get(PySisProcess, process_id)
    if not process:
        raise NotFoundError("Process", str(process_id))

    if not process.entity_id:
        raise ValidationError("Prozess hat keine verknüpfte Entity. Bitte zuerst Entity verknüpfen.")

    # Count fields with values for response
    fields_with_values = [
        f for f in process.fields
        if f.current_value or f.pysis_value or f.ai_extracted_value
    ]

    if not fields_with_values and not (data and data.include_empty_fields):
        raise ValidationError("Keine Felder mit Werten gefunden.")

    # Use unified service for consistent behavior
    service = PySisFacetService(session)
    try:
        ai_task = await service.analyze_for_facets(
            entity_id=process.entity_id,
            process_id=process_id,
            include_empty=data.include_empty_fields if data else False,
            min_confidence=data.min_field_confidence if data else 0.0,
        )
    except ValueError as e:
        raise ValidationError(str(e))

    return PySisAnalyzeForFacetsResult(
        success=True,
        task_id=ai_task.id,
        message=f"Analyse gestartet für {len(fields_with_values)} Felder",
        fields_analyzed=len(fields_with_values),
    )
