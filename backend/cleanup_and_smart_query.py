#!/usr/bin/env python3
"""Cleanup DB and run Smart Query."""
import asyncio
import logging

# Suppress SQL logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

PROMPT = """Ich möchte Windenergie-Projekte und Potenziale für Windflächen in Deutschland analysieren. Dafür brauche ich:

- Alle 16 deutschen Bundesländer mit Einwohnerzahl und Fläche - bitte auch Datenquellen einrichten damit die Zahlen aktuell bleiben
- Alle deutschen Gemeinden, verknüpft mit ihrem jeweiligen Bundesland
- Einen Typ "Windpark" der zu Gemeinden gehört - die Windparks sollen aus der Caeli Auction API importiert und automatisch mit der passenden Gemeinde verknüpft werden
- Für alle sollen die passenden Facetten nutzbar sein

Verknüpfe das Ganze mit den passenden bestehenden Analysethemen.

Kannst du das einrichten?"""

async def main():
    print("=" * 60)
    print("STEP 1: Cleanup Database")
    print("=" * 60)
    
    from app.database import get_session, engine
    from sqlalchemy import text
    
    async with engine.begin() as conn:
        # Cleanup everything except categories and facet_types
        await conn.execute(text("TRUNCATE TABLE data_sources CASCADE"))
        await conn.execute(text("TRUNCATE TABLE entities CASCADE"))
        await conn.execute(text("TRUNCATE TABLE entity_types CASCADE"))
        await conn.execute(text("TRUNCATE TABLE relation_types CASCADE"))
        print("✓ Truncated: data_sources, entities, entity_types, relation_types")
        
        # Verify
        result = await conn.execute(text("SELECT count(*) FROM categories"))
        cat_count = result.scalar()
        result = await conn.execute(text("SELECT count(*) FROM facet_types"))
        ft_count = result.scalar()
        print(f"✓ Preserved: {cat_count} categories, {ft_count} facet_types")
    
    print("\n" + "=" * 60)
    print("STEP 2: Run Smart Query")
    print("=" * 60)
    print(f"\nPrompt: {PROMPT[:80]}...")
    
    async for session in get_session():
        from services.smart_query import interpret_write_command, execute_write_command
        
        print("\n2a. Interpreting command...")
        command = await interpret_write_command(PROMPT, session)
        
        if not command or command.get("operation", "none") == "none":
            print(f"✗ No operation recognized: {command}")
            return
        
        print(f"✓ Operation: {command.get('operation')}")
        
        print("\n2b. Executing command...")
        result = await execute_write_command(session, command)
        await session.commit()
        
        print(f"\n✓ Result: success={result.get('success')}")
        if result.get('message'):
            print(f"  Message: {result.get('message')[:200]}")
        if result.get('created_count'):
            print(f"  Created: {result.get('created_count')}")
        break
    
    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
