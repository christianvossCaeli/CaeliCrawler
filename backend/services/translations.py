"""Translations for the Assistant Service."""

from typing import Any

TRANSLATIONS: dict[str, dict[str, str]] = {
    "de": {
        # Query responses
        "no_results": "Keine Ergebnisse gefunden. Versuche eine andere Formulierung.",
        "found_one": "Ich habe {entity_link} gefunden.",
        "found_one_plain": "Ich habe '{name}' gefunden.",
        "found_many": "Ich habe {total} Ergebnisse gefunden, darunter: {links_text} und {remaining} weitere.",
        "found_many_no_remaining": "Ich habe {total} Ergebnisse gefunden: {links_text}",
        "found_count": "Ich habe {total} Ergebnisse gefunden.",
        # Suggested actions
        "show_details": "Details zeigen",
        "new_search": "Neue Suche",
        "pain_points": "Pain Points",
        "summary": "Zusammenfassung",
        "relations": "Relationen",
        # Context query
        "not_on_entity_page": "Du befindest dich aktuell nicht auf einer Entity-Detailseite.",
        "invalid_entity_id": "Ungueltige Entity-ID.",
        "entity_not_found": "Entity nicht gefunden.",
        "entries": "{count} Einträge",
        # Inline edit
        "no_entity_selected": "Keine Entity ausgewählt. Navigiere zuerst zu einer Entity-Detailseite.",
        "could_not_parse_value": "Ich konnte den neuen Wert nicht erkennen. Bitte formuliere um, z.B. 'Ändere den Namen zu Neuer Name'",
        "invalid_entity_id_navigate": "Ungueltige Entity-ID. Bitte navigiere zuerst zu einer Entity-Detailseite.",
        "confirm_change": "Soll ich '{field}' von '{from_value}' zu '{to_value}' ändern?",
        # Write mode
        "write_mode_required": "Für Änderungen bitte in den Schreib-Modus wechseln.",
        "complex_write_redirect": "Für diese komplexe Operation nutze bitte die Smart Query Seite. Ich leite dich weiter.",
        "smart_query_redirect": "Für die Erstellung nutze bitte die Smart Query Seite im Schreib-Modus.",
        # Navigation
        "where_to_navigate": "Wohin möchtest du navigieren? Nenne mir einen Entity-Namen.",
        "entity_not_found_name": "Keine Entity mit dem Namen '{name}' gefunden.",
        "navigate_to": "Navigiere zu {entity_link}",
        # Summary
        "app_overview": "**App-Übersicht:**\n- {entity_count} Entities\n- {facet_count} Facet-Werte",
        "summary_title": "**Zusammenfassung: {name}**\n\n",
        "type_label": "Typ: {type}\n\n",
        "facets_label": "**Facets:**\n",
        "relations_label": "\n**Relationen:** {count}",
        "unknown_type": "Unbekannt",
        # Help
        "help_intro": "**Hallo! Ich bin dein Assistent für CaeliCrawler.**\n\n",
        "help_capabilities": "Ich kann dir helfen mit:\n",
        "help_search": "- **Suchen**: 'Zeige mir Pain Points von Gemeinden'\n",
        "help_navigation": "- **Navigation**: 'Geh zu Gummersbach'\n",
        "help_summaries": "- **Zusammenfassungen**: 'Fasse diese Entity zusammen'\n",
        "help_changes": "- **Änderungen**: 'Ändere den Namen zu XY' (im Schreib-Modus)\n\n",
        "help_current_entity": "**Du bist gerade bei:** {name}\n",
        "help_context_hint": "Frag mich z.B. 'Was sind die Pain Points hier?' oder 'Zeig mir die Relationen'\n\n",
        "help_slash_commands": "**Slash Commands:**\n",
        # Slash commands
        "search_missing_term": "Bitte gib einen Suchbegriff an: /search <suchbegriff>",
        "unknown_command": "Unbekannter Befehl: /{command}. Nutze /help für verfügbare Befehle.",
        # Errors
        "error_occurred": "Ein Fehler ist aufgetreten: {error}",
        "unknown_intent": "Ich konnte deine Anfrage nicht verstehen. Versuche es anders zu formulieren.",
        "query_error": "Fehler bei der Suche: {error}",
        "error_generic": "Fehler: {error}",
        # Action execution
        "entity_updated": "'{name}' wurde aktualisiert.",
        "unknown_action": "Unbekannte Aktion: {action}",
        # Follow-up suggestions
        "show_more_details": "Zeig mir mehr Details zu einem Ergebnis",
        "filter_by_criteria": "Filtere nach einem bestimmten Kriterium",
        "show_pain_points": "Zeige Pain Points von {name}",
        "show_relations": "Relationen von {name}",
        "show_all_municipalities": "Zeige alle Municipalities",
        "show_pain_points_generic": "Zeige Pain Points",
        # Streaming status
        "streaming_processing": "Verarbeite Anfrage...",
        "streaming_searching": "Suche läuft...",
        "streaming_analyzing": "Analysiere Ergebnisse...",
        "streaming_generating": "Generiere Antwort...",
        "streaming_complete": "Fertig",
        # Batch operations
        "batch_missing_filter": "Bitte gib an, welche Entities bearbeitet werden sollen (z.B. 'alle Gemeinden in NRW').",
        "batch_no_matches": "Keine passenden Entities für die Batch-Operation gefunden.",
        "batch_preview_message": "{count} Entities würden bearbeitet werden.",
    },
    "en": {
        # Query responses
        "no_results": "No results found. Try a different query.",
        "found_one": "I found {entity_link}.",
        "found_one_plain": "I found '{name}'.",
        "found_many": "I found {total} results, including: {links_text} and {remaining} more.",
        "found_many_no_remaining": "I found {total} results: {links_text}",
        "found_count": "I found {total} results.",
        # Suggested actions
        "show_details": "Show details",
        "new_search": "New search",
        "pain_points": "Pain Points",
        "summary": "Summary",
        "relations": "Relations",
        # Context query
        "not_on_entity_page": "You are not currently on an entity detail page.",
        "invalid_entity_id": "Invalid entity ID.",
        "entity_not_found": "Entity not found.",
        "entries": "{count} entries",
        # Inline edit
        "no_entity_selected": "No entity selected. Please navigate to an entity detail page first.",
        "could_not_parse_value": "I couldn't parse the new value. Please rephrase, e.g. 'Change the name to New Name'",
        "invalid_entity_id_navigate": "Invalid entity ID. Please navigate to an entity detail page first.",
        "confirm_change": "Should I change '{field}' from '{from_value}' to '{to_value}'?",
        # Write mode
        "write_mode_required": "Please switch to write mode for changes.",
        "complex_write_redirect": "For this complex operation, please use the Smart Query page. I'll redirect you.",
        "smart_query_redirect": "Please use the Smart Query page in write mode for creation.",
        # Navigation
        "where_to_navigate": "Where would you like to navigate? Tell me an entity name.",
        "entity_not_found_name": "No entity found with the name '{name}'.",
        "navigate_to": "Navigating to {entity_link}",
        # Summary
        "app_overview": "**App Overview:**\n- {entity_count} Entities\n- {facet_count} Facet values",
        "summary_title": "**Summary: {name}**\n\n",
        "type_label": "Type: {type}\n\n",
        "facets_label": "**Facets:**\n",
        "relations_label": "\n**Relations:** {count}",
        "unknown_type": "Unknown",
        # Help
        "help_intro": "**Hello! I'm your assistant for CaeliCrawler.**\n\n",
        "help_capabilities": "I can help you with:\n",
        "help_search": "- **Search**: 'Show me pain points from municipalities'\n",
        "help_navigation": "- **Navigation**: 'Go to Gummersbach'\n",
        "help_summaries": "- **Summaries**: 'Summarize this entity'\n",
        "help_changes": "- **Changes**: 'Change the name to XY' (in write mode)\n\n",
        "help_current_entity": "**You are currently at:** {name}\n",
        "help_context_hint": "Ask me e.g. 'What are the pain points here?' or 'Show me the relations'\n\n",
        "help_slash_commands": "**Slash Commands:**\n",
        # Slash commands
        "search_missing_term": "Please provide a search term: /search <query>",
        "unknown_command": "Unknown command: /{command}. Use /help for available commands.",
        # Errors
        "error_occurred": "An error occurred: {error}",
        "unknown_intent": "I couldn't understand your request. Try rephrasing it.",
        "query_error": "Error during search: {error}",
        "error_generic": "Error: {error}",
        # Action execution
        "entity_updated": "'{name}' has been updated.",
        "unknown_action": "Unknown action: {action}",
        # Follow-up suggestions
        "show_more_details": "Show me more details about a result",
        "filter_by_criteria": "Filter by a specific criterion",
        "show_pain_points": "Show pain points of {name}",
        "show_relations": "Relations of {name}",
        "show_all_municipalities": "Show all municipalities",
        "show_pain_points_generic": "Show pain points",
        # Streaming status
        "streaming_processing": "Processing request...",
        "streaming_searching": "Searching...",
        "streaming_analyzing": "Analyzing results...",
        "streaming_generating": "Generating response...",
        "streaming_complete": "Done",
        # Batch operations
        "batch_missing_filter": "Please specify which entities should be processed (e.g., 'all municipalities in NRW').",
        "batch_no_matches": "No matching entities found for the batch operation.",
        "batch_preview_message": "{count} entities would be processed.",
    },
}


def get_translation(key: str, lang: str = "de", **kwargs: Any) -> str:
    """
    Get a translated string.

    Args:
        key: Translation key
        lang: Language code ('de' or 'en')
        **kwargs: Format arguments for the string

    Returns:
        Translated and formatted string
    """
    translations = TRANSLATIONS.get(lang, TRANSLATIONS["de"])
    text = translations.get(key, TRANSLATIONS["de"].get(key, key))

    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text
    return text


class Translator:
    """Helper class for translations with a fixed language."""

    def __init__(self, language: str = "de"):
        self.language = language

    def t(self, key: str, **kwargs: Any) -> str:
        """Get a translated string."""
        return get_translation(key, self.language, **kwargs)
