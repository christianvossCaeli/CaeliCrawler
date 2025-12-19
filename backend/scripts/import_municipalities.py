#!/usr/bin/env python3
"""
Import German municipalities (Gemeinden) from official data.

Usage:
    docker compose exec backend python scripts/import_municipalities.py

Sources:
- Uses a subset of commonly relevant municipalities for wind energy projects
- Can be extended with full Destatis GV100 data
"""

import asyncio
import sys
import uuid
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.municipality import Municipality


# Sample of German municipalities - can be extended with full GV100 data
# Format: (AGS, Name, State, District, Population)
MUNICIPALITIES_DATA = [
    # Nordrhein-Westfalen
    ("05314000", "Bonn", "Nordrhein-Westfalen", "Bonn, Stadt", 336465),
    ("05315000", "Köln", "Nordrhein-Westfalen", "Köln, Stadt", 1073096),
    ("05316000", "Leverkusen", "Nordrhein-Westfalen", "Leverkusen, Stadt", 163729),
    ("05111000", "Düsseldorf", "Nordrhein-Westfalen", "Düsseldorf, Stadt", 619651),
    ("05112000", "Duisburg", "Nordrhein-Westfalen", "Duisburg, Stadt", 504795),
    ("05113000", "Essen", "Nordrhein-Westfalen", "Essen, Stadt", 579432),
    ("05114000", "Krefeld", "Nordrhein-Westfalen", "Krefeld, Stadt", 226844),
    ("05116000", "Mönchengladbach", "Nordrhein-Westfalen", "Mönchengladbach, Stadt", 268465),
    ("05117000", "Mülheim an der Ruhr", "Nordrhein-Westfalen", "Mülheim an der Ruhr, Stadt", 170632),
    ("05119000", "Oberhausen", "Nordrhein-Westfalen", "Oberhausen, Stadt", 210846),
    ("05120000", "Remscheid", "Nordrhein-Westfalen", "Remscheid, Stadt", 114077),
    ("05122000", "Solingen", "Nordrhein-Westfalen", "Solingen, Stadt", 159927),
    ("05124000", "Wuppertal", "Nordrhein-Westfalen", "Wuppertal, Stadt", 359012),
    ("05512000", "Bottrop", "Nordrhein-Westfalen", "Bottrop, Stadt", 117907),
    ("05513000", "Gelsenkirchen", "Nordrhein-Westfalen", "Gelsenkirchen, Stadt", 262528),
    ("05515000", "Münster", "Nordrhein-Westfalen", "Münster, Stadt", 315293),
    ("05711000", "Bielefeld", "Nordrhein-Westfalen", "Bielefeld, Stadt", 336352),
    ("05911000", "Bochum", "Nordrhein-Westfalen", "Bochum, Stadt", 365587),
    ("05913000", "Dortmund", "Nordrhein-Westfalen", "Dortmund, Stadt", 593317),
    ("05914000", "Hagen", "Nordrhein-Westfalen", "Hagen, Stadt", 188713),
    ("05915000", "Hamm", "Nordrhein-Westfalen", "Hamm, Stadt", 179397),
    ("05916000", "Herne", "Nordrhein-Westfalen", "Herne, Stadt", 156621),
    ("05954004", "Gummersbach", "Nordrhein-Westfalen", "Oberbergischer Kreis", 52097),
    ("05362004", "Aachen", "Nordrhein-Westfalen", "Städteregion Aachen", 249070),
    ("05758028", "Paderborn", "Nordrhein-Westfalen", "Paderborn", 155402),
    ("05774032", "Gütersloh", "Nordrhein-Westfalen", "Gütersloh", 100861),
    ("05970040", "Siegen", "Nordrhein-Westfalen", "Siegen-Wittgenstein", 102355),

    # Bayern
    ("09162000", "München", "Bayern", "München, Stadt", 1487708),
    ("09261000", "Nürnberg", "Bayern", "Nürnberg, Stadt", 523026),
    ("09462000", "Augsburg", "Bayern", "Augsburg, Stadt", 304288),
    ("09562000", "Würzburg", "Bayern", "Würzburg, Stadt", 127934),
    ("09661000", "Regensburg", "Bayern", "Regensburg, Stadt", 157793),
    ("09362000", "Fürth", "Bayern", "Fürth, Stadt", 131367),
    ("09564000", "Erlangen", "Bayern", "Erlangen, Stadt", 116062),
    ("09663000", "Ingolstadt", "Bayern", "Ingolstadt, Stadt", 138716),

    # Baden-Württemberg
    ("08111000", "Stuttgart", "Baden-Württemberg", "Stuttgart, Stadt", 632865),
    ("08212000", "Karlsruhe", "Baden-Württemberg", "Karlsruhe, Stadt", 313092),
    ("08221000", "Heidelberg", "Baden-Württemberg", "Heidelberg, Stadt", 159245),
    ("08222000", "Mannheim", "Baden-Württemberg", "Mannheim, Stadt", 313174),
    ("08311000", "Freiburg im Breisgau", "Baden-Württemberg", "Freiburg im Breisgau, Stadt", 230241),
    ("08421000", "Ulm", "Baden-Württemberg", "Ulm, Stadt", 126949),
    ("08415000", "Reutlingen", "Baden-Württemberg", "Reutlingen", 115819),
    ("08416000", "Tübingen", "Baden-Württemberg", "Tübingen", 92497),
    ("08115000", "Ludwigsburg", "Baden-Württemberg", "Ludwigsburg", 93779),
    ("08116000", "Esslingen am Neckar", "Baden-Württemberg", "Esslingen", 93542),
    ("08231000", "Pforzheim", "Baden-Württemberg", "Pforzheim, Stadt", 125957),
    ("08121000", "Heilbronn", "Baden-Württemberg", "Heilbronn, Stadt", 126592),

    # Hessen
    ("06411000", "Darmstadt", "Hessen", "Darmstadt, Stadt", 159878),
    ("06412000", "Frankfurt am Main", "Hessen", "Frankfurt am Main, Stadt", 759224),
    ("06413000", "Offenbach am Main", "Hessen", "Offenbach am Main, Stadt", 131295),
    ("06414000", "Wiesbaden", "Hessen", "Wiesbaden, Stadt", 283083),
    ("06611000", "Kassel", "Hessen", "Kassel, Stadt", 202137),
    ("06531014", "Gießen", "Hessen", "Gießen", 92124),
    ("06534014", "Marburg", "Hessen", "Marburg-Biedenkopf", 77129),
    ("06631009", "Fulda", "Hessen", "Fulda", 69004),

    # Niedersachsen
    ("03241001", "Hannover", "Niedersachsen", "Region Hannover", 545082),
    ("03101000", "Braunschweig", "Niedersachsen", "Braunschweig, Stadt", 249406),
    ("03102000", "Salzgitter", "Niedersachsen", "Salzgitter, Stadt", 106604),
    ("03103000", "Wolfsburg", "Niedersachsen", "Wolfsburg, Stadt", 124452),
    ("03404000", "Osnabrück", "Niedersachsen", "Osnabrück, Stadt", 166462),
    ("03405000", "Oldenburg", "Niedersachsen", "Oldenburg, Stadt", 170389),
    ("03402000", "Emden", "Niedersachsen", "Emden, Stadt", 50607),
    ("03403000", "Wilhelmshaven", "Niedersachsen", "Wilhelmshaven, Stadt", 78125),
    ("03452012", "Göttingen", "Niedersachsen", "Göttingen", 118911),
    ("03254021", "Hildesheim", "Niedersachsen", "Hildesheim", 101055),
    ("03151012", "Lüneburg", "Niedersachsen", "Lüneburg", 77527),
    ("03351021", "Celle", "Niedersachsen", "Celle", 69748),

    # Schleswig-Holstein
    ("01001000", "Flensburg", "Schleswig-Holstein", "Flensburg, Stadt", 91113),
    ("01002000", "Kiel", "Schleswig-Holstein", "Kiel, Stadt", 246794),
    ("01003000", "Lübeck", "Schleswig-Holstein", "Lübeck, Stadt", 217198),
    ("01004000", "Neumünster", "Schleswig-Holstein", "Neumünster, Stadt", 81779),
    ("01053042", "Husum", "Schleswig-Holstein", "Nordfriesland", 23202),
    ("01051063", "Heide", "Schleswig-Holstein", "Dithmarschen", 23064),
    ("01061072", "Bad Oldesloe", "Schleswig-Holstein", "Stormarn", 25078),
    ("01062064", "Rendsburg", "Schleswig-Holstein", "Rendsburg-Eckernförde", 28541),

    # Rheinland-Pfalz
    ("07111000", "Koblenz", "Rheinland-Pfalz", "Koblenz, Stadt", 114052),
    ("07211000", "Trier", "Rheinland-Pfalz", "Trier, Stadt", 111528),
    ("07312000", "Ludwigshafen am Rhein", "Rheinland-Pfalz", "Ludwigshafen am Rhein, Stadt", 171061),
    ("07314000", "Mainz", "Rheinland-Pfalz", "Mainz, Stadt", 220552),
    ("07313000", "Kaiserslautern", "Rheinland-Pfalz", "Kaiserslautern, Stadt", 100030),
    ("07317000", "Worms", "Rheinland-Pfalz", "Worms, Stadt", 84048),

    # Sachsen
    ("14612000", "Dresden", "Sachsen", "Dresden, Stadt", 561922),
    ("14713000", "Leipzig", "Sachsen", "Leipzig, Stadt", 605407),
    ("14511000", "Chemnitz", "Sachsen", "Chemnitz, Stadt", 249922),
    ("14522380", "Zwickau", "Sachsen", "Zwickau", 88260),
    ("14729370", "Plauen", "Sachsen", "Vogtlandkreis", 63571),

    # Sachsen-Anhalt
    ("15003000", "Magdeburg", "Sachsen-Anhalt", "Magdeburg, Stadt", 239364),
    ("15002000", "Halle (Saale)", "Sachsen-Anhalt", "Halle (Saale), Stadt", 239257),
    ("15001000", "Dessau-Roßlau", "Sachsen-Anhalt", "Dessau-Roßlau, Stadt", 80103),

    # Thüringen
    ("16051000", "Erfurt", "Thüringen", "Erfurt, Stadt", 214969),
    ("16053000", "Jena", "Thüringen", "Jena, Stadt", 111088),
    ("16052000", "Gera", "Thüringen", "Gera, Stadt", 93125),
    ("16054000", "Weimar", "Thüringen", "Weimar, Stadt", 65228),
    ("16055000", "Eisenach", "Thüringen", "Wartburgkreis", 42250),

    # Brandenburg
    ("12054000", "Potsdam", "Brandenburg", "Potsdam, Stadt", 182112),
    ("12051000", "Brandenburg an der Havel", "Brandenburg", "Brandenburg an der Havel, Stadt", 72698),
    ("12052000", "Cottbus", "Brandenburg", "Cottbus, Stadt", 99984),
    ("12053000", "Frankfurt (Oder)", "Brandenburg", "Frankfurt (Oder), Stadt", 58537),

    # Mecklenburg-Vorpommern
    ("13003000", "Rostock", "Mecklenburg-Vorpommern", "Rostock, Stadt", 209191),
    ("13004000", "Schwerin", "Mecklenburg-Vorpommern", "Schwerin, Stadt", 95653),
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
    ("04011000", "Bremen", "Bremen", "Bremen, Stadt", 569352),
    ("04012000", "Bremerhaven", "Bremen", "Bremerhaven, Stadt", 113366),

    # Hamburg
    ("02000000", "Hamburg", "Hamburg", "Hamburg", 1892122),

    # Berlin
    ("11000000", "Berlin", "Berlin", "Berlin", 3677472),
]


async def import_municipalities():
    """Import municipalities into the database."""
    async with async_session_factory() as session:
        # Check existing count
        result = await session.execute(select(Municipality))
        existing = result.scalars().all()
        existing_ags = {m.ags for m in existing}

        print(f"Found {len(existing)} existing municipalities")

        imported = 0
        skipped = 0

        for ags, name, state, district, population in MUNICIPALITIES_DATA:
            if ags in existing_ags:
                skipped += 1
                continue

            municipality = Municipality(
                id=uuid.uuid4(),
                ags=ags,
                name=name,
                name_normalized=Municipality.normalize_name(name),
                state=state,
                district=district,
                population=population,
                is_active=True,
            )
            session.add(municipality)
            imported += 1

        await session.commit()

        print(f"Imported {imported} new municipalities")
        print(f"Skipped {skipped} existing municipalities")
        print(f"Total municipalities: {len(existing) + imported}")


async def main():
    print("Starting municipality import...")
    await import_municipalities()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
