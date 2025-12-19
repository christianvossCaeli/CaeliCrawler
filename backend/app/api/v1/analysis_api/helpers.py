"""Helper functions for analysis API - translations and preview building."""

from typing import Dict


def operation_to_german(op: str) -> str:
    """Convert operation to German."""
    return {
        "create_entity": "Entity erstellen",
        "create_entity_type": "Entity-Typ erstellen",
        "create_facet": "Facet hinzufügen",
        "create_relation": "Verknüpfung erstellen",
        "update_entity": "Entity aktualisieren",
        "create_category_setup": "Category-Setup erstellen",
        "start_crawl": "Crawl starten",
        "combined": "Kombinierte Operationen",
    }.get(op, op)


def entity_type_to_german(et: str) -> str:
    """Convert entity type to German."""
    return {
        "municipality": "Gemeinde",
        "person": "Person",
        "organization": "Organisation",
        "event": "Veranstaltung",
    }.get(et, et)


def facet_type_to_german(ft: str) -> str:
    """Convert facet type to German."""
    return {
        "pain_point": "Pain Point / Problem",
        "positive_signal": "Positive Signal / Chance",
        "contact": "Kontakt",
        "event_attendance": "Event-Teilnahme",
        "summary": "Zusammenfassung",
    }.get(ft, ft)


def relation_to_german(rt: str) -> str:
    """Convert relation type to German."""
    return {
        "works_for": "arbeitet für",
        "attends": "nimmt teil an",
        "located_in": "befindet sich in",
        "member_of": "ist Mitglied von",
    }.get(rt, rt)


def build_preview(command: dict) -> dict:
    """Build a human-readable preview of what will be created."""
    operation = command.get("operation", "none")
    preview = {
        "operation_de": operation_to_german(operation),
        "description": command.get("explanation", ""),
        "details": [],
    }

    if operation == "create_entity":
        entity_data = command.get("entity_data", {})
        entity_type = command.get("entity_type", "unknown")
        preview["details"] = [
            f"Typ: {entity_type_to_german(entity_type)}",
            f"Name: {entity_data.get('name', 'N/A')}",
        ]
        attrs = entity_data.get("core_attributes", {})
        for key, value in attrs.items():
            if value:
                preview["details"].append(f"{key.title()}: {value}")

    elif operation == "create_facet":
        facet_data = command.get("facet_data", {})
        preview["details"] = [
            f"Facet-Typ: {facet_type_to_german(facet_data.get('facet_type', 'unknown'))}",
            f"Für Entity: {facet_data.get('target_entity_name', 'N/A')}",
            f"Inhalt: {facet_data.get('text_representation', 'N/A')}",
        ]

    elif operation == "create_relation":
        rel_data = command.get("relation_data", {})
        preview["details"] = [
            f"Verknüpfung: {relation_to_german(rel_data.get('relation_type', 'unknown'))}",
            f"Von: {rel_data.get('source_entity_name', 'N/A')} ({rel_data.get('source_entity_type', '')})",
            f"Nach: {rel_data.get('target_entity_name', 'N/A')} ({rel_data.get('target_entity_type', '')})",
        ]

    elif operation == "create_entity_type":
        type_data = command.get("entity_type_data", {})
        preview["details"] = [
            f"Name: {type_data.get('name', 'N/A')}",
            f"Plural: {type_data.get('name_plural', 'N/A')}",
            f"Icon: {type_data.get('icon', 'mdi-folder')}",
            f"Farbe: {type_data.get('color', '#4CAF50')}",
        ]
        if type_data.get("description"):
            preview["details"].append(f"Beschreibung: {type_data.get('description')}")

    elif operation == "create_category_setup":
        setup_data = command.get("category_setup_data", {})
        preview["details"] = [
            f"Name: {setup_data.get('name', 'N/A')}",
            f"Zweck: {setup_data.get('purpose', 'N/A')}",
        ]
        geo_filter = setup_data.get("geographic_filter", {})
        if geo_filter.get("admin_level_1"):
            preview["details"].append(f"Region: {geo_filter.get('admin_level_1')}")
        if geo_filter.get("admin_level_2"):
            preview["details"].append(f"Kreis/Stadt: {geo_filter.get('admin_level_2')}")
        search_terms = setup_data.get("search_terms", [])
        if search_terms:
            preview["details"].append(f"Suchbegriffe: {', '.join(search_terms[:5])}")
        search_focus = setup_data.get("search_focus", "general")
        focus_de = {
            "event_attendance": "Events & Teilnahmen",
            "pain_points": "Probleme & Herausforderungen",
            "contacts": "Kontakte & Ansprechpartner",
            "general": "Allgemein",
        }.get(search_focus, search_focus)
        preview["details"].append(f"Fokus: {focus_de}")
        preview["details"].append("→ Erstellt EntityType + Category + verknüpft Datenquellen")

    elif operation == "start_crawl":
        crawl_data = command.get("crawl_command_data", {})
        filter_type = crawl_data.get("filter_type", "unknown")
        preview["details"] = [f"Filter-Typ: {filter_type}"]
        if crawl_data.get("location_name"):
            preview["details"].append(f"Ort: {crawl_data.get('location_name')}")
        if crawl_data.get("admin_level_1"):
            preview["details"].append(f"Region: {crawl_data.get('admin_level_1')}")
        if crawl_data.get("category_slug"):
            preview["details"].append(f"Category: {crawl_data.get('category_slug')}")
        if crawl_data.get("entity_name"):
            preview["details"].append(f"Entity: {crawl_data.get('entity_name')}")
        preview["details"].append("→ Startet Crawl-Jobs für passende Datenquellen")

    elif operation == "combined":
        # Support both "operations" and "combined_operations" keys
        operations_list = command.get("operations", []) or command.get("combined_operations", [])
        preview["details"] = [f"Anzahl Operationen: {len(operations_list)}"]
        for i, sub_op in enumerate(operations_list, 1):
            op_name = sub_op.get("operation", "unknown")
            op_de = operation_to_german(op_name)
            preview["details"].append(f"  {i}. {op_de}")
        preview["details"].append("→ Führt alle Operationen nacheinander aus")

    return preview
