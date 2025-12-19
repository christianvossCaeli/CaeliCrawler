"""Schema generation for Smart Query - EntityType schemas, AI prompts, and URL patterns."""

from typing import Any, Dict, List, Tuple


def generate_entity_type_schema(search_focus: str, user_intent: str) -> Dict[str, Any]:
    """Generate attribute_schema for a new EntityType based on search focus."""
    schemas = {
        "event_attendance": {
            "type": "object",
            "properties": {
                "event_name": {"type": "string", "description": "Name der Veranstaltung"},
                "event_date": {"type": "string", "format": "date", "description": "Datum"},
                "event_end_date": {"type": "string", "format": "date", "description": "Enddatum"},
                "event_location": {"type": "string", "description": "Veranstaltungsort"},
                "event_type": {"type": "string", "description": "Art (Konferenz, Messe, etc.)"},
                "attendees_summary": {"type": "string", "description": "Zusammenfassung der Teilnehmer"},
            },
            "required": ["event_name"],
        },
        "pain_points": {
            "type": "object",
            "properties": {
                "issue_type": {"type": "string", "description": "Art des Problems"},
                "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                "description": {"type": "string", "description": "Beschreibung"},
                "affected_area": {"type": "string", "description": "Betroffener Bereich"},
            },
            "required": ["description"],
        },
        "contacts": {
            "type": "object",
            "properties": {
                "contact_name": {"type": "string", "description": "Name"},
                "role": {"type": "string", "description": "Position/Rolle"},
                "organization": {"type": "string", "description": "Organisation"},
                "email": {"type": "string", "format": "email"},
                "phone": {"type": "string"},
            },
            "required": ["contact_name"],
        },
        "general": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Titel"},
                "description": {"type": "string", "description": "Beschreibung"},
                "category": {"type": "string", "description": "Kategorie"},
            },
        },
    }
    return schemas.get(search_focus, schemas["general"])


def generate_ai_extraction_prompt(
    user_intent: str,
    search_focus: str,
    target_entity_type_name: str,
) -> str:
    """Generate an AI extraction prompt based on user intent and search focus."""

    focus_prompts = {
        "event_attendance": f"""Extrahiere aus diesem Dokument alle Informationen über Events und Veranstaltungen.

## Zu extrahieren:
1. **Event-Details:**
   - Name der Veranstaltung
   - Datum und Uhrzeit
   - Ort/Location
   - Art (Konferenz, Messe, Tagung, Workshop, etc.)

2. **Teilnehmer:**
   - Personenname und vollständiger Titel
   - Position/Rolle (Bürgermeister, Landrat, Dezernent, etc.)
   - Organisation/Gemeinde die die Person vertritt
   - Rolle auf dem Event (Redner, Teilnehmer, Aussteller, Organisator)

## Fokus: {user_intent}

## Output:
Erstelle für jedes gefundene Event eine Entity vom Typ "{target_entity_type_name}".
Verknüpfe die Teilnehmer als Relations (attends) mit ihren Personen-Entities.

Gib das Ergebnis als strukturiertes JSON zurück mit:
- events: [{{event_name, event_date, event_location, event_type, attendees: [{{name, position, organization, role}}]}}]
- is_future_event: boolean (basierend auf event_date)""",

        "pain_points": f"""Extrahiere aus diesem Dokument alle Pain Points, Probleme und Herausforderungen.

## Zu extrahieren:
1. **Probleme/Herausforderungen:**
   - Beschreibung des Problems
   - Betroffener Bereich (Personal, IT, Finanzen, etc.)
   - Schweregrad (hoch/mittel/niedrig)
   - Relevante Zitate

2. **Kontext:**
   - Welche Gemeinde/Organisation ist betroffen?
   - Zeitlicher Rahmen
   - Geplante Maßnahmen

## Fokus: {user_intent}

## Output:
Erstelle für jedes Problem eine Entity vom Typ "{target_entity_type_name}".
Bewerte jeden Pain Point nach Schweregrad.""",

        "contacts": f"""Extrahiere aus diesem Dokument alle relevanten Kontaktpersonen und Entscheider.

## Zu extrahieren:
1. **Kontaktdaten:**
   - Vollständiger Name und Titel
   - Position/Rolle
   - Organisation/Gemeinde
   - E-Mail und Telefon (falls vorhanden)

2. **Zusätzliche Infos:**
   - Zitate oder Aussagen der Person
   - Zuständigkeitsbereich
   - Sentiment (positiv/negativ/neutral)

## Fokus: {user_intent}

## Output:
Erstelle für jede Person eine Entity vom Typ "{target_entity_type_name}".""",

        "general": f"""Analysiere dieses Dokument im Hinblick auf:
{user_intent}

Extrahiere relevante Informationen strukturiert.

## Output:
Erstelle Entities vom Typ "{target_entity_type_name}" für alle relevanten Funde.""",
    }

    return focus_prompts.get(search_focus, focus_prompts["general"])


def generate_url_patterns(search_focus: str, user_intent: str) -> Tuple[List[str], List[str]]:
    """
    Generate URL exclude patterns based on search focus.

    WICHTIG: Keine Include-Patterns mehr! Die KI-gestützte Inhaltsanalyse
    filtert relevante Dokumente - der Crawler soll ALLE Seiten besuchen.

    Returns:
        Tuple of (include_patterns=[], exclude_patterns)
    """
    # Common exclude patterns (always exclude these)
    common_exclude = [
        r"/impressum",
        r"/datenschutz",
        r"/privacy",
        r"/kontakt$",
        r"/contact$",
        r"/login",
        r"/logout",
        r"/register",
        r"/admin/",
        r"/api/",
        r"/wp-admin/",
        r"/wp-login",
        r"/sitemap",
        r"\.xml$",
        r"\.json$",
        r"/feed/",
        r"/rss",
        r"/print/",
        r"/drucken/",
        r"/suche\?",
        r"/search\?",
        r"\?page=",
        r"\?sort=",
        r"\?filter=",
        r"/cdn/",
        r"/static/",
        r"/assets/",
        r"/warenkorb",
        r"/cart",
        r"/checkout",
    ]

    # Focus-specific additional excludes
    focus_excludes = {
        "event_attendance": common_exclude + [
            r"/archiv/\d{4}/\d{2}/",  # Alte Monatsarchive
            r"/stellenangebot",
            r"/karriere",
            r"/job",
        ],
        "pain_points": common_exclude,
        "contacts": common_exclude,
        "general": common_exclude,
    }

    exclude_patterns = focus_excludes.get(search_focus, common_exclude)

    # KEINE Include-Patterns mehr - der Crawler besucht alle Seiten
    # Die KI-Inhaltsanalyse filtert relevante Dokumente
    return [], exclude_patterns
