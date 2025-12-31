#!/usr/bin/env python3
import asyncio
import logging
import os

# Disable SQL logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
os.environ['SQLALCHEMY_ECHO'] = 'false'

PROMPT = """Ich möchte Windenergie-Projekte und Potenziale für Windflächen in Deutschland analysieren. Dafür brauche ich:

- Alle 16 deutschen Bundesländer mit Einwohnerzahl und Fläche - bitte auch Datenquellen einrichten damit die Zahlen aktuell bleiben
- Alle deutschen Gemeinden, verknüpft mit ihrem jeweiligen Bundesland
- Einen Typ "Windpark" der zu Gemeinden gehört - die Windparks sollen aus der Caeli Auction API importiert und automatisch mit der passenden Gemeinde verknüpft werden
- Für alle sollen die passenden Facetten nutzbar sein

Verknüpfe das Ganze mit den passenden bestehenden Analysethemen.

Kannst du das einrichten?"""

async def main():

    from app.core.database import SessionLocal
    db = SessionLocal()

    try:
        from services.smart_query import SmartQueryService
        service = SmartQueryService(db)


        result = await service.interpret_query(PROMPT)

        for _i, _step in enumerate(result.get('steps', []), 1):
            pass

        if result.get('needs_confirmation'):
            exec_result = await service.execute_steps(result['steps'])
            if exec_result.get('results'):
                for r in exec_result['results']:
                    "✓" if r.get('success') else "✗"
        else:
            pass

    except Exception:
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
