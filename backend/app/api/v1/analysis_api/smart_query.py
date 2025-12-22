"""Smart Query endpoints - AI-powered natural language queries and commands."""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.user import User
from app.core.deps import get_current_user_optional, get_current_user, require_editor
from .helpers import build_preview

router = APIRouter()


class SmartQueryRequest(BaseModel):
    """Request for smart query endpoint."""
    question: str = Field(..., min_length=3, max_length=2000, description="Natural language question or command")
    allow_write: bool = Field(default=False, description="Allow write operations (create entities, facets, relations)")


class SmartWriteRequest(BaseModel):
    """Request for smart write endpoint with preview support."""
    question: str = Field(..., min_length=3, max_length=2000, description="Natural language command")
    preview_only: bool = Field(default=True, description="If true, only return preview without executing")
    confirmed: bool = Field(default=False, description="If true and preview_only=false, execute the command")


@router.post("/smart-query")
async def smart_query_endpoint(
    request: SmartQueryRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Execute a natural language query or command against the Entity-Facet system.

    ## Read Examples:
    - "Zeige mir auf welche künftige Events wichtige Entscheider-Personen von Gemeinden gehen"
    - "Welche Bürgermeister sprechen auf Windenergie-Konferenzen in den nächsten 3 Monaten?"
    - "Zeige mir alle Pain Points von Gemeinden in NRW"

    ## Write Examples (requires allow_write=True):
    - "Erstelle eine neue Person Max Müller, Bürgermeister"
    - "Füge einen Pain Point für Gummersbach hinzu: Bürgerbeschwerden wegen Lärmbelästigung"
    - "Verknüpfe Max Müller mit Gummersbach als Arbeitgeber"

    The AI interprets the question/command and executes the appropriate action.
    """
    from services.smart_query import smart_query

    result = await smart_query(session, request.question, allow_write=request.allow_write)
    return result


@router.post("/smart-write")
async def smart_write_endpoint(
    request: SmartWriteRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Execute a write command in natural language with preview support.

    **Workflow:**
    1. Send command with preview_only=True (default) → Get preview of what will be created
    2. Review the preview
    3. Send same command with preview_only=False, confirmed=True → Execute the command

    This endpoint is for:
    - Creating new entities (persons, municipalities, organizations, events)
    - Adding facets (pain points, positive signals, contacts)
    - Creating relations between entities
    - Creating category setups with automatic data source linking
    - Starting crawls for specific data sources

    Examples:
    - "Erstelle eine Person Hans Schmidt, Landrat von Oberberg"
    - "Füge einen Pain Point für Münster hinzu: Personalmangel in der IT-Abteilung"
    - "Neue Organisation: Caeli Wind GmbH, Windenergie-Entwickler"
    - "Verknüpfe Hans Schmidt mit Oberbergischer Kreis"
    - "Finde alle Events auf denen Entscheider aus NRW teilnehmen"
    - "Starte Crawls für alle Gummersbach Datenquellen"
    """
    from services.smart_query import interpret_write_command, execute_write_command

    # First, interpret the command (now uses dynamic prompt with DB data)
    command = await interpret_write_command(request.question, session)

    if not command or command.get("operation", "none") == "none":
        return {
            "success": False,
            "mode": "preview" if request.preview_only else "write",
            "message": "Keine Schreib-Operation erkannt. Bitte formulieren Sie das Kommando anders.",
            "interpretation": command,
            "original_question": request.question,
        }

    # Preview mode - just return the interpretation
    if request.preview_only:
        return {
            "success": True,
            "mode": "preview",
            "message": "Vorschau der geplanten Aktion",
            "interpretation": command,
            "preview": build_preview(command),
            "original_question": request.question,
        }

    # Execute mode - require confirmation
    if not request.confirmed:
        return {
            "success": False,
            "mode": "write",
            "message": "Bestätigung erforderlich. Setzen Sie confirmed=true um fortzufahren.",
            "interpretation": command,
            "preview": build_preview(command),
            "original_question": request.question,
        }

    # Execute the command with current user context
    result = await execute_write_command(
        session, command, current_user.id, original_question=request.question
    )
    result["original_question"] = request.question
    result["mode"] = "write"
    result["interpretation"] = command

    return result


@router.get("/smart-query/examples")
async def get_smart_query_examples():
    """Get example queries for the smart query endpoint."""
    return {
        "read_examples": [
            {
                "question": "Zeige mir auf welche künftige Events wichtige Entscheider-Personen von Gemeinden gehen",
                "description": "Findet alle Personen mit Positionen wie Bürgermeister, Landrat etc. und deren zukünftige Event-Teilnahmen",
            },
            {
                "question": "Welche Bürgermeister sprechen auf Windenergie-Konferenzen?",
                "description": "Filtert nach Position 'Bürgermeister' und Event-Attendance Facets",
            },
            {
                "question": "Wo kann ich Entscheider aus Bayern in den nächsten 90 Tagen treffen?",
                "description": "Kombiniert Regions-Filter mit zukünftigen Events",
            },
            {
                "question": "Zeige mir alle Pain Points von Gemeinden",
                "description": "Listet alle Pain Point Facets gruppiert nach Gemeinde",
            },
        ],
        "write_examples": [
            {
                "question": "Erstelle eine neue Person Max Müller, Bürgermeister von Gummersbach",
                "description": "Erstellt eine Person-Entity mit Position 'Bürgermeister'",
            },
            {
                "question": "Füge einen Pain Point für Münster hinzu: Personalmangel in der IT",
                "description": "Erstellt einen Pain Point Facet für die Gemeinde Münster",
            },
            {
                "question": "Neue Organisation: Caeli Wind GmbH, Windenergie-Entwickler",
                "description": "Erstellt eine neue Organisation-Entity",
            },
            {
                "question": "Verknüpfe Max Müller mit Gummersbach als Arbeitgeber",
                "description": "Erstellt eine 'works_for' Relation zwischen Person und Gemeinde",
            },
        ],
        "supported_filters": {
            "time": ["künftig", "vergangen", "zukünftig", "in den nächsten X Tagen/Monaten"],
            "positions": ["Bürgermeister", "Landrat", "Dezernent", "Entscheider", "Amtsleiter"],
            "entity_types": ["Person", "Gemeinde", "Event", "Organisation"],
            "facet_types": ["Pain Points", "Positive Signale", "Event-Teilnahmen", "Kontakte"],
        },
        "write_operations": {
            "create_entity": ["Erstelle", "Neue/r/s", "Anlegen"],
            "create_facet": ["Füge hinzu", "Neuer Pain Point", "Neues Positive Signal"],
            "create_relation": ["Verknüpfe", "Verbinde", "arbeitet für", "ist Mitglied von"],
        },
    }
