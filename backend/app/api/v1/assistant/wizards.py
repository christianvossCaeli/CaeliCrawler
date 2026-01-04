"""Conversational Wizard API endpoints for the AI Chat Assistant."""

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user_optional
from app.database import get_session
from app.models.user import User

router = APIRouter(prefix="/wizards", tags=["assistant-wizards"])


@router.get("")
async def get_available_wizards(
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict:
    """
    Get list of available wizard types.

    Returns all wizard definitions that can be started.
    Each wizard provides a guided, step-by-step workflow.
    """
    from services.wizard_service import WizardService

    wizard_service = WizardService(session)
    wizards = await wizard_service.get_available_wizards()
    return {"wizards": wizards}


@router.post("/start")
async def start_wizard(
    wizard_type: str = Query(..., description="Type of wizard to start"),
    context: dict | None = Body(None, description="Optional context to pre-fill wizard values"),
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict:
    """
    Start a new wizard session.

    ## Wizard Types
    - `create_entity`: Create a new entity with guided input
    - `add_pain_point`: Add a pain point to an entity
    - `quick_search`: Search with advanced filters

    ## Context
    Optional context can pre-fill wizard values:
    - `current_entity_id`: Pre-select entity for entity-related wizards
    - `current_entity_type`: Pre-select entity type

    Returns the first step of the wizard.
    """
    from services.wizard_service import WizardService

    wizard_service = WizardService(session)
    try:
        response = await wizard_service.start_wizard(wizard_type, context)
        return response.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post("/{wizard_id}/respond")
async def wizard_respond(
    wizard_id: str,
    response: dict,
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict:
    """
    Submit a response for the current wizard step.

    The response dict should contain:
    - `value`: The user's response to the current step

    Returns the next step or completion result.
    """
    from services.wizard_service import WizardService

    wizard_service = WizardService(session)
    try:
        wizard_response, result = await wizard_service.process_wizard_response(wizard_id, response.get("value"))
        return {
            "wizard_response": wizard_response.model_dump(),
            "result": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post("/{wizard_id}/back")
async def wizard_back(
    wizard_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict:
    """
    Go back to the previous wizard step.

    Only available if not on the first step.
    """
    from services.wizard_service import WizardService

    wizard_service = WizardService(session)
    try:
        response = await wizard_service.go_back(wizard_id)
        return response.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post("/{wizard_id}/cancel")
async def wizard_cancel(
    wizard_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict:
    """
    Cancel an active wizard session.

    The wizard state will be discarded.
    """
    from services.wizard_service import WizardService

    wizard_service = WizardService(session)
    await wizard_service.cancel_wizard(wizard_id)
    return {"success": True, "message": "Wizard abgebrochen"}
