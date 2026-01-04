#!/usr/bin/env python3
"""
Import German locations (Gemeinden) from official data.

Usage:
    docker compose exec backend python scripts/import_locations.py

This imports a curated list of German municipalities for the location dropdown.
"""

import asyncio
import os
import uuid
from datetime import UTC, datetime

import asyncpg

# German municipalities - Format: (AGS, Name, State, District, Population)
LOCATIONS_DATA = [
    # Nordrhein-Westfalen
    ("05314000", "Bonn", "Nordrhein-Westfalen", "Bonn", 336465),
    ("05315000", "Köln", "Nordrhein-Westfalen", "Köln", 1073096),
    ("05316000", "Leverkusen", "Nordrhein-Westfalen", "Leverkusen", 163729),
    ("05111000", "Düsseldorf", "Nordrhein-Westfalen", "Düsseldorf", 619651),
    ("05112000", "Duisburg", "Nordrhein-Westfalen", "Duisburg", 504795),
    ("05113000", "Essen", "Nordrhein-Westfalen", "Essen", 579432),
    ("05114000", "Krefeld", "Nordrhein-Westfalen", "Krefeld", 226844),
    ("05116000", "Mönchengladbach", "Nordrhein-Westfalen", "Mönchengladbach", 268465),
    ("05117000", "Mülheim an der Ruhr", "Nordrhein-Westfalen", "Mülheim an der Ruhr", 170632),
    ("05119000", "Oberhausen", "Nordrhein-Westfalen", "Oberhausen", 210846),
    ("05120000", "Remscheid", "Nordrhein-Westfalen", "Remscheid", 114077),
    ("05122000", "Solingen", "Nordrhein-Westfalen", "Solingen", 159927),
    ("05124000", "Wuppertal", "Nordrhein-Westfalen", "Wuppertal", 359012),
    ("05512000", "Bottrop", "Nordrhein-Westfalen", "Bottrop", 117907),
    ("05513000", "Gelsenkirchen", "Nordrhein-Westfalen", "Gelsenkirchen", 262528),
    ("05515000", "Münster", "Nordrhein-Westfalen", "Münster", 315293),
    ("05711000", "Bielefeld", "Nordrhein-Westfalen", "Bielefeld", 336352),
    ("05911000", "Bochum", "Nordrhein-Westfalen", "Bochum", 365587),
    ("05913000", "Dortmund", "Nordrhein-Westfalen", "Dortmund", 593317),
    ("05914000", "Hagen", "Nordrhein-Westfalen", "Hagen", 188713),
    ("05915000", "Hamm", "Nordrhein-Westfalen", "Hamm", 179397),
    ("05916000", "Herne", "Nordrhein-Westfalen", "Herne", 156621),
    ("05954004", "Gummersbach", "Nordrhein-Westfalen", "Oberbergischer Kreis", 52097),
    ("05362004", "Aachen", "Nordrhein-Westfalen", "Städteregion Aachen", 249070),
    ("05758028", "Paderborn", "Nordrhein-Westfalen", "Paderborn", 155402),
    ("05774032", "Gütersloh", "Nordrhein-Westfalen", "Gütersloh", 100861),
    ("05970040", "Siegen", "Nordrhein-Westfalen", "Siegen-Wittgenstein", 102355),
    # NRW - Additional Municipalities
    ("05566020", "Greven", "Nordrhein-Westfalen", "Steinfurt", 38600),
    ("05566016", "Emsdetten", "Nordrhein-Westfalen", "Steinfurt", 36100),
    ("05570040", "Telgte", "Nordrhein-Westfalen", "Warendorf", 20500),
    ("05562024", "Gronau", "Nordrhein-Westfalen", "Borken", 48000),
    ("05558032", "Rheine", "Nordrhein-Westfalen", "Steinfurt", 76200),
    ("05554008", "Coesfeld", "Nordrhein-Westfalen", "Coesfeld", 36800),
    ("05558004", "Ibbenbüren", "Nordrhein-Westfalen", "Steinfurt", 52000),
    ("05558048", "Steinfurt", "Nordrhein-Westfalen", "Steinfurt", 34100),
    ("05570004", "Ahlen", "Nordrhein-Westfalen", "Warendorf", 53000),
    ("05570008", "Beckum", "Nordrhein-Westfalen", "Warendorf", 37200),
    ("05570044", "Warendorf", "Nordrhein-Westfalen", "Warendorf", 38300),
    # Bayern
    ("09162000", "München", "Bayern", "München", 1487708),
    ("09261000", "Nürnberg", "Bayern", "Nürnberg", 523026),
    ("09462000", "Augsburg", "Bayern", "Augsburg", 304288),
    ("09562000", "Würzburg", "Bayern", "Würzburg", 127934),
    ("09661000", "Regensburg", "Bayern", "Regensburg", 157793),
    ("09362000", "Fürth", "Bayern", "Fürth", 131367),
    ("09564000", "Erlangen", "Bayern", "Erlangen", 116062),
    ("09663000", "Ingolstadt", "Bayern", "Ingolstadt", 138716),
    # Baden-Württemberg
    ("08111000", "Stuttgart", "Baden-Württemberg", "Stuttgart", 632865),
    ("08212000", "Karlsruhe", "Baden-Württemberg", "Karlsruhe", 313092),
    ("08221000", "Heidelberg", "Baden-Württemberg", "Heidelberg", 159245),
    ("08222000", "Mannheim", "Baden-Württemberg", "Mannheim", 313174),
    ("08311000", "Freiburg im Breisgau", "Baden-Württemberg", "Freiburg im Breisgau", 230241),
    ("08421000", "Ulm", "Baden-Württemberg", "Ulm", 126949),
    ("08415000", "Reutlingen", "Baden-Württemberg", "Reutlingen", 115819),
    ("08416000", "Tübingen", "Baden-Württemberg", "Tübingen", 92497),
    ("08115000", "Ludwigsburg", "Baden-Württemberg", "Ludwigsburg", 93779),
    ("08116000", "Esslingen am Neckar", "Baden-Württemberg", "Esslingen", 93542),
    ("08231000", "Pforzheim", "Baden-Württemberg", "Pforzheim", 125957),
    ("08121000", "Heilbronn", "Baden-Württemberg", "Heilbronn", 126592),
    # Hessen
    ("06411000", "Darmstadt", "Hessen", "Darmstadt", 159878),
    ("06412000", "Frankfurt am Main", "Hessen", "Frankfurt am Main", 759224),
    ("06413000", "Offenbach am Main", "Hessen", "Offenbach am Main", 131295),
    ("06414000", "Wiesbaden", "Hessen", "Wiesbaden", 283083),
    ("06611000", "Kassel", "Hessen", "Kassel", 202137),
    ("06531014", "Gießen", "Hessen", "Gießen", 92124),
    ("06534014", "Marburg", "Hessen", "Marburg-Biedenkopf", 77129),
    ("06631009", "Fulda", "Hessen", "Fulda", 69004),
    # Niedersachsen
    ("03241001", "Hannover", "Niedersachsen", "Region Hannover", 545082),
    ("03101000", "Braunschweig", "Niedersachsen", "Braunschweig", 249406),
    ("03102000", "Salzgitter", "Niedersachsen", "Salzgitter", 106604),
    ("03103000", "Wolfsburg", "Niedersachsen", "Wolfsburg", 124452),
    ("03404000", "Osnabrück", "Niedersachsen", "Osnabrück", 166462),
    ("03405000", "Oldenburg", "Niedersachsen", "Oldenburg", 170389),
    ("03402000", "Emden", "Niedersachsen", "Emden", 50607),
    ("03403000", "Wilhelmshaven", "Niedersachsen", "Wilhelmshaven", 78125),
    ("03452012", "Göttingen", "Niedersachsen", "Göttingen", 118911),
    ("03254021", "Hildesheim", "Niedersachsen", "Hildesheim", 101055),
    ("03151012", "Lüneburg", "Niedersachsen", "Lüneburg", 77527),
    ("03351021", "Celle", "Niedersachsen", "Celle", 69748),
    # Schleswig-Holstein
    ("01001000", "Flensburg", "Schleswig-Holstein", "Flensburg", 91113),
    ("01002000", "Kiel", "Schleswig-Holstein", "Kiel", 246794),
    ("01003000", "Lübeck", "Schleswig-Holstein", "Lübeck", 217198),
    ("01004000", "Neumünster", "Schleswig-Holstein", "Neumünster", 81779),
    ("01053042", "Husum", "Schleswig-Holstein", "Nordfriesland", 23202),
    ("01051063", "Heide", "Schleswig-Holstein", "Dithmarschen", 23064),
    ("01061072", "Bad Oldesloe", "Schleswig-Holstein", "Stormarn", 25078),
    ("01062064", "Rendsburg", "Schleswig-Holstein", "Rendsburg-Eckernförde", 28541),
    # Rheinland-Pfalz
    ("07111000", "Koblenz", "Rheinland-Pfalz", "Koblenz", 114052),
    ("07211000", "Trier", "Rheinland-Pfalz", "Trier", 111528),
    ("07312000", "Ludwigshafen am Rhein", "Rheinland-Pfalz", "Ludwigshafen am Rhein", 171061),
    ("07314000", "Mainz", "Rheinland-Pfalz", "Mainz", 220552),
    ("07313000", "Kaiserslautern", "Rheinland-Pfalz", "Kaiserslautern", 100030),
    ("07317000", "Worms", "Rheinland-Pfalz", "Worms", 84048),
    # Sachsen
    ("14612000", "Dresden", "Sachsen", "Dresden", 561922),
    ("14713000", "Leipzig", "Sachsen", "Leipzig", 605407),
    ("14511000", "Chemnitz", "Sachsen", "Chemnitz", 249922),
    ("14522380", "Zwickau", "Sachsen", "Zwickau", 88260),
    ("14729370", "Plauen", "Sachsen", "Vogtlandkreis", 63571),
    # Sachsen-Anhalt
    ("15003000", "Magdeburg", "Sachsen-Anhalt", "Magdeburg", 239364),
    ("15002000", "Halle (Saale)", "Sachsen-Anhalt", "Halle (Saale)", 239257),
    ("15001000", "Dessau-Roßlau", "Sachsen-Anhalt", "Dessau-Roßlau", 80103),
    # Thüringen
    ("16051000", "Erfurt", "Thüringen", "Erfurt", 214969),
    ("16053000", "Jena", "Thüringen", "Jena", 111088),
    ("16052000", "Gera", "Thüringen", "Gera", 93125),
    ("16054000", "Weimar", "Thüringen", "Weimar", 65228),
    ("16055000", "Eisenach", "Thüringen", "Wartburgkreis", 42250),
    # Brandenburg
    ("12054000", "Potsdam", "Brandenburg", "Potsdam", 182112),
    ("12051000", "Brandenburg an der Havel", "Brandenburg", "Brandenburg an der Havel", 72698),
    ("12052000", "Cottbus", "Brandenburg", "Cottbus", 99984),
    ("12053000", "Frankfurt (Oder)", "Brandenburg", "Frankfurt (Oder)", 58537),
    # Mecklenburg-Vorpommern
    ("13003000", "Rostock", "Mecklenburg-Vorpommern", "Rostock", 209191),
    ("13004000", "Schwerin", "Mecklenburg-Vorpommern", "Schwerin", 95653),
    ("13072111", "Stralsund", "Mecklenburg-Vorpommern", "Vorpommern-Rügen", 59106),
    ("13071079", "Greifswald", "Mecklenburg-Vorpommern", "Vorpommern-Greifswald", 59382),
    ("13074132", "Wismar", "Mecklenburg-Vorpommern", "Nordwestmecklenburg", 44246),
    ("13071109", "Neubrandenburg", "Mecklenburg-Vorpommern", "Mecklenburgische Seenplatte", 64086),
    # Saarland
    ("10041100", "Saarbrücken", "Saarland", "Regionalverband Saarbrücken", 181959),
    ("10043115", "Neunkirchen", "Saarland", "Neunkirchen", 47054),
    ("10042111", "Völklingen", "Saarland", "Regionalverband Saarbrücken", 39424),
    ("10044117", "Homburg", "Saarland", "Saarpfalz-Kreis", 42252),
    # Bremen
    ("04011000", "Bremen", "Bremen", "Bremen", 569352),
    ("04012000", "Bremerhaven", "Bremen", "Bremerhaven", 113366),
    # Hamburg
    ("02000000", "Hamburg", "Hamburg", "Hamburg", 1892122),
    # Berlin
    ("11000000", "Berlin", "Berlin", "Berlin", 3677472),
]


def normalize_name(name: str, country: str = "DE") -> str:
    """Normalize location name for search."""
    result = name.lower()
    if country == "DE":
        replacements = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}
        for old, new in replacements.items():
            result = result.replace(old, new)
    return result


async def import_locations():
    """Import locations into the database."""
    conn = await asyncpg.connect(
        host=os.environ.get("DB_HOST", "postgres"),
        port=5432,
        user="caelichrawler",
        password=os.environ.get("DB_PASSWORD", "caelichrawler_secret"),
        database="caelichrawler",
    )

    try:
        # Get existing locations
        existing = await conn.fetch("SELECT official_code FROM locations WHERE country = 'DE'")
        existing_codes = {r["official_code"] for r in existing}

        imported = 0
        skipped = 0

        for ags, name, state, district, population in LOCATIONS_DATA:
            if ags in existing_codes:
                skipped += 1
                continue

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
                ags,
                name,
                normalize_name(name),
                state,
                district,
                "municipality",
                "{}",
                population,
                True,
                datetime.now(UTC),
                datetime.now(UTC),
            )
            imported += 1

    finally:
        await conn.close()


async def main():
    await import_locations()


if __name__ == "__main__":
    asyncio.run(main())
