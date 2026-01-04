#!/usr/bin/env python3
"""Cleanup DB and run Smart Query."""

import asyncio
import logging

# Suppress SQL logging
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

PROMPT = """Ich möchte Windenergie-Projekte und Potenziale für Windflächen in Deutschland analysieren. Dafür brauche ich:

- Alle 16 deutschen Bundesländer mit Einwohnerzahl und Fläche - bitte auch Datenquellen einrichten damit die Zahlen aktuell bleiben
- Alle deutschen Gemeinden, verknüpft mit ihrem jeweiligen Bundesland
- Einen Typ "Windpark" der zu Gemeinden gehört - die Windparks sollen aus der Caeli Auction API importiert und automatisch mit der passenden Gemeinde verknüpft werden
- Für alle sollen die passenden Facetten nutzbar sein

Verknüpfe das Ganze mit den passenden bestehenden Analysethemen.

Kannst du das einrichten?"""


async def main():
    from sqlalchemy import text

    from app.database import engine, get_session

    async with engine.begin() as conn:
        # Cleanup everything except categories and facet_types
        await conn.execute(text("TRUNCATE TABLE data_sources CASCADE"))
        await conn.execute(text("TRUNCATE TABLE entities CASCADE"))
        await conn.execute(text("TRUNCATE TABLE entity_types CASCADE"))
        await conn.execute(text("TRUNCATE TABLE relation_types CASCADE"))

        # Verify
        result = await conn.execute(text("SELECT count(*) FROM categories"))
        result.scalar()
        result = await conn.execute(text("SELECT count(*) FROM facet_types"))
        result.scalar()

    async for session in get_session():
        from services.smart_query import execute_write_command, interpret_write_command

        command = await interpret_write_command(PROMPT, session)

        if not command or command.get("operation", "none") == "none":
            return

        result = await execute_write_command(session, command)
        await session.commit()

        if result.get("message"):
            pass
        if result.get("created_count"):
            pass
        break


if __name__ == "__main__":
    asyncio.run(main())
