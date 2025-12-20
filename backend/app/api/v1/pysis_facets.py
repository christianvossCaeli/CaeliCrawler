"""
PySis-Facets API - Einheitliche Endpunkte für PySis-Facet-Operationen.

Bietet:
- Analyse von PySis-Feldern zur Facet-Erstellung
- Anreicherung bestehender Facets mit PySis-Daten
- Vorschau und Status-Abfragen
"""

from typing import Any, Dict, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.user import User
from app.core.deps import get_current_user, require_editor
from services.pysis_facet_service import PySisFacetService

router = APIRouter(tags=["PySis Facets"])


# Request/Response Schemas

class AnalyzeForFacetsRequest(BaseModel):
    """Request für PySis-Facet-Analyse."""
    entity_id: UUID = Field(..., description="Entity-ID")
    process_id: Optional[UUID] = Field(None, description="Spezifischer PySis-Prozess (optional)")
    include_empty: bool = Field(False, description="Auch leere Felder analysieren")
    min_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Minimale Konfidenz")


class EnrichFacetsRequest(BaseModel):
    """Request für Facet-Anreicherung."""
    entity_id: UUID = Field(..., description="Entity-ID")
    facet_type_id: Optional[UUID] = Field(None, description="Nur diesen FacetType anreichern")
    overwrite: bool = Field(False, description="Bestehende Werte überschreiben")


class OperationResponse(BaseModel):
    """Antwort für gestartete Operationen."""
    success: bool
    task_id: str
    message: str


class PreviewResponse(BaseModel):
    """Vorschau einer Operation."""
    can_execute: bool
    message: str
    operation: str
    entity_name: str
    pysis_processes: int = 0
    pysis_fields: int = 0
    fields_with_values: int = 0
    facet_types_count: Optional[int] = None
    facet_values_count: Optional[int] = None
    facet_types: Optional[list] = None
    facets_by_type: Optional[list] = None


class StatusResponse(BaseModel):
    """PySis-Status einer Entity."""
    has_pysis: bool
    entity_name: str
    message: Optional[str] = None
    processes: Optional[list] = None
    recent_tasks: Optional[list] = None
    total_processes: int = 0
    total_fields: int = 0


# Endpoints

@router.post("/analyze", response_model=OperationResponse)
async def analyze_pysis_for_facets(
    request: AnalyzeForFacetsRequest,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    """
    Analysiert PySis-Felder und erstellt Facets.

    Startet einen Hintergrund-Task der:
    1. PySis-Felder der Entity lädt
    2. Aktive FacetTypes mit AI-Extraktion identifiziert
    3. Mit KI relevante Informationen extrahiert
    4. Neue FacetValues erstellt
    """
    service = PySisFacetService(session)

    try:
        task = await service.analyze_for_facets(
            entity_id=request.entity_id,
            process_id=request.process_id,
            include_empty=request.include_empty,
            min_confidence=request.min_confidence,
        )
        return OperationResponse(
            success=True,
            task_id=str(task.id),
            message="PySis-Facet-Analyse gestartet",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/enrich", response_model=OperationResponse)
async def enrich_facets_from_pysis(
    request: EnrichFacetsRequest,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    """
    Reichert bestehende Facets mit PySis-Daten an.

    Startet einen Hintergrund-Task der:
    1. Bestehende FacetValues der Entity lädt
    2. PySis-Felder sammelt
    3. Mit KI fehlende Felder in FacetValues ergänzt
    4. FacetValues aktualisiert
    """
    service = PySisFacetService(session)

    try:
        task = await service.enrich_facets_from_pysis(
            entity_id=request.entity_id,
            facet_type_id=request.facet_type_id,
            overwrite=request.overwrite,
        )
        return OperationResponse(
            success=True,
            task_id=str(task.id),
            message="Facet-Anreicherung gestartet",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/preview", response_model=PreviewResponse)
async def get_operation_preview(
    entity_id: UUID = Query(..., description="Entity-ID"),
    operation: Literal["analyze", "enrich"] = Query(..., description="Operation: 'analyze' oder 'enrich'"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Zeigt Vorschau einer Operation.

    Gibt Informationen zurück über:
    - Anzahl PySis-Prozesse und -Felder
    - Anzahl betroffener Facets
    - Ob die Operation ausgeführt werden kann
    """
    service = PySisFacetService(session)

    try:
        preview = await service.get_operation_preview(entity_id, operation)
        return PreviewResponse(**preview)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status", response_model=StatusResponse)
async def get_pysis_status(
    entity_id: UUID = Query(..., description="Entity-ID"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Zeigt den PySis-Status einer Entity.

    Gibt Informationen zurück über:
    - Verknüpfte PySis-Prozesse
    - Felder und deren Werte
    - Letzte AI-Tasks
    """
    service = PySisFacetService(session)

    try:
        status = await service.get_pysis_status(entity_id)
        return StatusResponse(**status)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/summary")
async def get_entity_pysis_summary(
    entity_id: UUID = Query(..., description="Entity-ID"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Kurze Zusammenfassung für UI-Anzeige.

    Gibt zurück ob Entity PySis-Daten hat und Anzahl Prozesse/Felder.
    """
    service = PySisFacetService(session)

    summary = await service.get_entity_pysis_summary(entity_id)
    if summary:
        return summary
    return {"has_pysis": False}
