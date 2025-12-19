#!/usr/bin/env python3
"""
Script to extract hardcoded German texts from HelpView.vue and create i18n translations.
"""
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Mapping of German to English translations for common terms
TRANSLATIONS = {
    # Common UI elements
    "Kategorien": "Categories",
    "Datenquellen": "Data Sources",
    "Dokumente": "Documents",
    "Gemeinden": "Municipalities",
    "Ergebnisse": "Results",
    "Crawler": "Crawler",
    "Dashboard": "Dashboard",
    "Einführung": "Introduction",
    "Schnellstart": "Quick Start",

    # Categories section
    "Kategorien sind die oberste Organisationsebene und definieren, <strong>was</strong> gesucht wird\n              und <strong>wie</strong> die Ergebnisse analysiert werden.": "Categories are the top organizational level and define <strong>what</strong> is being searched for and <strong>how</strong> the results are analyzed.",
    "Grundeinstellungen": "Basic Settings",
    "Suchbegriffe (Keywords)": "Search Terms (Keywords)",
    "Keywords für die Relevanz-Filterung:": "Keywords for relevance filtering:",
    "Dokumente werden nur zur KI-Analyse weitergeleitet, wenn sie mindestens 2 dieser Keywords enthalten.": "Documents are only forwarded to AI analysis if they contain at least 2 of these keywords.",
    "URL-Filter (Regex)": "URL Filters (Regex)",
    "KI-Extraktions-Prompt": "AI Extraction Prompt",
    "Definiert, was die KI extrahieren soll. Beispiel:": "Defines what the AI should extract. Example:",
    "Aktionen": "Actions",
    "Neu analysieren": "Reanalyze",

    # Data Sources section
    "Datenquellen sind die konkreten Websites oder APIs, die gecrawlt werden.": "Data sources are the specific websites or APIs that are crawled.",
    "Kategorie-Zuordnung (N:M)": "Category Assignment (N:M)",
    "Mehrfachzuordnung": "Multiple Assignment",
    'Eine Quelle kann z.B. sowohl für "Windkraft" als auch "Solarenergie" relevant sein': 'A source can be relevant for both "Wind Energy" and "Solar Energy", for example',
    "Crawl-Kontext": "Crawl Context",
    "Beim Crawlen wird der AI-Prompt und die Filter der gewählten Kategorie verwendet": "When crawling, the AI prompt and filters of the selected category are used",
    "Smart Query Integration": "Smart Query Integration",
    "Smart Query kann automatisch passende Quellen zu neuen Kategorien verknüpfen": "Smart Query can automatically link matching sources to new categories",
    "Quellentypen": "Source Types",
    "Standard-Website-Crawling für kommunale Websites, Nachrichtenseiten": "Standard website crawling for municipal websites, news sites",
    "OParl-Schnittstelle für Ratsinformationssysteme": "OParl interface for council information systems",
    "RSS-Feed für News-Aggregation": "RSS feed for news aggregation",
    "Verfügbare Filter": "Available Filters",
    "Land (mit Anzahl)": "Country (with count)",
    "Gemeinde (Autocomplete)": "Municipality (Autocomplete)",
    "Kategorie": "Category",
    "Status": "Status",
    "Suche (Name/URL)": "Search (Name/URL)",
    "Formular-Felder (Neue/Bearbeiten)": "Form Fields (New/Edit)",
    "Bulk Import": "Bulk Import",
    "Kategorie auswählen": "Select category",
    "JSON-Array mit Quellen eingeben:": "Enter JSON array with sources:",
    "Crawl-Konfiguration": "Crawl Configuration",
    "URL-Filter (Erweiterte Einstellungen)": "URL Filters (Advanced Settings)",
    "Status-Bedeutung": "Status Meaning",

    # Crawler section
    "Die Crawler-Seite zeigt den Live-Status aller Crawling- und KI-Aktivitäten.": "The crawler page shows the live status of all crawling and AI activities.",
    "Status-Karten": "Status Cards",
    "Aktive Worker": "Active Workers",
    "Verfügbare Prozesse": "Available Processes",
    "Laufende Jobs": "Running Jobs",
    "Aktive Crawls": "Active Crawls",
    "Wartende Jobs": "Waiting Jobs",
    "In der Queue": "In Queue",
    "Gesamt gefunden": "Total Found",
    "KI-Aufgaben (Live)": "AI Tasks (Live)",
    "Aktive Crawler (Live)": "Active Crawlers (Live)",
    "Expandierbare Panels für jeden laufenden Crawl:": "Expandable panels for each running crawl:",
    "Quelle & aktuelle URL": "Source & Current URL",
    "Seiten gecrawlt / Dokumente gefunden / Neue": "Pages Crawled / Documents Found / New",
    "Fehlerzähler (falls vorhanden)": "Error Counter (if present)",
    "Live-Log (expandierbar)": "Live Log (expandable)",
    "Job-Tabelle": "Job Table",
    "Job-Details-Dialog": "Job Details Dialog",
    "Klicken Sie auf das Info-Symbol für den vollständigen Job-Report:": "Click the info icon for the complete job report:",
    "Statistiken:": "Statistics:",
    "Seiten gecrawlt": "Pages Crawled",
    "Dokumente gefunden": "Documents Found",
    "Neue Dokumente": "New Documents",
    "Status-Filter": "Status Filter",

    # Documents section
    "Die Dokumenten-Ansicht zeigt alle gefundenen und verarbeiteten Dateien.": "The documents view shows all found and processed files.",
    "Status-Übersicht": "Status Overview",
    "Aktions-Buttons": "Action Buttons",
    "Volltextsuche": "Full Text Search",
    "Gemeinde/Ort": "Municipality/Location",
    "Typ (PDF, HTML, ...)": "Type (PDF, HTML, ...)",
    "Dokument-Details": "Document Details",
    "Original-URL mit Link": "Original URL with Link",
    "Quelle und Kategorie": "Source and Category",
    "Zeitstempel (entdeckt, geladen, verarbeitet)": "Timestamps (discovered, loaded, processed)",
    "Dateigröße und Seitenanzahl": "File Size and Page Count",
    "Anzahl KI-Extraktionen": "Number of AI Extractions",
    "Zeigt den extrahierten Rohtext des Dokuments in einem Textfeld.": "Shows the extracted raw text of the document in a text field.",
    "KI-Analyse-Ergebnisse als JSON": "AI Analysis Results as JSON",
    "Konfidenz-Score pro Extraktion": "Confidence Score per Extraction",
    "Verifizierungs-Status": "Verification Status",

    # Municipalities section
    "Übersicht aller Standorte mit aggregierten Daten und Detail-Reports.": "Overview of all locations with aggregated data and detail reports.",
    "Statistik-Karten": "Statistics Cards",
    "Anzahl Standorte": "Number of Locations",
    "Gesamtzahl": "Total Count",
    "Mit Ergebnissen": "With Results",
    "Prioritäre Gemeinden": "Priority Municipalities",
    "Tabellen-Spalten": "Table Columns",
    "Gemeindename (klickbar für Report)": "Municipality Name (clickable for report)",
    "Bundesland / Landkreis": "State / District",
    "Anzahl verknüpfter Datenquellen": "Number of Linked Data Sources",
    "Chips: Gesamt / Relevant / High Priority / Opportunity Score": "Chips: Total / Relevant / High Priority / Opportunity Score",
    "Durchschnittliche KI-Konfidenz als Fortschrittsbalken": "Average AI Confidence as Progress Bar",
    "Anzahl gefundener Entscheidungsträger": "Number of Found Decision Makers",
    "Filter": "Filters",
    "Bundesland (Admin Level 1)": "State (Admin Level 1)",
    "Landkreis (Admin Level 2)": "District (Admin Level 2)",
    "Min. Konfidenz": "Min. Confidence",
    "Suche": "Search",
    "Gemeinde-Report (Detail-Dialog)": "Municipality Report (Detail Dialog)",
    "Klicken Sie auf eine Zeile oder das Auge-Symbol für den vollständigen Report:": "Click on a row or the eye icon for the complete report:",
    "Report-Header: Gemeindename, Opportunity Score, Kategorie-Zweck": "Report Header: Municipality Name, Opportunity Score, Category Purpose",
    "Übersichts-Karten": "Overview Cards",
    "Report-Tabs": "Report Tabs",

    # Smart Query section
    "Workflow: Schreib-Modus": "Workflow: Write Mode",
    "Anfrage eingeben": "Enter Request",
    "Beschreiben Sie in natuerlicher Sprache was Sie suchen/ueberwachen moechten.": "Describe in natural language what you want to search/monitor.",
    "Schreib-Modus aktivieren": "Activate Write Mode",
    "Schalten Sie den Toggle auf \"Schreib-Modus\" um.": 'Switch the toggle to "Write Mode".',
    "Vorschau pruefen": "Check Preview",
    'Klicken Sie "Vorschau" um zu sehen was erstellt wird (EntityType, Category, Datenquellen).': 'Click "Preview" to see what will be created (EntityType, Category, Data Sources).',
    "Bestaetigen": "Confirm",
    'Klicken Sie "Bestaetigen & Erstellen". Die 3-Schritt-KI-Generierung startet.': 'Click "Confirm & Create". The 3-step AI generation starts.',
    "Crawl starten": "Start Crawl",
    "Nach Erstellung koennen Sie direkt den Crawl fuer die neue Category starten.": "After creation, you can directly start the crawl for the new category.",
    "Geografische Filter": "Geographic Filters",
    "Smart Query versteht geografische Begriffe und Abkuerzungen:": "Smart Query understands geographic terms and abbreviations:",
    "Beispiel-Anfragen": "Example Queries",
    'Liste aller Pain Points aus NRW-Gemeinden': 'List of all pain points from NRW municipalities',
    'Zukuenftige Events mit Teilnehmern': 'Future events with participants',
    'Neue Category + EntityType + Datenquellen-Verknuepfung': 'New Category + EntityType + Data Source Linking',
    'Neues Analyse-Setup fuer Bayern': 'New analysis setup for Bavaria',
}

def find_hardcoded_texts(vue_file: str) -> List[Tuple[str, str]]:
    """Find hardcoded German texts in Vue template."""
    with open(vue_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # List of patterns to find hardcoded German text
    patterns = [
        # Text between HTML tags
        r'<(?:h[1-6]|p|td|th|div|li|strong|v-alert|v-list-item-title|v-list-item-subtitle|v-chip|v-card-title|v-expansion-panel-title)[^>]*>([^<{]+?)</\1>',
        # Text in v-chip and similar components
        r'<v-chip[^>]*>([^<]+?)</v-chip>',
    ]

    found_texts = []
    for pattern in patterns:
        matches = re.finditer(pattern, content, re.MULTILINE)
        for match in matches:
            text = match.group(1).strip()
            # Check if it's German (contains common German characters or words)
            if text and not text.startswith('{{') and not text.startswith('mdi-'):
                # Skip if already using i18n
                if 't(' not in text and '$t(' not in text:
                    found_texts.append((match.start(), text))

    return found_texts

print("This script helps translate HelpView.vue to i18n.")
print("Due to the complexity and size of the file, manual translation is recommended.")
print("The translations are already structured in the de/help/*.json files.")
