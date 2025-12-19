#!/usr/bin/env python3
"""
Seed script to populate the database with categories and data sources
for Wind Energy Sales Intelligence.

Use Case:
- Monitor municipal publications (council meetings, decisions, news)
- Identify pain points and positive signals regarding wind energy
- Enable personalized outreach to municipalities

Run with: python -m scripts.seed_data
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.database import get_session_context
from app.models import Category, DataSource, SourceType, SourceStatus


# =============================================================================
# KATEGORIEN - Organisiert nach Sales Intelligence Zielen
# =============================================================================

CATEGORIES = [
    # -------------------------------------------------------------------------
    # 1. KOMMUNALE RATSINFORMATIONEN (OParl)
    # -------------------------------------------------------------------------
    {
        "name": "Ratsinformationen NRW",
        "slug": "ratsinformationen-nrw",
        "description": "Gemeinderats- und Kreistagssitzungen aus NRW-Kommunen",
        "purpose": """Monitoring kommunaler Entscheidungen zu Windenergie:
- Flächennutzungspläne und Konzentrationszonen
- Genehmigungsverfahren und Einwände
- Bürgerbeteiligung und Widerstand
- Beschlüsse zu Mindestabständen""",
        "search_terms": [
            "Windkraft", "Windenergie", "Windrad", "Windpark",
            "Flächennutzungsplan", "Konzentrationsfläche", "Vorranggebiet",
            "Repowering", "Abstandsregelung", "Höhenbegrenzung",
            "Artenschutz", "Vogelschutz", "Bürgerwindpark"
        ],
        "ai_extraction_prompt": """Analysiere dieses kommunale Dokument für Sales Intelligence im Bereich Windenergie.

WICHTIG: Extrahiere NUR Informationen, die DIREKT mit Windenergie, Windkraft oder erneuerbaren Energien zusammenhängen!
- Ignoriere allgemeine kommunale Themen (Haushalt, Personal, Verkehr, etc.) KOMPLETT
- Pain Points und Positive Signals müssen sich auf Windenergie/Erneuerbare beziehen
- Wenn das Dokument KEINE Windenergie-relevanten Inhalte hat, setze is_relevant=false und lasse pain_points/positive_signals LEER

EXTRAHIERE IM JSON-FORMAT:
{
  "is_relevant": true/false (NUR true wenn Windenergie/Erneuerbare Energien explizit behandelt werden),
  "relevanz": "hoch|mittel|gering|keine",
  "municipality": "Name der Gemeinde/Stadt",
  "document_type": "Beschluss|Antrag|Anfrage|Bericht|Sonstiges",
  "document_date": "YYYY-MM-DD oder null",

  "pain_points": [
    NUR Windenergie-bezogene Probleme! Beispiele:
    - Bürgerproteste gegen Windräder
    - Naturschutz-Konflikte bei Windparks
    - Abstandsregelungen für Windkraftanlagen
    - Lärmbelästigung durch Windräder
    - Genehmigungsprobleme für Windprojekte
    {
      "type": "Bürgerprotest|Naturschutz|Abstandsregelung|Genehmigung|Lärm|Optik|Artenschutz",
      "description": "Konkrete Beschreibung des Windenergie-Problems",
      "severity": "hoch|mittel|niedrig",
      "quote": "Originalzitat aus dem Dokument"
    }
  ],

  "positive_signals": [
    NUR Windenergie-bezogene positive Signale! Beispiele:
    - Interesse an Windkraftausbau
    - Genehmigung von Windparks
    - Bürgerwindpark-Beteiligungen
    - Klimaziele mit Windenergie-Bezug
    - Flächenausweisungen für Windkraft
    {
      "type": "Interesse|Planung|Genehmigung|Bürgerbeteiligung|Klimaziel|Flächenausweisung",
      "description": "Konkrete Beschreibung des positiven Signals für Windenergie",
      "quote": "Originalzitat"
    }
  ],

  "decision_makers": [
    NUR Personen mit Bezug zu Energie/Windkraft-Entscheidungen
    {
      "name": "Name der Person",
      "role": "Bürgermeister|Ratsmitglied|Amtsleiter|Energiebeauftragter|Stadtwerke-GF",
      "stance": "positiv|neutral|negativ|unbekannt (zu Windenergie)"
    }
  ],

  "current_status": "Planung|Prüfung|Genehmigt|Abgelehnt|Diskussion|Unbekannt",
  "timeline": "Erwähnte Fristen oder Zeitpläne für Windprojekte",
  "next_steps": ["Nächste geplante Schritte bzgl. Windenergie"],

  "outreach_recommendation": {
    "priority": "hoch|mittel|niedrig",
    "approach": "Empfohlene Ansprache-Strategie",
    "key_message": "Kernbotschaft für Ansprache",
    "contact_timing": "Optimaler Zeitpunkt"
  },

  "summary": "Kurze Zusammenfassung mit Fokus auf Windenergie-Aspekte (2-3 Sätze)"
}

NOCHMAL: Wenn keine Windenergie-Inhalte vorhanden sind → is_relevant=false, pain_points=[], positive_signals=[]""",
        "schedule_cron": "0 6 * * *",  # Täglich um 6 Uhr
    },

    # -------------------------------------------------------------------------
    # 2. KOMMUNALE WEBSITES & NEWS - WINDENERGIE
    # -------------------------------------------------------------------------
    {
        "name": "Kommunale News - Windenergie",
        "slug": "kommunale-news",
        "description": "Aktuelle Meldungen und Pressemitteilungen von Gemeinden zu Windenergie-Themen",
        "purpose": """Monitoring öffentlicher Kommunikation zu Windenergie:
- Pressemitteilungen zu Windenergieprojekten
- News über Bürgerwindparks und Beteiligungen
- Ankündigungen von Informationsveranstaltungen zu Windkraft
- Statements von Bürgermeistern und Räten zu Windenergie""",
        "search_terms": [
            "Windkraft", "Windenergie", "Windrad", "Windpark", "Windenergieanlage",
            "Erneuerbare Energien", "Energiewende", "Bürgerwindpark",
            "Repowering", "Flächennutzungsplan", "Konzentrationsfläche",
            "Genehmigung Windkraft", "Windvorranggebiet", "Klimaschutz Windenergie"
        ],
        "ai_extraction_prompt": """Analysiere diese kommunale Pressemitteilung/News für Sales Intelligence.

EXTRAHIERE IM JSON-FORMAT:
{
  "is_relevant": true/false,
  "municipality": "Name der Gemeinde/Stadt",
  "publication_date": "YYYY-MM-DD",
  "news_type": "Pressemitteilung|Ankündigung|Bericht|Statement",

  "topic": "Hauptthema der Meldung",
  "sentiment": "positiv|neutral|negativ|gemischt",

  "decision_makers": [
    {
      "person": "Name",
      "role": "Position",
      "statement": "Zitat",
      "sentiment": "positiv|neutral|negativ"
    }
  ],

  "events_mentioned": [
    {
      "type": "Informationsveranstaltung|Ratssitzung|Bürgerbeteiligung",
      "date": "YYYY-MM-DD oder null",
      "location": "Ort"
    }
  ],

  "positive_signals": ["Identifizierte Chancen für Ansprache"],
  "pain_points": ["Erwähnte Bedenken oder Probleme"],

  "contact_opportunity": {
    "exists": true/false,
    "type": "Veranstaltung|Meeting|Gespräch",
    "timing": "Zeitfenster"
  },

  "summary": "Kurze Zusammenfassung"
}""",
        "schedule_cron": "0 8 * * *",
    },

    # -------------------------------------------------------------------------
    # 3. BUNDESTAG & LANDTAGE
    # -------------------------------------------------------------------------
    {
        "name": "Parlamentarische Anfragen Energie",
        "slug": "parlamentarische-anfragen",
        "description": "Kleine Anfragen und Drucksachen zu Energiethemen",
        "purpose": """Monitoring der politischen Landschaft:
- Anfragen zu Windkraft-Regulierung
- Gesetzesinitiativen
- Statistische Anfragen zu Genehmigungen
- Politische Positionierungen""",
        "search_terms": [
            "Windenergie", "Windkraft", "Erneuerbare Energien",
            "Genehmigungsverfahren", "Abstandsregelung", "BImSchG",
            "Flächenausweisung", "Repowering"
        ],
        "ai_extraction_prompt": """Analysiere dieses parlamentarische Dokument für Market Intelligence.

EXTRAHIERE IM JSON-FORMAT:
{
  "is_relevant": true/false,
  "document_type": "Kleine Anfrage|Große Anfrage|Antrag|Gesetzentwurf|Antwort",
  "legislative_period": "Wahlperiode",
  "date": "YYYY-MM-DD",

  "initiators": [
    {
      "name": "Name",
      "party": "Partei/Fraktion",
      "role": "Abgeordneter|Fraktion|Regierung"
    }
  ],

  "main_topic": "Hauptthema",
  "sub_topics": ["Unterthemen"],

  "regulatory_changes": [
    {
      "type": "Geplant|Diskutiert|Beschlossen",
      "description": "Beschreibung der Änderung",
      "impact": "Auswirkung auf Windenergie"
    }
  ],

  "statistics_mentioned": [
    {
      "metric": "Was wird gemessen",
      "value": "Wert",
      "region": "Betroffene Region"
    }
  ],

  "political_positions": {
    "pro_wind": ["Argumente/Positionen"],
    "contra_wind": ["Argumente/Positionen"]
  },

  "market_implications": "Auswirkungen auf den Markt",
  "summary": "Kurze Zusammenfassung"
}""",
        "schedule_cron": "0 9 * * 1-5",
    },

    # -------------------------------------------------------------------------
    # 4. IFG-ANFRAGEN (FragDenStaat)
    # -------------------------------------------------------------------------
    {
        "name": "IFG-Anfragen Windenergie",
        "slug": "ifg-anfragen",
        "description": "Informationsfreiheitsanfragen zu Windenergie-Themen",
        "purpose": """Einblicke in behördliche Prozesse:
- Genehmigungsverfahren
- Interne Behördenkommunikation
- Gutachten und Studien
- Ablehnungsgründe""",
        "search_terms": [
            "Windkraft", "Windenergie", "Genehmigung",
            "BImSchG", "Umweltverträglichkeit", "Artenschutz"
        ],
        "ai_extraction_prompt": """Analysiere diese IFG-Anfrage/Antwort für Business Intelligence.

EXTRAHIERE IM JSON-FORMAT:
{
  "is_relevant": true/false,
  "request_topic": "Thema der Anfrage",
  "authority": "Angefragte Behörde",
  "status": "erfolgreich|teilweise_erfolgreich|abgelehnt|ausstehend",

  "information_revealed": [
    {
      "type": "Gutachten|Korrespondenz|Statistik|Entscheidung",
      "description": "Was wurde offengelegt",
      "relevance": "hoch|mittel|niedrig"
    }
  ],

  "approval_barriers": ["Identifizierte Hürden im Genehmigungsprozess"],
  "processing_times": "Erwähnte Bearbeitungszeiten",
  "rejection_reasons": ["Ablehnungsgründe falls genannt"],

  "business_insights": ["Geschäftsrelevante Erkenntnisse"],
  "summary": "Kurze Zusammenfassung"
}""",
        "schedule_cron": "0 10 * * 3",
    },

    # -------------------------------------------------------------------------
    # 5. OPEN DATA - STANDORTANALYSE
    # -------------------------------------------------------------------------
    {
        "name": "Standortdaten Windenergie",
        "slug": "standortdaten",
        "description": "Offene Daten für Standortbewertung",
        "purpose": """Datengrundlage für Standortanalysen:
- Windpotenzialflächen
- Schutzgebiete und Restriktionen
- Bestehende Anlagen
- Netzinfrastruktur""",
        "search_terms": [
            "Windenergie", "Windpotenzial", "Vorranggebiet",
            "Naturschutzgebiet", "Landschaftsschutz", "Netzausbau"
        ],
        "ai_extraction_prompt": """Beschreibe diesen Datensatz für Standortanalyse.

EXTRAHIERE IM JSON-FORMAT:
{
  "dataset_name": "Name des Datensatzes",
  "publisher": "Herausgeber",
  "geographic_coverage": "Geografische Abdeckung",
  "temporal_coverage": "Zeitliche Abdeckung",
  "update_frequency": "Aktualisierungsfrequenz",

  "data_type": "Geodaten|Statistik|Register|Bericht",
  "relevance_for": ["Standortsuche", "Restriktionsanalyse", "Potenzialanalyse"],

  "key_attributes": ["Wichtige enthaltene Attribute"],
  "data_quality": "hoch|mittel|niedrig|unbekannt",
  "access_type": "Download|API|WMS|WFS",

  "use_cases": ["Mögliche Anwendungsfälle"],
  "summary": "Kurze Beschreibung"
}""",
        "schedule_cron": "0 2 * * 0",
    },

    # -------------------------------------------------------------------------
    # 6. LEAD-QUALIFIZIERUNG WINDENERGIE (Meta-Kategorie)
    # -------------------------------------------------------------------------
    {
        "name": "Lead-Qualifizierung Windenergie",
        "slug": "lead-qualifizierung",
        "description": "Bewertung von Kommunen als potenzielle Windenergie-Leads",
        "purpose": """Konsolidierte Lead-Bewertung für Windenergie-Vertrieb:
- Zusammenführung aller Windenergie-Signale pro Kommune
- Lead-Scoring basierend auf Windkraft-Aktivität und -Interesse
- Priorisierung für Windenergie-Vertrieb
- Personalisierte Ansprache-Empfehlungen für Windprojekte""",
        "search_terms": [
            "Windkraft Interesse", "Windenergie Potenzial", "Windvorranggebiet",
            "Flächennutzungsplan Wind", "Bürgermeister Windkraft",
            "Energiebeauftragter", "Klimaschutzmanager",
            "Windpark Planung", "Repowering Interesse", "Bürgerenergie"
        ],
        "ai_extraction_prompt": """Erstelle eine Lead-Bewertung für diese Kommune basierend auf allen verfügbaren Informationen.

EXTRAHIERE IM JSON-FORMAT:
{
  "municipality": "Name der Kommune",
  "state": "Bundesland",
  "population": "Einwohnerzahl falls bekannt",

  "lead_score": {
    "total": 0-100,
    "interest_level": 0-100,
    "urgency": 0-100,
    "accessibility": 0-100,
    "fit": 0-100
  },

  "classification": "Hot Lead|Warm Lead|Cold Lead|Not Qualified",

  "wind_energy_status": {
    "existing_turbines": "Anzahl oder unbekannt",
    "planned_projects": "Ja|Nein|Unbekannt",
    "general_stance": "Positiv|Neutral|Negativ|Gemischt"
  },

  "pain_points_summary": [
    {
      "pain_point": "Beschreibung",
      "our_solution": "Wie wir helfen können",
      "priority": "hoch|mittel|niedrig"
    }
  ],

  "positive_signals_summary": ["Identifizierte Chancen"],

  "key_contacts": [
    {
      "name": "Name",
      "role": "Position",
      "stance": "positiv|neutral|negativ",
      "contact_priority": "hoch|mittel|niedrig"
    }
  ],

  "recommended_approach": {
    "channel": "Persönlich|Telefon|Email|Veranstaltung",
    "timing": "Sofort|Diese Woche|Dieser Monat|Beobachten",
    "key_message": "Kernbotschaft",
    "talking_points": ["Gesprächspunkte"],
    "avoid": ["Was vermieden werden sollte"]
  },

  "next_actions": [
    {
      "action": "Empfohlene Aktion",
      "deadline": "Zeitrahmen",
      "responsible": "Vertrieb|Marketing|Management"
    }
  ],

  "data_sources": ["Liste der verwendeten Quellen"],
  "confidence": "hoch|mittel|niedrig",
  "last_updated": "YYYY-MM-DD"
}""",
        "schedule_cron": "0 7 * * 1",  # Montags für wöchentliches Update
    },
]


# =============================================================================
# DATENQUELLEN - Pro Kategorie
# =============================================================================

DATA_SOURCES = {
    # -------------------------------------------------------------------------
    # Ratsinformationen NRW (OParl)
    # -------------------------------------------------------------------------
    "ratsinformationen-nrw": [
        {
            "name": "Stadt Münster - Ratsinformation",
            "source_type": SourceType.OPARL_API,
            "base_url": "https://oparl.stadt-muenster.de/system",
            "api_endpoint": "https://oparl.stadt-muenster.de/system",
            "country": "DE",
            "location_name": "Münster",
            "admin_level_1": "Nordrhein-Westfalen",
            "crawl_config": {
                "max_pages": 100,
                "filter_keywords": ["Wind", "Energie", "Klima", "Flächennutzung"],
            },
            "extra_data": {
                "einwohner": 317000,
                "region": "Münsterland"
            },
            "priority": 10,
        },
        {
            "name": "Stadt Köln - Ratsinformation",
            "source_type": SourceType.OPARL_API,
            "base_url": "https://sdnetrim.kdvz-frechen.de/rim4550/webservice/oparl/v1/system",
            "api_endpoint": "https://sdnetrim.kdvz-frechen.de/rim4550/webservice/oparl/v1/system",
            "country": "DE",
            "location_name": "Köln",
            "admin_level_1": "Nordrhein-Westfalen",
            "crawl_config": {
                "max_pages": 200,
                "filter_keywords": ["Wind", "Energie", "Klima", "Flächennutzung"],
            },
            "extra_data": {
                "einwohner": 1084000,
                "region": "Köln/Bonn"
            },
            "priority": 10,
        },
        {
            "name": "Stadt Düsseldorf - Ratsinformation",
            "source_type": SourceType.OPARL_API,
            "base_url": "https://oparl.duesseldorf.de/oparl/v1.1/system",
            "api_endpoint": "https://oparl.duesseldorf.de/oparl/v1.1/system",
            "country": "DE",
            "location_name": "Düsseldorf",
            "admin_level_1": "Nordrhein-Westfalen",
            "crawl_config": {
                "max_pages": 200,
                "filter_keywords": ["Wind", "Energie", "Klima", "Flächennutzung"],
            },
            "extra_data": {
                "einwohner": 621877,
                "region": "Düsseldorf"
            },
            "priority": 10,
        },
        {
            "name": "Stadt Bonn - Ratsinformation",
            "source_type": SourceType.OPARL_API,
            "base_url": "https://oparl.bonn.de/oparl/v1.1/system",
            "api_endpoint": "https://oparl.bonn.de/oparl/v1.1/system",
            "country": "DE",
            "location_name": "Bonn",
            "admin_level_1": "Nordrhein-Westfalen",
            "crawl_config": {
                "max_pages": 100,
                "filter_keywords": ["Wind", "Energie", "Klima", "Flächennutzung"],
            },
            "extra_data": {
                "einwohner": 336465,
                "region": "Köln/Bonn"
            },
            "priority": 10,
        },
        {
            "name": "Stadt Dortmund - Ratsinformation",
            "source_type": SourceType.OPARL_API,
            "base_url": "https://sdnetrim.kdvz-frechen.de/rim4571/webservice/oparl/v1/system",
            "api_endpoint": "https://sdnetrim.kdvz-frechen.de/rim4571/webservice/oparl/v1/system",
            "country": "DE",
            "location_name": "Dortmund",
            "admin_level_1": "Nordrhein-Westfalen",
            "crawl_config": {
                "max_pages": 150,
                "filter_keywords": ["Wind", "Energie", "Klima", "Flächennutzung"],
            },
            "extra_data": {
                "einwohner": 593317,
                "region": "Ruhrgebiet"
            },
            "priority": 10,
        },
        {
            "name": "Stadt Essen - Ratsinformation",
            "source_type": SourceType.OPARL_API,
            "base_url": "https://oparl.essen.de/oparl/v1.1/system",
            "api_endpoint": "https://oparl.essen.de/oparl/v1.1/system",
            "country": "DE",
            "location_name": "Essen",
            "admin_level_1": "Nordrhein-Westfalen",
            "crawl_config": {
                "max_pages": 150,
                "filter_keywords": ["Wind", "Energie", "Klima", "Flächennutzung"],
            },
            "extra_data": {
                "einwohner": 579432,
                "region": "Ruhrgebiet"
            },
            "priority": 10,
        },
        {
            "name": "Stadt Duisburg - Ratsinformation",
            "source_type": SourceType.OPARL_API,
            "base_url": "https://oparl.duisburg.de/oparl/v1/system",
            "api_endpoint": "https://oparl.duisburg.de/oparl/v1/system",
            "country": "DE",
            "location_name": "Duisburg",
            "admin_level_1": "Nordrhein-Westfalen",
            "crawl_config": {
                "max_pages": 150,
                "filter_keywords": ["Wind", "Energie", "Klima", "Flächennutzung"],
            },
            "extra_data": {
                "einwohner": 504795,
                "region": "Ruhrgebiet"
            },
            "priority": 10,
        },
        {
            "name": "Stadt Bochum - Ratsinformation",
            "source_type": SourceType.OPARL_API,
            "base_url": "https://oparl.bochum.de/oparl/v1.1/system",
            "api_endpoint": "https://oparl.bochum.de/oparl/v1.1/system",
            "country": "DE",
            "location_name": "Bochum",
            "admin_level_1": "Nordrhein-Westfalen",
            "crawl_config": {
                "max_pages": 100,
                "filter_keywords": ["Wind", "Energie", "Klima", "Flächennutzung"],
            },
            "extra_data": {
                "einwohner": 365587,
                "region": "Ruhrgebiet"
            },
            "priority": 10,
        },
        {
            "name": "Stadt Wuppertal - Ratsinformation",
            "source_type": SourceType.OPARL_API,
            "base_url": "https://oparl.wuppertal.de/oparl/v1/system",
            "api_endpoint": "https://oparl.wuppertal.de/oparl/v1/system",
            "country": "DE",
            "location_name": "Wuppertal",
            "admin_level_1": "Nordrhein-Westfalen",
            "crawl_config": {
                "max_pages": 100,
                "filter_keywords": ["Wind", "Energie", "Klima", "Flächennutzung"],
            },
            "extra_data": {
                "einwohner": 359012,
                "region": "Bergisches Land"
            },
            "priority": 10,
        },
        {
            "name": "Stadt Bielefeld - Ratsinformation",
            "source_type": SourceType.OPARL_API,
            "base_url": "https://oparl.bielefeld.de/oparl/v1.1/system",
            "api_endpoint": "https://oparl.bielefeld.de/oparl/v1.1/system",
            "country": "DE",
            "location_name": "Bielefeld",
            "admin_level_1": "Nordrhein-Westfalen",
            "crawl_config": {
                "max_pages": 100,
                "filter_keywords": ["Wind", "Energie", "Klima", "Flächennutzung"],
            },
            "extra_data": {
                "einwohner": 336352,
                "region": "Ostwestfalen-Lippe"
            },
            "priority": 10,
        },
        {
            "name": "Stadt Gelsenkirchen - Ratsinformation",
            "source_type": SourceType.OPARL_API,
            "base_url": "https://oparl.gelsenkirchen.de/oparl/v1/system",
            "api_endpoint": "https://oparl.gelsenkirchen.de/oparl/v1/system",
            "country": "DE",
            "location_name": "Gelsenkirchen",
            "admin_level_1": "Nordrhein-Westfalen",
            "crawl_config": {
                "max_pages": 100,
                "filter_keywords": ["Wind", "Energie", "Klima", "Flächennutzung"],
            },
            "extra_data": {
                "einwohner": 262528,
                "region": "Ruhrgebiet"
            },
            "priority": 9,
        },
        {
            "name": "Stadt Aachen - Ratsinformation",
            "source_type": SourceType.OPARL_API,
            "base_url": "https://ratsinfo.aachen.de/bi/oparl/1.0/system.asp",
            "api_endpoint": "https://ratsinfo.aachen.de/bi/oparl/1.0/system.asp",
            "country": "DE",
            "location_name": "Aachen",
            "admin_level_1": "Nordrhein-Westfalen",
            "crawl_config": {
                "max_pages": 100,
                "filter_keywords": ["Wind", "Energie", "Klima", "Flächennutzung"],
            },
            "extra_data": {
                "einwohner": 249070,
                "region": "Städteregion Aachen"
            },
            "priority": 9,
        },
        {
            "name": "Kreis Steinfurt - Ratsinformation",
            "source_type": SourceType.OPARL_API,
            "base_url": "https://sdnetrim.kdvz-frechen.de/rim4000/webservice/oparl/v1/system",
            "api_endpoint": "https://sdnetrim.kdvz-frechen.de/rim4000/webservice/oparl/v1/system",
            "country": "DE",
            "location_name": "Steinfurt",
            "admin_level_1": "Nordrhein-Westfalen",
            "crawl_config": {
                "max_pages": 100,
                "filter_keywords": ["Wind", "Energie", "Klima", "Flächennutzung"],
            },
            "extra_data": {
                "kreis": True,
                "region": "Münsterland"
            },
            "priority": 8,
        },
        {
            "name": "Kreis Borken - Ratsinformation",
            "source_type": SourceType.OPARL_API,
            "base_url": "https://sdnetrim.kdvz-frechen.de/rim4501/webservice/oparl/v1/system",
            "api_endpoint": "https://sdnetrim.kdvz-frechen.de/rim4501/webservice/oparl/v1/system",
            "country": "DE",
            "location_name": "Borken",
            "admin_level_1": "Nordrhein-Westfalen",
            "crawl_config": {
                "max_pages": 100,
                "filter_keywords": ["Wind", "Energie", "Klima", "Flächennutzung"],
            },
            "extra_data": {
                "kreis": True,
                "region": "Münsterland"
            },
            "priority": 8,
        },
        {
            "name": "Kreis Warendorf - Ratsinformation",
            "source_type": SourceType.OPARL_API,
            "base_url": "https://sdnetrim.kdvz-frechen.de/rim4003/webservice/oparl/v1/system",
            "api_endpoint": "https://sdnetrim.kdvz-frechen.de/rim4003/webservice/oparl/v1/system",
            "country": "DE",
            "location_name": "Warendorf",
            "admin_level_1": "Nordrhein-Westfalen",
            "crawl_config": {
                "max_pages": 100,
                "filter_keywords": ["Wind", "Energie", "Klima", "Flächennutzung"],
            },
            "extra_data": {
                "kreis": True,
                "region": "Münsterland"
            },
            "priority": 8,
        },
        {
            "name": "Kreis Coesfeld - Ratsinformation",
            "source_type": SourceType.OPARL_API,
            "base_url": "https://sdnetrim.kdvz-frechen.de/rim4002/webservice/oparl/v1/system",
            "api_endpoint": "https://sdnetrim.kdvz-frechen.de/rim4002/webservice/oparl/v1/system",
            "country": "DE",
            "location_name": "Coesfeld",
            "admin_level_1": "Nordrhein-Westfalen",
            "crawl_config": {
                "max_pages": 100,
                "filter_keywords": ["Wind", "Energie", "Klima", "Flächennutzung"],
            },
            "extra_data": {
                "kreis": True,
                "region": "Münsterland"
            },
            "priority": 8,
        },
        {
            "name": "Kreis Paderborn - Ratsinformation",
            "source_type": SourceType.OPARL_API,
            "base_url": "https://sdnetrim.kdvz-frechen.de/rim4064/webservice/oparl/v1/system",
            "api_endpoint": "https://sdnetrim.kdvz-frechen.de/rim4064/webservice/oparl/v1/system",
            "country": "DE",
            "location_name": "Paderborn",
            "admin_level_1": "Nordrhein-Westfalen",
            "crawl_config": {
                "max_pages": 100,
                "filter_keywords": ["Wind", "Energie", "Klima", "Flächennutzung"],
            },
            "extra_data": {
                "kreis": True,
                "region": "Ostwestfalen-Lippe"
            },
            "priority": 8,
        },
    ],

    # -------------------------------------------------------------------------
    # Kommunale News (RSS Feeds)
    # -------------------------------------------------------------------------
    "kommunale-news": [
        {
            "name": "Bundesregierung - Energie & Klima",
            "source_type": SourceType.RSS,
            "base_url": "https://www.bundesregierung.de/breg-de/themen/klimaschutz",
            "api_endpoint": "https://www.bundesregierung.de/breg-de/service/rss/992814-992814",
            "crawl_config": {
                "filter_keywords": ["Wind", "Energie", "Erneuerbar"],
            },
            "extra_data": {"type": "Bundesregierung", "scope": "national"},
            "priority": 8,
        },
        {
            "name": "BMWK - Pressemitteilungen",
            "source_type": SourceType.RSS,
            "base_url": "https://www.bmwk.de/",
            "api_endpoint": "https://www.bmwk.de/SiteGlobals/Functions/RSSFeed/DE/RSSNewsfeed/Pressemitteilungen/RSSNewsfeed.xml",
            "crawl_config": {
                "filter_keywords": ["Wind", "Energie", "Erneuerbar", "Strom"],
            },
            "extra_data": {"type": "Ministerium", "scope": "national"},
            "priority": 9,
        },
    ],

    # -------------------------------------------------------------------------
    # Parlamentarische Anfragen (DIP Bundestag)
    # -------------------------------------------------------------------------
    "parlamentarische-anfragen": [
        {
            "name": "Bundestag - Kleine Anfragen Windenergie",
            "source_type": SourceType.CUSTOM_API,
            "base_url": "https://search.dip.bundestag.de/api/v1/vorgang?f.vorgangstyp=Kleine%20Anfrage",
            "api_endpoint": "https://search.dip.bundestag.de/api/v1/vorgang",
            "crawl_config": {
                "api_type": "dip_bundestag",
                "wahlperiode": 20,
                "vorgangstyp": "Kleine Anfrage",
                "search_query": "Windenergie OR Windkraft",
                "max_results": 500,
            },
            "extra_data": {"document_type": "Kleine Anfrage"},
            "priority": 10,
        },
        {
            "name": "Bundestag - Drucksachen Erneuerbare Energien",
            "source_type": SourceType.CUSTOM_API,
            "base_url": "https://search.dip.bundestag.de/api/v1/drucksache",
            "api_endpoint": "https://search.dip.bundestag.de/api/v1/drucksache",
            "crawl_config": {
                "api_type": "dip_bundestag",
                "wahlperiode": 20,
                "search_query": "Erneuerbare Energien Windkraft",
                "max_results": 300,
            },
            "extra_data": {"document_type": "Drucksache"},
            "priority": 8,
        },
    ],

    # -------------------------------------------------------------------------
    # IFG-Anfragen (FragDenStaat)
    # -------------------------------------------------------------------------
    "ifg-anfragen": [
        {
            "name": "FragDenStaat - Windkraft Genehmigungen",
            "source_type": SourceType.CUSTOM_API,
            "base_url": "https://fragdenstaat.de/api/v1/request/?q=Windkraft+Genehmigung",
            "api_endpoint": "https://fragdenstaat.de/api/v1/request/",
            "crawl_config": {
                "api_type": "fragdenstaat",
                "search_query": "Windkraft Genehmigung",
                "max_results": 300,
            },
            "extra_data": {"topic": "Genehmigungen"},
            "priority": 10,
        },
        {
            "name": "FragDenStaat - BImSchG Verfahren",
            "source_type": SourceType.CUSTOM_API,
            "base_url": "https://fragdenstaat.de/api/v1/request/?q=BImSchG+Windenergie",
            "api_endpoint": "https://fragdenstaat.de/api/v1/request/",
            "crawl_config": {
                "api_type": "fragdenstaat",
                "search_query": "BImSchG Windenergie",
                "max_results": 200,
            },
            "extra_data": {"topic": "BImSchG"},
            "priority": 8,
        },
        {
            "name": "FragDenStaat - Erfolgreiche Energie-Anfragen",
            "source_type": SourceType.CUSTOM_API,
            "base_url": "https://fragdenstaat.de/api/v1/request/?q=Windenergie&status=resolved",
            "api_endpoint": "https://fragdenstaat.de/api/v1/request/",
            "crawl_config": {
                "api_type": "fragdenstaat",
                "search_query": "Windenergie",
                "status": "resolved",
                "max_results": 200,
            },
            "extra_data": {"topic": "Windenergie", "filter": "erfolgreich"},
            "priority": 7,
        },
    ],

    # -------------------------------------------------------------------------
    # Standortdaten (GovData)
    # -------------------------------------------------------------------------
    "standortdaten": [
        {
            "name": "GovData - Windenergie Potenzialflächen",
            "source_type": SourceType.CUSTOM_API,
            "base_url": "https://ckan.govdata.de/api/3/action/package_search?q=Windenergie+Potenzial",
            "api_endpoint": "https://ckan.govdata.de/api/3/action/package_search",
            "crawl_config": {
                "api_type": "govdata",
                "search_query": "Windenergie Potenzial Fläche",
                "max_results": 200,
            },
            "extra_data": {"category": "Potenzialflächen"},
            "priority": 10,
        },
        {
            "name": "GovData - Schutzgebiete",
            "source_type": SourceType.CUSTOM_API,
            "base_url": "https://ckan.govdata.de/api/3/action/package_search?q=Naturschutzgebiet+Landschaftsschutz",
            "api_endpoint": "https://ckan.govdata.de/api/3/action/package_search",
            "crawl_config": {
                "api_type": "govdata",
                "search_query": "Naturschutzgebiet Landschaftsschutz Vogelschutz",
                "groups": ["umwelt", "geo"],
                "max_results": 300,
            },
            "extra_data": {"category": "Schutzgebiete"},
            "priority": 9,
        },
        {
            "name": "GovData - Bestandsanlagen Wind",
            "source_type": SourceType.CUSTOM_API,
            "base_url": "https://ckan.govdata.de/api/3/action/package_search?q=Windkraftanlage+Standort",
            "api_endpoint": "https://ckan.govdata.de/api/3/action/package_search",
            "crawl_config": {
                "api_type": "govdata",
                "search_query": "Windkraftanlage Windrad Standort",
                "groups": ["energie"],
                "max_results": 200,
            },
            "extra_data": {"category": "Bestandsanlagen"},
            "priority": 8,
        },
    ],

    # Lead-Qualifizierung hat keine direkten Datenquellen
    # (wird aus anderen Kategorien aggregiert)
    "lead-qualifizierung": [],
}


async def seed_database():
    """Seed the database with example data."""
    print("🌱 Starte Datenbank-Seeding für Sales Intelligence...")
    print("=" * 60)

    async with get_session_context() as session:
        categories_created = 0
        categories_updated = 0
        sources_created = 0

        for cat_data in CATEGORIES:
            # Check if category already exists
            existing = await session.execute(
                select(Category).where(Category.slug == cat_data["slug"])
            )
            existing_cat = existing.scalar()

            if existing_cat:
                # Update existing category
                existing_cat.name = cat_data["name"]
                existing_cat.description = cat_data["description"]
                existing_cat.purpose = cat_data["purpose"]
                existing_cat.search_terms = cat_data["search_terms"]
                existing_cat.ai_extraction_prompt = cat_data["ai_extraction_prompt"]
                existing_cat.schedule_cron = cat_data["schedule_cron"]
                categories_updated += 1
                category = existing_cat
                print(f"  🔄 Kategorie aktualisiert: {cat_data['name']}")
            else:
                # Create new category
                category = Category(
                    name=cat_data["name"],
                    slug=cat_data["slug"],
                    description=cat_data["description"],
                    purpose=cat_data["purpose"],
                    search_terms=cat_data["search_terms"],
                    ai_extraction_prompt=cat_data["ai_extraction_prompt"],
                    schedule_cron=cat_data["schedule_cron"],
                    is_active=True,
                )
                session.add(category)
                await session.flush()
                categories_created += 1
                print(f"  ✅ Kategorie erstellt: {cat_data['name']}")

            # Create data sources for this category
            source_configs = DATA_SOURCES.get(cat_data["slug"], [])
            for src_data in source_configs:
                # Check if source already exists
                existing_src = await session.execute(
                    select(DataSource).where(
                        DataSource.category_id == category.id,
                        DataSource.base_url == src_data["base_url"],
                    )
                )
                if existing_src.scalar():
                    print(f"    ⏭️  Quelle existiert: {src_data['name']}")
                    continue

                source = DataSource(
                    category_id=category.id,
                    name=src_data["name"],
                    source_type=src_data["source_type"],
                    base_url=src_data["base_url"],
                    api_endpoint=src_data.get("api_endpoint"),
                    country=src_data.get("country", "DE"),
                    location_name=src_data.get("location_name"),
                    admin_level_1=src_data.get("admin_level_1"),
                    crawl_config=src_data.get("crawl_config", {}),
                    extra_data=src_data.get("extra_data", {}),
                    priority=src_data.get("priority", 0),
                    status=SourceStatus.ACTIVE,
                )
                session.add(source)
                sources_created += 1
                print(f"    ✅ Quelle erstellt: {src_data['name']}")

        await session.commit()

    print("\n" + "=" * 60)
    print("🎉 Seeding abgeschlossen!")
    print(f"   📁 {categories_created} Kategorien erstellt")
    print(f"   🔄 {categories_updated} Kategorien aktualisiert")
    print(f"   🔗 {sources_created} Datenquellen erstellt")
    print("\n📊 Kategorien-Übersicht:")
    print("   • Ratsinformationen NRW - Kommunale Beschlüsse (OParl)")
    print("   • Kommunale News - Pressemitteilungen & Ankündigungen")
    print("   • Parlamentarische Anfragen - Bundestag/Landtage")
    print("   • IFG-Anfragen - Behördliche Einblicke")
    print("   • Standortdaten - Potenzialflächen & Restriktionen")
    print("   • Lead-Qualifizierung - Aggregierte Bewertung")


async def main():
    """Main entry point."""
    await seed_database()


if __name__ == "__main__":
    asyncio.run(main())
