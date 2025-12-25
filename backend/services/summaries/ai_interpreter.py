"""AI Interpreter for Custom Summaries.

Interprets natural language prompts into widget configurations
for user-defined dashboard summaries.
"""

import json
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from services.smart_query.query_interpreter import (
    get_openai_client,
    load_facet_and_entity_types,
    sanitize_user_input,
)
from services.smart_query.utils import clean_json_response

logger = structlog.get_logger(__name__)


def _build_summary_interpreter_prompt(
    entity_types: List[Dict[str, Any]],
    facet_types: List[Dict[str, Any]],
    prompt: str,
) -> str:
    """Build the prompt for interpreting a summary request.

    Args:
        entity_types: Available entity types from database
        facet_types: Available facet types from database
        prompt: User's natural language prompt

    Returns:
        Complete prompt for AI interpretation
    """
    # Build entity types section with attribute info
    entity_lines = []
    for et in entity_types:
        desc = et.get("description") or et["name"]
        # Include attribute schema hints if available
        attrs = et.get("attribute_schema", {})
        attr_info = ""
        if attrs and isinstance(attrs, dict):
            props = attrs.get("properties", {})
            if props:
                attr_names = list(props.keys())[:5]
                attr_info = f" [core_attributes: {', '.join(attr_names)}]"
        entity_lines.append(f"- {et['slug']}: {desc}{attr_info}")
    entity_section = "\n".join(entity_lines) if entity_lines else "- (keine Entity-Typen)"

    # Build facet types section
    facet_lines = []
    for ft in facet_types:
        desc = ft.get("description") or ft["name"]
        time_note = " [zeitbasiert]" if ft.get("is_time_based") else ""
        facet_lines.append(f"- {ft['slug']}: {desc}{time_note}")
    facet_section = "\n".join(facet_lines) if facet_lines else "- (keine Facet-Typen)"

    return f"""Du bist ein Dashboard-Designer der aus natürlichsprachigen Beschreibungen
Widget-Konfigurationen für Dashboards erstellt.

## Verfügbare Entity-Typen:
{entity_section}

## Verfügbare Facet-Typen:
{facet_section}

## WICHTIG - Datenstruktur:
Jede Entity hat diese Felder direkt verfügbar:
- name: Entity-Name
- entity_id: Eindeutige ID
- admin_level_1: Bundesland/Region
- country: Land
- latitude, longitude: Koordinaten (wenn vorhanden oder vom Parent geerbt)
- Alle Felder aus core_attributes sind DIREKT verfügbar (z.B. status, power_mw, area_ha)
- facets: Nur für Facet-Daten (facets.FACET_SLUG.value)

## Widget-Typen:
- table: Tabellen für Listen und Ranglisten (Standard für viele Daten)
- bar_chart: Balkendiagramm für Kategorievergleiche (2-20 Kategorien)
- line_chart: Liniendiagramm für Zeitverläufe
- pie_chart: Kreisdiagramm für Anteile (max 8 Kategorien)
- stat_card: Einzelwert-Karte für KPIs und Zahlen
- comparison: Vergleich von 2-3 Entities
- timeline: Zeitlicher Verlauf von Ereignissen
- map: Geografische Karte (wenn Standortdaten vorhanden)
  NUTZE map WENN: Standorte, Orte, "wo", "where", "location", "karte"
  Koordinaten sind DIREKT als latitude/longitude verfügbar!
- calendar: Kalenderansicht für Events, Termine, Sitzungen
  NUTZE calendar WENN: Events, Termine, "wann", "when", "kommende", "upcoming"

## Grid-Layout:
- 4 Spalten verfügbar
- Widgets haben x, y, w(idth), h(eight)
- Sinnvolle Größen: stat_card (1x1), table (4x3), bar_chart (2x2), line_chart (3x2), calendar (4x4), map (3x3)

## Aufgabe:
Analysiere den User-Prompt und erstelle eine vollständige Dashboard-Konfiguration.

## User-Prompt:
"{prompt}"

## Antwortformat (JSON):
{{
  "name": "Kurzer, prägnanter Dashboard-Name",
  "description": "Beschreibung des Dashboards",
  "theme": {{
    "primary_entity_type": "entity_type_slug",
    "context": "Kurze Kontextbeschreibung",
    "focus_areas": ["fokus1", "fokus2"]
  }},
  "widgets": [
    {{
      "widget_type": "table|bar_chart|line_chart|pie_chart|stat_card|comparison|timeline|map|calendar",
      "title": "Widget-Titel",
      "subtitle": "Optional: Untertitel",
      "position": {{ "x": 0, "y": 0, "w": 2, "h": 2 }},
      "query_config": {{
        "entity_type": "entity_type_slug",
        "facet_types": ["facet1", "facet2"],
        "filters": {{}},
        "sort_by": "feld_name",
        "sort_order": "desc|asc",
        "limit": 10,
        "aggregate": null,
        "group_by": null
      }},
      "visualization_config": {{
        // Für table - WICHTIG: Nutze "key" nicht "field"!
        "columns": [
          {{"key": "name", "label": "Name"}},
          {{"key": "status", "label": "Status"}},
          {{"key": "admin_level_1", "label": "Region"}},
          {{"key": "power_mw", "label": "Leistung (MW)", "type": "number"}}
        ],
        "show_pagination": true,
        "rows_per_page": 15,
        // Für Charts:
        "x_axis": {{"field": "name", "label": "X-Achse"}},
        "y_axis": {{"field": "value_field", "label": "Y-Achse"}},
        "color": "#1976d2",
        "horizontal": false,
        "show_legend": true,
        // Für calendar:
        "active_view": "month",
        "date_field": "facets.datum.value",
        "title_field": "name",
        // Für map - Koordinaten sind DIREKT verfügbar:
        "lat_field": "latitude",
        "lng_field": "longitude",
        "name_field": "name",
        "popup_fields": ["name", "status", "admin_level_1"]
      }},
      "reasoning": "Warum dieses Widget für diese Anforderung"
    }}
  ],
  "suggested_schedule": {{
    "type": "manual|daily|weekly|on_crawl",
    "cron": "0 8 * * *",
    "reason": "Warum dieses Update-Intervall"
  }},
  "auto_expand_suggestion": {{
    "enabled": false,
    "reason": "Ob neue relevante Daten automatisch hinzugefügt werden sollen"
  }},
  "overall_reasoning": "Zusammenfassung der Design-Entscheidungen"
}}

## Wichtige Regeln:
1. Nutze NUR Entity-Typen und Facet-Typen aus der obigen Liste
2. Für table columns: Nutze "key" (nicht "field"!) für Spaltenkonfiguration
3. Für map: lat_field="latitude", lng_field="longitude" (NICHT facets.xxx!)
4. Core-Attribute wie status, power_mw sind DIREKT verfügbar (nicht in facets!)
5. Bei Ranglisten → table Widget mit sortierter Liste
6. Bei Einzelwerten ("Wie viele...") → stat_card
7. Bei Standorten/Karte → map Widget
8. Ordne Widgets logisch an (wichtigstes oben links)
9. Maximal 6 Widgets pro Dashboard

Antworte NUR mit validem JSON."""


async def interpret_summary_prompt(
    prompt: str,
    session: AsyncSession,
    user_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Interpret a natural language prompt into a summary configuration.

    Uses AI to analyze the prompt and generate:
    - Dashboard name and description
    - Widget configurations with queries
    - Suggested layout
    - Scheduling recommendations

    Args:
        prompt: Natural language description of desired dashboard
        session: Database session for loading available types
        user_name: Optional user name for personalization

    Returns:
        Dict with interpreted configuration:
        - name: Suggested dashboard name
        - description: Dashboard description
        - theme: Theme/context information
        - widgets: List of widget configurations
        - suggested_schedule: Scheduling recommendation
        - auto_expand_suggestion: Auto-expand recommendation
        - overall_reasoning: AI's reasoning

    Raises:
        ValueError: If prompt is invalid or AI not configured
        RuntimeError: If interpretation fails
    """
    logger.info(
        "ai_interpretation_started",
        prompt_preview=prompt[:100] if prompt else "",
        user_name=user_name,
    )

    # Sanitize input
    sanitized_prompt = sanitize_user_input(prompt, max_length=2000)
    if not sanitized_prompt or len(sanitized_prompt) < 10:
        raise ValueError("Prompt ist zu kurz oder ungültig")

    # Load available types from database
    facet_types, entity_types = await load_facet_and_entity_types(session)

    if not entity_types:
        logger.warning("No entity types available for summary interpretation")
        raise ValueError("Keine Entity-Typen im System vorhanden")

    # Build prompt
    ai_prompt = _build_summary_interpreter_prompt(
        entity_types=entity_types,
        facet_types=facet_types,
        prompt=sanitized_prompt,
    )

    logger.debug(
        "Interpreting summary prompt",
        prompt_length=len(sanitized_prompt),
        entity_types_count=len(entity_types),
        facet_types_count=len(facet_types),
    )

    try:
        client = get_openai_client()

        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[
                {
                    "role": "system",
                    "content": "Du bist ein intelligenter Dashboard-Designer. Erstelle präzise Widget-Konfigurationen. Antworte nur mit JSON.",
                },
                {
                    "role": "user",
                    "content": ai_prompt,
                },
            ],
            temperature=settings.ai_summary_temperature,
            max_tokens=settings.ai_summary_max_tokens,
            timeout=60,  # 60 second timeout
        )

        # Validate response structure
        if not response.choices:
            raise RuntimeError("AI response contains no choices")

        message = response.choices[0].message
        if not message or not message.content:
            raise RuntimeError("AI response message is empty")

        content = message.content.strip()
        logger.debug("AI raw response", content=content[:300] if content else "empty")

        # Clean and parse JSON
        content = clean_json_response(content)
        parsed = json.loads(content)

        # Validate required fields
        if "name" not in parsed or "widgets" not in parsed:
            raise ValueError("KI-Antwort fehlen erforderliche Felder (name, widgets)")

        if not parsed.get("widgets"):
            raise ValueError("Keine Widgets in der KI-Antwort generiert")

        # Post-process widgets: validate positions and ensure unique IDs
        widgets = parsed.get("widgets", [])
        processed_widgets = _process_widgets(widgets, entity_types, facet_types)
        parsed["widgets"] = processed_widgets

        logger.info(
            "Summary prompt interpreted successfully",
            name=parsed.get("name"),
            widget_count=len(processed_widgets),
            schedule_type=parsed.get("suggested_schedule", {}).get("type"),
        )

        return parsed

    except json.JSONDecodeError as e:
        logger.error("Failed to parse AI response as JSON", error=str(e))
        raise RuntimeError(f"KI-Antwort konnte nicht geparst werden: {str(e)}")
    except ValueError:
        raise
    except Exception as e:
        logger.error("Summary interpretation failed", error=str(e), exc_info=True)
        raise RuntimeError(f"Dashboard-Interpretation fehlgeschlagen: {str(e)}")


def _process_widgets(
    widgets: List[Dict[str, Any]],
    entity_types: List[Dict[str, Any]],
    facet_types: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Process and validate widget configurations.

    - Validates entity_type and facet_types references
    - Ensures valid grid positions
    - Adds default values where missing

    Args:
        widgets: Raw widget configurations from AI
        entity_types: Available entity types
        facet_types: Available facet types

    Returns:
        Processed widget configurations
    """
    valid_entity_slugs = {et["slug"] for et in entity_types}
    valid_facet_slugs = {ft["slug"] for ft in facet_types}

    processed = []
    y_cursor = 0  # Track vertical position for auto-layout

    for i, widget in enumerate(widgets):
        # Validate widget type
        valid_types = [
            "table", "bar_chart", "line_chart", "pie_chart",
            "stat_card", "text", "comparison", "timeline", "map", "calendar"
        ]
        widget_type = widget.get("widget_type", "table")
        if widget_type not in valid_types:
            widget_type = "table"

        # Validate and fix position
        position = widget.get("position", {})
        x = max(0, min(3, int(position.get("x", 0))))
        w = max(1, min(4, int(position.get("w", 2))))
        h = max(1, min(6, int(position.get("h", 2))))

        # Auto-calculate y if not valid
        y = position.get("y")
        if y is None or not isinstance(y, (int, float)):
            y = y_cursor
        y = max(0, int(y))

        # Update cursor for next widget
        if x + w > 4:  # Would overflow, move to next row
            x = 0
            y = y_cursor
        y_cursor = max(y_cursor, y + h)

        # Validate query_config
        query_config = widget.get("query_config", {})

        # Validate entity_type reference
        entity_type = query_config.get("entity_type")
        if entity_type and entity_type not in valid_entity_slugs:
            logger.warning(
                "Unknown entity_type in widget, using first available",
                unknown=entity_type,
            )
            entity_type = list(valid_entity_slugs)[0] if valid_entity_slugs else None
        query_config["entity_type"] = entity_type

        # Validate facet_types references
        requested_facets = query_config.get("facet_types", [])
        valid_facets = [f for f in requested_facets if f in valid_facet_slugs]
        if len(valid_facets) != len(requested_facets):
            logger.warning(
                "Some facet_types not found",
                requested=requested_facets,
                valid=valid_facets,
            )
        query_config["facet_types"] = valid_facets

        # Ensure reasonable defaults
        if "limit" not in query_config:
            query_config["limit"] = 100 if widget_type == "table" else 20
        if "sort_order" not in query_config:
            query_config["sort_order"] = "desc"

        # Build processed widget
        processed_widget = {
            "widget_type": widget_type,
            "title": widget.get("title", f"Widget {i + 1}"),
            "subtitle": widget.get("subtitle"),
            "position": {
                "x": x,
                "y": y,
                "w": w,
                "h": h,
            },
            "query_config": query_config,
            "visualization_config": widget.get("visualization_config", {}),
            "display_order": i,
        }

        processed.append(processed_widget)

    return processed


async def suggest_widgets_for_entity_type(
    entity_type_slug: str,
    session: AsyncSession,
    focus: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Suggest default widgets for a given entity type.

    Quick helper to generate widget suggestions without full AI interpretation.

    Args:
        entity_type_slug: The entity type to create widgets for
        session: Database session
        focus: Optional focus area (e.g., "ranking", "timeline", "comparison")

    Returns:
        List of widget configurations
    """
    facet_types, entity_types = await load_facet_and_entity_types(session)

    # Find the entity type
    entity_type = next(
        (et for et in entity_types if et["slug"] == entity_type_slug),
        None
    )
    if not entity_type:
        logger.warning("Entity type not found", slug=entity_type_slug)
        return []

    # Find applicable facets
    applicable_facets = [
        ft for ft in facet_types
        if not ft.get("applicable_entity_type_slugs") or
        entity_type_slug in ft.get("applicable_entity_type_slugs", [])
    ]

    widgets = []

    # Add stat card for total count
    widgets.append({
        "widget_type": "stat_card",
        "title": f"Anzahl {entity_type.get('name', entity_type_slug)}",
        "position": {"x": 0, "y": 0, "w": 1, "h": 1},
        "query_config": {
            "entity_type": entity_type_slug,
            "aggregate": "count",
        },
        "visualization_config": {},
        "display_order": 0,
    })

    # Add table with main facets
    if applicable_facets:
        facet_slugs = [ft["slug"] for ft in applicable_facets[:5]]
        columns = [{"key": "name", "label": entity_type.get("name", "Name")}]
        columns.extend([
            {"key": f"facets.{slug}.value", "label": slug}
            for slug in facet_slugs
        ])

        widgets.append({
            "widget_type": "table",
            "title": f"{entity_type.get('name_plural', entity_type['name'])} Übersicht",
            "position": {"x": 1, "y": 0, "w": 3, "h": 3},
            "query_config": {
                "entity_type": entity_type_slug,
                "facet_types": facet_slugs,
                "limit": 50,
            },
            "visualization_config": {
                "columns": columns,
                "show_pagination": True,
                "rows_per_page": 10,
            },
            "display_order": 1,
        })

    # Add time-based chart if time-based facets exist
    time_facets = [ft for ft in applicable_facets if ft.get("is_time_based")]
    if time_facets and focus in ("timeline", None):
        widgets.append({
            "widget_type": "line_chart",
            "title": f"{time_facets[0]['name']} Verlauf",
            "position": {"x": 0, "y": 3, "w": 4, "h": 2},
            "query_config": {
                "entity_type": entity_type_slug,
                "facet_types": [time_facets[0]["slug"]],
            },
            "visualization_config": {
                "x_axis": {"field": "recorded_at", "label": "Zeit"},
                "y_axis": {"field": "value", "label": time_facets[0]["name"]},
                "show_legend": True,
            },
            "display_order": 2,
        })

    return widgets


def get_schedule_suggestion(
    theme: Optional[str] = None,
    entity_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Get schedule suggestion based on data characteristics.

    Args:
        theme: Optional theme/topic of the summary
        entity_type: Optional primary entity type

    Returns:
        Schedule suggestion with type, cron, and reason
    """
    # Default: manual updates
    suggestion = {
        "type": "manual",
        "cron": None,
        "reason": "Manuelle Aktualisierung empfohlen - keine automatischen Updates konfiguriert",
    }

    # Time-sensitive themes suggest more frequent updates
    time_sensitive_keywords = [
        "aktuell", "live", "heute", "news", "ticker", "ranking",
        "tabelle", "stand", "börse", "wetter"
    ]
    if theme and any(kw in theme.lower() for kw in time_sensitive_keywords):
        suggestion = {
            "type": "daily",
            "cron": "0 8 * * *",
            "reason": "Tägliche Aktualisierung empfohlen für zeitkritische Daten",
        }

    # Weekly themes
    weekly_keywords = ["woche", "weekly", "wöchentlich", "zusammenfassung"]
    if theme and any(kw in theme.lower() for kw in weekly_keywords):
        suggestion = {
            "type": "weekly",
            "cron": "0 9 * * 1",  # Monday 9:00
            "reason": "Wöchentliche Aktualisierung am Montag morgen",
        }

    return suggestion
