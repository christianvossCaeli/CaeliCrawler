#!/usr/bin/env python3
"""Full setup: cleanup + smart query prompt."""
import asyncio
import logging
import sys

# Suppress SQL logging
for logger_name in ['sqlalchemy.engine', 'sqlalchemy', 'httpx', 'httpcore']:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

PROMPT = """Ich möchte Windenergie-Projekte und Potenziale für Windflächen in Deutschland analysieren. Dafür brauche ich:

- Alle 16 deutschen Bundesländer mit Einwohnerzahl und Fläche - bitte auch Datenquellen einrichten damit die Zahlen aktuell bleiben
- Alle deutschen Gemeinden, verknüpft mit ihrem jeweiligen Bundesland
- Einen Typ "Windpark" der zu Gemeinden gehört - die Windparks sollen aus der Caeli Auction API importiert und automatisch mit der passenden Gemeinde verknüpft werden
- Für alle sollen die passenden Facetten nutzbar sein

Verknüpfe das Ganze mit den passenden bestehenden Analysethemen.

Kannst du das einrichten?"""

async def main():
    from app.database import get_session, engine
    from sqlalchemy import text
    
    print("=" * 60)
    print("SCHRITT 1: Datenbank bereinigen")
    print("=" * 60)
    
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE data_sources CASCADE"))
        await conn.execute(text("TRUNCATE TABLE entities CASCADE"))
        await conn.execute(text("TRUNCATE TABLE entity_types CASCADE"))
        await conn.execute(text("TRUNCATE TABLE relation_types CASCADE"))
        print("✓ Tabellen bereinigt (außer categories, facet_types)")
        
        result = await conn.execute(text("SELECT count(*) FROM categories"))
        cat_count = result.scalar()
        result = await conn.execute(text("SELECT count(*) FROM facet_types"))
        ft_count = result.scalar()
        print(f"✓ Erhalten: {cat_count} Categories, {ft_count} FacetTypes")
    
    print("\n" + "=" * 60)
    print("SCHRITT 2: Smart Query ausführen")
    print("=" * 60)
    print(f"\nPrompt:\n{PROMPT}\n")
    
    async for session in get_session():
        from services.smart_query import interpret_write_command, execute_write_command
        
        print("2a. AI interpretiert Prompt...")
        command = await interpret_write_command(PROMPT, session)
        
        if not command:
            print("✗ Keine Operation erkannt!")
            return
        
        op = command.get("operation", "none")
        print(f"✓ Operation: {op}")
        
        if command.get("explanation"):
            print(f"   Erklärung: {command.get('explanation')[:200]}")
        
        if op == "combined" and command.get("combined_operations"):
            print(f"   Kombinierte Operationen: {len(command.get('combined_operations'))}")
            for i, sub_op in enumerate(command.get("combined_operations"), 1):
                print(f"   {i}. {sub_op.get('operation')}")
        
        print("\n2b. Führe Operationen aus...")
        result = await execute_write_command(session, command)
        await session.commit()
        
        print(f"\n✓ Ergebnis:")
        print(f"   Success: {result.get('success')}")
        if result.get('message'):
            print(f"   Message: {result.get('message')[:300]}")
        if result.get('created_count'):
            print(f"   Created: {result.get('created_count')}")
        if result.get('results'):
            for r in result.get('results', []):
                status = "✓" if r.get('success', True) else "✗"
                msg = r.get('message', r.get('step_name', 'Unknown'))[:80]
                print(f"   {status} {msg}")
        break
    
    print("\n" + "=" * 60)
    print("SCHRITT 3: Sanity Check")
    print("=" * 60)
    
    async with engine.begin() as conn:
        # Entity Types
        result = await conn.execute(text("""
            SELECT et.slug, et.name, count(e.id) as entity_count
            FROM entity_types et
            LEFT JOIN entities e ON e.entity_type_id = et.id
            GROUP BY et.id, et.slug, et.name
            ORDER BY entity_count DESC
        """))
        print("\nEntity Types:")
        for row in result:
            print(f"  - {row[0]}: {row[1]} ({row[2]} entities)")
        
        # Hierarchy
        result = await conn.execute(text("""
            SELECT 
              CASE WHEN parent_id IS NULL THEN 'Root (Bundesländer)' ELSE 'Children (Gemeinden)' END as level,
              count(*)
            FROM entities
            GROUP BY (parent_id IS NULL)
        """))
        print("\nHierarchie:")
        for row in result:
            print(f"  - {row[0]}: {row[1]}")
        
        # DataSources
        result = await conn.execute(text("SELECT source_type, count(*) FROM data_sources GROUP BY source_type"))
        print("\nDataSources:")
        for row in result:
            print(f"  - {row[0]}: {row[1]}")
        
        # Relations
        result = await conn.execute(text("""
            SELECT rt.name, count(er.id)
            FROM relation_types rt
            LEFT JOIN entity_relations er ON er.relation_type_id = rt.id
            GROUP BY rt.id, rt.name
        """))
        print("\nRelations:")
        for row in result:
            print(f"  - {row[0]}: {row[1]}")
    
    print("\n" + "=" * 60)
    print("FERTIG!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
