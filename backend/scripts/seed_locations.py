#!/usr/bin/env python3
"""
Seed script for international locations (DE + UK).
Creates demo data for testing the location system.
"""
import asyncio
import uuid
from datetime import UTC, datetime

import asyncpg

# Demo data for Germany
DE_LOCATIONS = [
    # Nordrhein-Westfalen
    {"name": "Münster", "admin_level_1": "Nordrhein-Westfalen", "admin_level_2": "Münster", "official_code": "05515000", "population": 317713, "locality_type": "kreisfreie_stadt"},
    {"name": "Greven", "admin_level_1": "Nordrhein-Westfalen", "admin_level_2": "Steinfurt", "official_code": "05566020", "population": 38600, "locality_type": "municipality"},
    {"name": "Emsdetten", "admin_level_1": "Nordrhein-Westfalen", "admin_level_2": "Steinfurt", "official_code": "05566016", "population": 36100, "locality_type": "municipality"},
    {"name": "Telgte", "admin_level_1": "Nordrhein-Westfalen", "admin_level_2": "Warendorf", "official_code": "05570040", "population": 20500, "locality_type": "municipality"},
    {"name": "Köln", "admin_level_1": "Nordrhein-Westfalen", "admin_level_2": "Köln", "official_code": "05315000", "population": 1084000, "locality_type": "kreisfreie_stadt"},
    {"name": "Düsseldorf", "admin_level_1": "Nordrhein-Westfalen", "admin_level_2": "Düsseldorf", "official_code": "05111000", "population": 621877, "locality_type": "kreisfreie_stadt"},
    # Niedersachsen
    {"name": "Hannover", "admin_level_1": "Niedersachsen", "admin_level_2": "Region Hannover", "official_code": "03241001", "population": 536925, "locality_type": "kreisfreie_stadt"},
    {"name": "Osnabrück", "admin_level_1": "Niedersachsen", "admin_level_2": "Osnabrück", "official_code": "03404000", "population": 166000, "locality_type": "kreisfreie_stadt"},
    {"name": "Oldenburg", "admin_level_1": "Niedersachsen", "admin_level_2": "Oldenburg", "official_code": "03403000", "population": 172000, "locality_type": "kreisfreie_stadt"},
    # Bayern
    {"name": "München", "admin_level_1": "Bayern", "admin_level_2": "München", "official_code": "09162000", "population": 1488000, "locality_type": "kreisfreie_stadt"},
    {"name": "Nürnberg", "admin_level_1": "Bayern", "admin_level_2": "Nürnberg", "official_code": "09564000", "population": 523000, "locality_type": "kreisfreie_stadt"},
    # Baden-Württemberg
    {"name": "Stuttgart", "admin_level_1": "Baden-Württemberg", "admin_level_2": "Stuttgart", "official_code": "08111000", "population": 635911, "locality_type": "kreisfreie_stadt"},
    {"name": "Freiburg im Breisgau", "admin_level_1": "Baden-Württemberg", "admin_level_2": "Freiburg im Breisgau", "official_code": "08311000", "population": 236000, "locality_type": "kreisfreie_stadt"},
    # Schleswig-Holstein
    {"name": "Kiel", "admin_level_1": "Schleswig-Holstein", "admin_level_2": "Kiel", "official_code": "01002000", "population": 247000, "locality_type": "kreisfreie_stadt"},
    {"name": "Lübeck", "admin_level_1": "Schleswig-Holstein", "admin_level_2": "Lübeck", "official_code": "01003000", "population": 217000, "locality_type": "kreisfreie_stadt"},
]

# Demo data for UK
UK_LOCATIONS = [
    # England
    {"name": "London", "admin_level_1": "England", "admin_level_2": "Greater London", "official_code": "E12000007", "population": 8982000, "locality_type": "city"},
    {"name": "Manchester", "admin_level_1": "England", "admin_level_2": "Greater Manchester", "official_code": "E08000003", "population": 553230, "locality_type": "city"},
    {"name": "Birmingham", "admin_level_1": "England", "admin_level_2": "West Midlands", "official_code": "E08000025", "population": 1149000, "locality_type": "city"},
    {"name": "Leeds", "admin_level_1": "England", "admin_level_2": "West Yorkshire", "official_code": "E08000035", "population": 793000, "locality_type": "city"},
    {"name": "Bristol", "admin_level_1": "England", "admin_level_2": "Bristol", "official_code": "E06000023", "population": 463400, "locality_type": "city"},
    {"name": "Liverpool", "admin_level_1": "England", "admin_level_2": "Merseyside", "official_code": "E08000012", "population": 498000, "locality_type": "city"},
    {"name": "Newcastle upon Tyne", "admin_level_1": "England", "admin_level_2": "Tyne and Wear", "official_code": "E08000021", "population": 302820, "locality_type": "city"},
    {"name": "Sheffield", "admin_level_1": "England", "admin_level_2": "South Yorkshire", "official_code": "E08000019", "population": 584853, "locality_type": "city"},
    # Scotland
    {"name": "Edinburgh", "admin_level_1": "Scotland", "admin_level_2": "City of Edinburgh", "official_code": "S12000036", "population": 524930, "locality_type": "city"},
    {"name": "Glasgow", "admin_level_1": "Scotland", "admin_level_2": "Glasgow City", "official_code": "S12000049", "population": 633120, "locality_type": "city"},
    {"name": "Aberdeen", "admin_level_1": "Scotland", "admin_level_2": "Aberdeen City", "official_code": "S12000033", "population": 228670, "locality_type": "city"},
    # Wales
    {"name": "Cardiff", "admin_level_1": "Wales", "admin_level_2": "Cardiff", "official_code": "W06000015", "population": 364248, "locality_type": "city"},
    {"name": "Swansea", "admin_level_1": "Wales", "admin_level_2": "Swansea", "official_code": "W06000011", "population": 246500, "locality_type": "city"},
    # Northern Ireland
    {"name": "Belfast", "admin_level_1": "Northern Ireland", "admin_level_2": "Belfast", "official_code": "N09000003", "population": 343542, "locality_type": "city"},
]


def normalize_name(name: str, country: str) -> str:
    """Normalize location name for search."""
    result = name.lower()
    if country == "DE":
        replacements = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}
        for old, new in replacements.items():
            result = result.replace(old, new)
    elif country == "GB":
        result = result.replace("saint ", "st ")
        result = result.replace("-upon-", " upon ")
        result = result.replace("-on-", " on ")
    return result


async def seed_locations():
    """Seed locations into the database."""
    import os
    conn = await asyncpg.connect(
        host=os.environ.get("DB_HOST", "postgres"),
        port=5432,
        user="caelichrawler",
        password=os.environ.get("DB_PASSWORD", "caelichrawler_secret"),
        database="caelichrawler",
    )

    try:
        # Clear existing locations
        await conn.execute("DELETE FROM locations")

        # Insert German locations
        for loc in DE_LOCATIONS:
            await conn.execute(
                """
                INSERT INTO locations (
                    id, country, official_code, name, name_normalized,
                    admin_level_1, admin_level_2, locality_type,
                    country_metadata, population, is_active, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                uuid.uuid4(),
                "DE",
                loc["official_code"],
                loc["name"],
                normalize_name(loc["name"], "DE"),
                loc["admin_level_1"],
                loc["admin_level_2"],
                loc["locality_type"],
                "{}",
                loc["population"],
                True,
                datetime.now(UTC),
                datetime.now(UTC),
            )

        # Insert UK locations
        for loc in UK_LOCATIONS:
            await conn.execute(
                """
                INSERT INTO locations (
                    id, country, official_code, name, name_normalized,
                    admin_level_1, admin_level_2, locality_type,
                    country_metadata, population, is_active, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                uuid.uuid4(),
                "GB",
                loc["official_code"],
                loc["name"],
                normalize_name(loc["name"], "GB"),
                loc["admin_level_1"],
                loc["admin_level_2"],
                loc["locality_type"],
                "{}",
                loc["population"],
                True,
                datetime.now(UTC),
                datetime.now(UTC),
            )

        # Create a demo category
        category_id = uuid.uuid4()
        await conn.execute(
            """
            INSERT INTO categories (
                id, name, slug, description, purpose, ai_extraction_prompt,
                search_terms, document_types, url_include_patterns, url_exclude_patterns,
                schedule_cron, is_active, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            ON CONFLICT (slug) DO NOTHING
            """,
            category_id,
            "Windenergie",
            "windenergie",
            "Dokumente zu Windenergie-Projekten und Genehmigungen",
            "Erfassung von Informationen zu Windenergie-Projekten in Kommunen",
            "Extrahiere Informationen zu Windenergie-Projekten...",
            '["windenergie", "windkraft", "windrad", "windenergieanlage", "windpark"]',
            '["pdf", "html"]',
            '[]',
            '[]',
            "0 6 * * *",
            True,
            datetime.now(UTC),
            datetime.now(UTC),
        )

        # Get the category id (in case it already existed)
        row = await conn.fetchrow("SELECT id FROM categories WHERE slug = 'windenergie'")
        category_id = row["id"]

        # Create some demo data sources
        sources = [
            {"name": "Stadt Münster - Ratsinformationssystem", "location_name": "Münster", "admin_level_1": "Nordrhein-Westfalen", "country": "DE", "url": "https://www.muenster.de/ratsinformationssystem", "type": "OPARL_API"},
            {"name": "Stadt Greven - Bekanntmachungen", "location_name": "Greven", "admin_level_1": "Nordrhein-Westfalen", "country": "DE", "url": "https://www.greven.net/bekanntmachungen", "type": "WEBSITE"},
            {"name": "Stadt Köln - Ratsinformation", "location_name": "Köln", "admin_level_1": "Nordrhein-Westfalen", "country": "DE", "url": "https://ratsinformation.stadt-koeln.de", "type": "OPARL_API"},
            {"name": "Stadt München - Stadtrat", "location_name": "München", "admin_level_1": "Bayern", "country": "DE", "url": "https://www.muenchen.de/rathaus/stadtrat", "type": "WEBSITE"},
            {"name": "Manchester City Council - Planning", "location_name": "Manchester", "admin_level_1": "England", "country": "GB", "url": "https://manchester.gov.uk/planning", "type": "WEBSITE"},
            {"name": "Edinburgh Council - Wind Energy", "location_name": "Edinburgh", "admin_level_1": "Scotland", "country": "GB", "url": "https://edinburgh.gov.uk/windenergy", "type": "WEBSITE"},
            {"name": "London Borough Planning", "location_name": "London", "admin_level_1": "England", "country": "GB", "url": "https://planning.london.gov.uk", "type": "WEBSITE"},
            {"name": "Cardiff Council - Environment", "location_name": "Cardiff", "admin_level_1": "Wales", "country": "GB", "url": "https://cardiff.gov.uk/environment", "type": "WEBSITE"},
        ]

        for src in sources:
            await conn.execute(
                """
                INSERT INTO data_sources (
                    id, category_id, name, source_type, base_url, country,
                    location_name, admin_level_1, crawl_config, extra_data,
                    status, priority, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                """,
                uuid.uuid4(),
                category_id,
                src["name"],
                src["type"],
                src["url"],
                src["country"],
                src["location_name"],
                src["admin_level_1"],
                "{}",
                "{}",
                "ACTIVE",
                1,
                datetime.now(UTC),
                datetime.now(UTC),
            )


    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed_locations())
