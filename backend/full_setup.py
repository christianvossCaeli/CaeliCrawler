#!/usr/bin/env python3
"""Full setup: cleanup + smart query prompt."""

import asyncio
import logging

# Suppress SQL logging
for logger_name in ["sqlalchemy.engine", "sqlalchemy", "httpx", "httpcore"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

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
        await conn.execute(text("TRUNCATE TABLE data_sources CASCADE"))
        await conn.execute(text("TRUNCATE TABLE entities CASCADE"))
        await conn.execute(text("TRUNCATE TABLE entity_types CASCADE"))
        await conn.execute(text("TRUNCATE TABLE relation_types CASCADE"))

        result = await conn.execute(text("SELECT count(*) FROM categories"))
        result.scalar()
        result = await conn.execute(text("SELECT count(*) FROM facet_types"))
        result.scalar()

    async for session in get_session():
        from services.smart_query import execute_write_command, interpret_write_command

        command = await interpret_write_command(PROMPT, session)

        if not command:
            return

        op = command.get("operation", "none")

        if command.get("explanation"):
            pass

        if op == "combined" and command.get("combined_operations"):
            for _i, _sub_op in enumerate(command.get("combined_operations"), 1):
                pass

        result = await execute_write_command(session, command)
        await session.commit()

        if result.get("message"):
            pass
        if result.get("created_count"):
            pass
        if result.get("results"):
            for r in result.get("results", []):
                "✓" if r.get("success", True) else "✗"
                r.get("message", r.get("step_name", "Unknown"))[:80]
        break

    async with engine.begin() as conn:
        # Entity Types
        result = await conn.execute(
            text("""
            SELECT et.slug, et.name, count(e.id) as entity_count
            FROM entity_types et
            LEFT JOIN entities e ON e.entity_type_id = et.id
            GROUP BY et.id, et.slug, et.name
            ORDER BY entity_count DESC
        """)
        )
        for _row in result:
            pass

        # Hierarchy
        result = await conn.execute(
            text("""
            SELECT
              CASE WHEN parent_id IS NULL THEN 'Root (Bundesländer)' ELSE 'Children (Gemeinden)' END as level,
              count(*)
            FROM entities
            GROUP BY (parent_id IS NULL)
        """)
        )
        for _row in result:
            pass

        # DataSources
        result = await conn.execute(text("SELECT source_type, count(*) FROM data_sources GROUP BY source_type"))
        for _row in result:
            pass

        # Relations
        result = await conn.execute(
            text("""
            SELECT rt.name, count(er.id)
            FROM relation_types rt
            LEFT JOIN entity_relations er ON er.relation_type_id = rt.id
            GROUP BY rt.id, rt.name
        """)
        )
        for _row in result:
            pass


if __name__ == "__main__":
    asyncio.run(main())
