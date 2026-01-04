#!/usr/bin/env python3
"""Smart Query Import Script - Quiet Version"""

import asyncio
import logging
import sys

# Disable all SQL logging
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

# Add app to path
sys.path.insert(0, "/app")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.config import settings  # noqa: E402

PROMPT = """Ich möchte Windenergie-Projekte und Potenziale für Windflächen in Deutschland analysieren. Dafür brauche ich:

- Alle 16 deutschen Bundesländer mit Einwohnerzahl und Fläche - bitte auch Datenquellen einrichten damit die Zahlen aktuell bleiben
- Alle deutschen Gemeinden, verknüpft mit ihrem jeweiligen Bundesland
- Einen Typ "Windpark" der zu Gemeinden gehört - die Windparks sollen aus der Caeli Auction API importiert und automatisch mit der passenden Gemeinde verknüpft werden
- Für alle sollen die passenden Facetten nutzbar sein

Verknüpfe das Ganze mit den passenden bestehenden Analysethemen.

Kannst du das einrichten?"""


async def main():
    # Create engine without echo
    engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI), echo=False)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        from services.smart_query import SmartQueryService

        service = SmartQueryService(db)

        result = await service.interpret_query(PROMPT)

        if result.get("needs_confirmation"):
            exec_result = await service.execute_steps(result["steps"])
            if exec_result.get("results"):
                for _r in exec_result["results"]:
                    pass
        else:
            pass

    except Exception:
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
