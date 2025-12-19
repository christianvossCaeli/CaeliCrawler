# Leitfaden: Gemeinden für ein neues Land importieren

## Übersicht

Dieser Leitfaden beschreibt, wie man Gemeinden (Municipalities) für ein neues Land
in das CaeliCrawler-System importiert. Er richtet sich an Entwickler und KI-Agenten,
die ohne zusätzlichen Kontext arbeiten.

## Kritische Regel: Normalisierung

**WICHTIG:** Alle Entity-Namen MÜSSEN mit der zentralen Normalisierungsfunktion
verarbeitet werden. Das Verwenden eigener Normalisierung führt zu Duplikaten!

```python
# RICHTIG - Zentrale Funktion verwenden
from app.utils.text import normalize_entity_name

name_normalized = normalize_entity_name("Wien", country="AT")
# Ergebnis: "wien"

# FALSCH - Eigene Normalisierung schreiben
name_normalized = name.lower().replace(" ", "")  # NIEMALS SO!
```

Siehe auch: `backend/scripts/README_duplicate_cleanup.md`

## Datenmodell

### Entity-Tabelle

Gemeinden werden als `Entity` mit `entity_type.slug = "municipality"` gespeichert:

```python
from app.models import Entity, EntityType

entity = Entity(
    entity_type_id=municipality_type.id,  # EntityType mit slug="municipality"
    name="Wien",                           # Original-Name
    name_normalized="wien",                # Via normalize_entity_name()
    slug="wien",                           # URL-safe, via create_slug()
    external_id="20101",                   # Offizieller Code (z.B. Gemeindekennziffer)
    country="AT",                          # ISO 3166-1 alpha-2
    parent_id=None,                        # Optional: Übergeordnete Entity (z.B. Bundesland)
    core_attributes={                      # Zusätzliche Metadaten
        "population": 1920949,
        "wikidata_id": "Q1741",
    },
    latitude=48.2082,                      # Optional: Koordinaten
    longitude=16.3738,
)
```

### DataSource-Verknüpfung

Nach dem Entity-Import sollten DataSources verknüpft werden:

```python
from app.models import DataSource

# DataSource zu Entity verknüpfen
data_source.entity_id = entity.id
data_source.location_name = entity.name  # Für Legacy-Kompatibilität
```

## Schritt-für-Schritt: Neues Land hinzufügen

### 1. Länderspezifische Normalisierung prüfen/erweitern

Prüfen ob `app/utils/text.py` das Land unterstützt:

```python
# Datei: backend/app/utils/text.py

def normalize_entity_name(name: str, country: str = "DE") -> str:
    result = name.lower()

    # Deutsche Umlaute
    if country == "DE":
        replacements = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}
        for old, new in replacements.items():
            result = result.replace(old, new)

    # UK-spezifisch
    elif country == "GB":
        result = result.replace("saint ", "st ")
        result = result.replace("-upon-", " upon ")

    # Österreich - gleiche Umlaute wie DE
    elif country == "AT":
        replacements = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}
        for old, new in replacements.items():
            result = result.replace(old, new)

    # ... weitere Länder bei Bedarf

    # Diakritische Zeichen entfernen
    result = unicodedata.normalize("NFD", result)
    result = "".join(c for c in result if not unicodedata.combining(c))

    # Nur alphanumerisch
    result = re.sub(r"[^a-z0-9]", "", result)

    return result
```

### 2. Wikidata-Query für das Land erstellen

Beispiel für Österreich:

```sparql
# Österreichische Gemeinden
SELECT DISTINCT
    ?gemeinde
    ?gemeindeLabel
    ?website
    ?gkz              # Gemeindekennziffer (P964)
    ?population
    ?bundeslandLabel
WHERE {
    # Gemeinde in Österreich (Q667509 = municipality of Austria)
    ?gemeinde wdt:P31/wdt:P279* wd:Q667509 .

    # Optional: Website
    OPTIONAL { ?gemeinde wdt:P856 ?website }

    # Gemeindekennziffer (Austrian municipality key)
    OPTIONAL { ?gemeinde wdt:P964 ?gkz }

    # Einwohnerzahl
    OPTIONAL { ?gemeinde wdt:P1082 ?population }

    # Bundesland
    OPTIONAL {
        ?gemeinde wdt:P131* ?bundesland .
        ?bundesland wdt:P31 wd:Q261543 .  # Bundesland Österreichs
    }

    SERVICE wikibase:label { bd:serviceParam wikibase:language "de,en" }
}
ORDER BY ?bundeslandLabel ?gemeindeLabel
```

### 3. Import-Script erstellen

Beispiel: `backend/scripts/import_austrian_municipalities.py`

```python
#!/usr/bin/env python3
"""
Import Austrian municipalities from Wikidata.

Usage:
    docker compose exec backend python -m scripts.import_austrian_municipalities [--dry-run]
"""

import asyncio
import argparse
import httpx
from uuid import UUID
from typing import List, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# WICHTIG: Zentrale Normalisierung verwenden!
from app.utils.text import normalize_entity_name, create_slug
from app.database import async_session_factory
from app.models import Entity, EntityType, DataSource, SourceType, SourceStatus

WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"

# Wikidata-Codes für österreichische Bundesländer
BUNDESLAND_QIDS = {
    "1": "Wien",
    "2": "Niederösterreich",
    "3": "Oberösterreich",
    "4": "Salzburg",
    "5": "Steiermark",
    "6": "Kärnten",
    "7": "Tirol",
    "8": "Vorarlberg",
    "9": "Burgenland",
}

SPARQL_QUERY = """
SELECT DISTINCT ?gemeinde ?gemeindeLabel ?website ?gkz ?population ?bundeslandLabel
WHERE {
    ?gemeinde wdt:P31/wdt:P279* wd:Q667509 .
    OPTIONAL { ?gemeinde wdt:P856 ?website }
    OPTIONAL { ?gemeinde wdt:P964 ?gkz }
    OPTIONAL { ?gemeinde wdt:P1082 ?population }
    OPTIONAL {
        ?gemeinde wdt:P131* ?bundesland .
        ?bundesland wdt:P31 wd:Q261543 .
    }
    SERVICE wikibase:label { bd:serviceParam wikibase:language "de,en" }
}
ORDER BY ?gemeindeLabel
"""


async def fetch_municipalities() -> List[Dict]:
    """Fetch Austrian municipalities from Wikidata."""
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.get(
            WIKIDATA_ENDPOINT,
            params={"query": SPARQL_QUERY, "format": "json"},
            headers={"User-Agent": "CaeliCrawler/1.0"}
        )
        response.raise_for_status()
        data = response.json()

    results = []
    seen = set()

    for binding in data.get("results", {}).get("bindings", []):
        name = binding.get("gemeindeLabel", {}).get("value", "")
        if not name or name in seen:
            continue
        seen.add(name)

        results.append({
            "wikidata_id": binding.get("gemeinde", {}).get("value", "").split("/")[-1],
            "name": name,
            "website": binding.get("website", {}).get("value"),
            "gkz": binding.get("gkz", {}).get("value"),
            "population": binding.get("population", {}).get("value"),
            "bundesland": binding.get("bundeslandLabel", {}).get("value"),
        })

    return results


async def import_entities(municipalities: List[Dict], dry_run: bool = False) -> Dict:
    """Import municipalities as entities."""
    stats = {"created": 0, "skipped": 0, "errors": 0}

    if dry_run:
        print(f"[DRY RUN] Would import {len(municipalities)} municipalities")
        return stats

    async with async_session_factory() as session:
        # EntityType holen
        result = await session.execute(
            select(EntityType).where(EntityType.slug == "municipality")
        )
        entity_type = result.scalar_one_or_none()
        if not entity_type:
            print("ERROR: EntityType 'municipality' not found!")
            return stats

        for muni in municipalities:
            try:
                # WICHTIG: Zentrale Normalisierung!
                name_normalized = normalize_entity_name(muni["name"], country="AT")

                # Prüfen ob bereits existiert
                existing = await session.execute(
                    select(Entity).where(
                        Entity.entity_type_id == entity_type.id,
                        Entity.name_normalized == name_normalized,
                        Entity.country == "AT",
                    )
                )
                if existing.scalar_one_or_none():
                    stats["skipped"] += 1
                    continue

                # Neue Entity erstellen
                entity = Entity(
                    entity_type_id=entity_type.id,
                    name=muni["name"],
                    name_normalized=name_normalized,
                    slug=create_slug(muni["name"], country="AT"),
                    external_id=muni.get("gkz"),  # Gemeindekennziffer
                    country="AT",
                    core_attributes={
                        "wikidata_id": muni.get("wikidata_id"),
                        "population": int(float(muni["population"])) if muni.get("population") else None,
                        "admin_level_1": muni.get("bundesland"),
                    },
                )
                session.add(entity)
                await session.flush()

                # Optional: DataSource erstellen wenn Website vorhanden
                if muni.get("website"):
                    # Prüfen ob DataSource schon existiert
                    ds_existing = await session.execute(
                        select(DataSource).where(DataSource.base_url == muni["website"])
                    )
                    if not ds_existing.scalar_one_or_none():
                        # Hinweis: category_id muss noch ermittelt werden
                        pass

                stats["created"] += 1

                if stats["created"] % 100 == 0:
                    print(f"  Created {stats['created']} entities...")
                    await session.commit()

            except Exception as e:
                print(f"  Error importing {muni['name']}: {e}")
                stats["errors"] += 1

        await session.commit()

    return stats


async def main():
    parser = argparse.ArgumentParser(description="Import Austrian municipalities")
    parser.add_argument("--dry-run", "-n", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("Austrian Municipality Import")
    print("=" * 60)

    municipalities = await fetch_municipalities()
    print(f"Found {len(municipalities)} municipalities in Wikidata")

    stats = await import_entities(municipalities, dry_run=args.dry_run)

    print("\nResults:")
    print(f"  Created: {stats['created']}")
    print(f"  Skipped: {stats['skipped']}")
    print(f"  Errors: {stats['errors']}")


if __name__ == "__main__":
    asyncio.run(main())
```

### 4. Nach dem Import: Duplikat-Check

```bash
# Prüfen ob Duplikate entstanden sind
docker compose exec backend python -m scripts.cleanup_duplicate_municipalities --country AT --dry-run
```

## Wikidata-Referenz: Offizielle Gemeinde-Codes

| Land | Property | Bezeichnung | Beispiel |
|------|----------|-------------|----------|
| DE | P439 | AGS (Amtlicher Gemeindeschlüssel) | "05315000" (Köln) |
| AT | P964 | Gemeindekennziffer | "90001" (Wien) |
| CH | P771 | Gemeindenummer (BFS) | "261" (Zürich) |
| GB | P836 | GSS code | "E09000001" |
| FR | P374 | Code INSEE | "75056" (Paris) |
| IT | P635 | Codice ISTAT | "001272" (Turin) |

## Wikidata-Referenz: Gemeinde-Typen (P31)

| Land | QID | Bezeichnung |
|------|-----|-------------|
| DE | Q262166 | municipality of Germany |
| AT | Q667509 | municipality of Austria |
| CH | Q70208 | municipality of Switzerland |
| GB | Q1115575 | civil parish (England) |
| FR | Q484170 | commune of France |

## Checkliste für neue Länder

- [ ] `app/utils/text.py` - Länderspezifische Normalisierung hinzugefügt?
- [ ] Wikidata-Query getestet? (https://query.wikidata.org/)
- [ ] Import-Script erstellt und `--dry-run` getestet?
- [ ] Nach Import: Duplikat-Check durchgeführt?
- [ ] DataSources mit Entities verknüpft?

## Fehlerbehebung

### Duplikate nach Import

Ursache: Verschiedene Normalisierungsmethoden verwendet.
Lösung: `cleanup_duplicate_municipalities.py` ausführen.

### Entity nicht gefunden beim DataSource-Linking

```python
# Debugging: Normalisierte Namen vergleichen
from app.utils.text import normalize_entity_name

print(normalize_entity_name("Wien", "AT"))  # -> "wien"
print(normalize_entity_name("Wien", "DE"))  # -> "wien" (gleich für AT/DE)
```

### Wikidata-Query gibt keine Ergebnisse

1. QID für Gemeinde-Typ prüfen (P31)
2. Query auf https://query.wikidata.org/ testen
3. Timeout erhöhen bei vielen Ergebnissen

## Dateien-Übersicht

| Datei | Zweck |
|-------|-------|
| `app/utils/text.py` | Zentrale Normalisierung |
| `services/entity_facet_service.py` | get_or_create_entity() Funktion |
| `scripts/import_wikidata_gemeinden.py` | DE-Import (Referenz) |
| `scripts/import_wikidata_uk.py` | UK-Import (Referenz) |
| `scripts/cleanup_duplicate_municipalities.py` | Duplikat-Bereinigung |
