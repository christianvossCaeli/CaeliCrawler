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
from app.models import Category, DataSource, SourceStatus

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
    # 6. UK WIND ENERGY
    # -------------------------------------------------------------------------
    {
        "name": "UK Wind Planning Applications",
        "slug": "uk-wind-planning",
        "description": "Planning applications and council decisions for wind energy projects in the UK",
        "purpose": """Monitoring UK municipal decisions on wind energy:
- Planning applications for wind farms
- Council decisions and consultations
- Environmental impact assessments
- Community engagement""",
        "search_terms": [
            "wind farm", "wind energy", "wind turbine", "planning application",
            "renewable energy", "onshore wind", "offshore wind",
            "environmental impact", "community benefit", "planning permission",
            "local plan", "energy strategy"
        ],
        "ai_extraction_prompt": """Analyse this UK planning document for wind energy sales intelligence.

EXTRACT IN JSON FORMAT:
{
  "is_relevant": true/false,
  "council": "Name of the council/authority",
  "document_type": "Planning Application|Decision Notice|Consultation|Report",
  "document_date": "YYYY-MM-DD",

  "pain_points": [
    {
      "type": "Community Opposition|Environmental|Visual Impact|Noise|Heritage",
      "description": "Description of the issue",
      "severity": "high|medium|low"
    }
  ],

  "positive_signals": [
    {
      "type": "Planning Approval|Community Support|Climate Policy|Economic Benefits",
      "description": "Description of the positive signal"
    }
  ],

  "decision_makers": [
    {
      "name": "Name",
      "role": "Councillor|Planning Officer|Mayor",
      "stance": "supportive|neutral|opposed"
    }
  ],

  "project_details": {
    "capacity_mw": null,
    "turbine_count": null,
    "status": "Pre-Application|Application|Approved|Refused|Appeal"
  },

  "summary": "Brief summary of the document"
}""",
        "schedule_cron": "0 7 * * *",
    },

    # -------------------------------------------------------------------------
    # 7. ÖSTERREICH WINDENERGIE
    # -------------------------------------------------------------------------
    {
        "name": "Windenergie Österreich",
        "slug": "at-windenergie",
        "description": "UVP-Verfahren und Genehmigungen für Windkraftprojekte in Österreich",
        "purpose": """Monitoring österreichischer Windenergie-Entwicklungen:
- UVP-Verfahren und Bescheide
- Landesregierungs-Entscheidungen
- Bürgerbeteiligung und Einsprüche
- Flächenwidmungen""",
        "search_terms": [
            "Windkraft", "Windenergie", "Windpark", "Windrad",
            "UVP", "Umweltverträglichkeitsprüfung", "Genehmigung",
            "Flächenwidmung", "Raumordnung", "Ökostromanlagen",
            "Energiewende", "Bürgerwindpark", "Repowering"
        ],
        "ai_extraction_prompt": """Analysiere dieses österreichische Dokument für Windenergie Sales Intelligence.

EXTRAHIERE IM JSON-FORMAT:
{
  "is_relevant": true/false,
  "bundesland": "Name des Bundeslandes",
  "gemeinde": "Name der Gemeinde",
  "document_type": "UVP-Bescheid|Genehmigung|Stellungnahme|Antrag",
  "document_date": "YYYY-MM-DD",

  "pain_points": [
    {
      "type": "Bürgerprotest|Naturschutz|Landschaftsschutz|Vogelschutz|Lärm",
      "description": "Beschreibung des Problems",
      "severity": "hoch|mittel|niedrig"
    }
  ],

  "positive_signals": [
    {
      "type": "Genehmigung|Interesse|Bürgerbeteiligung|Klimastrategie",
      "description": "Beschreibung des positiven Signals"
    }
  ],

  "decision_makers": [
    {
      "name": "Name",
      "role": "Bürgermeister|Landesrat|Umweltanwalt",
      "stance": "positiv|neutral|negativ"
    }
  ],

  "project_details": {
    "capacity_mw": null,
    "turbine_count": null,
    "status": "Antrag|Prüfung|Genehmigt|Abgelehnt"
  },

  "summary": "Kurze Zusammenfassung"
}""",
        "schedule_cron": "0 7 * * *",
    },

    # -------------------------------------------------------------------------
    # 8. LEAD-QUALIFIZIERUNG WINDENERGIE (Meta-Kategorie)
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
# DATENQUELLEN - Werden via Smart Query dynamisch hinzugefügt
# =============================================================================
# Die Datenquellen werden nicht mehr hardcoded, sondern via Smart Query
# basierend auf den Category-Eigenschaften (search_terms, purpose) gefunden.

DATA_SOURCES = {
    "ratsinformationen-nrw": [],
    "kommunale-news": [],
    "parlamentarische-anfragen": [],
    "ifg-anfragen": [],
    "standortdaten": [],
    "uk-wind-planning": [],
    "at-windenergie": [],
    "lead-qualifizierung": [],
}


async def seed_database():
    """Seed the database with example data."""

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
                existing_cat.is_public = True  # Always visible in frontend
                categories_updated += 1
                category = existing_cat
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
                    is_public=True,  # Always visible in frontend
                )
                session.add(category)
                await session.flush()
                categories_created += 1

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

        await session.commit()



async def main():
    """Main entry point."""
    await seed_database()


if __name__ == "__main__":
    asyncio.run(main())
