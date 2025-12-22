#!/usr/bin/env python3
"""Step-by-step setup."""
import asyncio
from app.database import get_session
from services.smart_query.write_executor import execute_write_command

async def run_step_by_step():
    print("=" * 60)
    print("Step-by-Step Setup")
    print("=" * 60)
    
    async for session in get_session():
        # Step 1: Create territorial-entity type
        print("\n1. Creating territorial-entity type...")
        op = {
            "operation": "create_entity_type",
            "entity_type_data": {
                "name": "Gebietskörperschaft",
                "name_plural": "Gebietskörperschaften",
                "slug": "territorial-entity",
                "supports_hierarchy": True,
                "is_public": True
            }
        }
        result = await execute_write_command(session, op)
        print(f"   Success: {result.get('success')}, Message: {result.get('message', '')[:80]}")
        await session.commit()
        
        # Step 2: Import Bundesländer
        print("\n2. Importing Bundesländer...")
        op = {
            "operation": "fetch_and_create_from_api",
            "fetch_and_create_data": {
                "api_config": {"type": "sparql", "query": "bundeslaender", "country": "DE"},
                "entity_type": "territorial-entity",
                "create_entity_type": False,
                "hierarchy_level": 1,
                "create_data_sources": True
            }
        }
        result = await execute_write_command(session, op)
        print(f"   Created: {result.get('created_count', 0)}, Success: {result.get('success')}")
        if not result.get("success"):
            print(f"   Error: {result.get('error', result.get('message', ''))[:200]}")
        await session.commit()
        
        # Step 3: Import Gemeinden
        print("\n3. Importing Gemeinden (this may take a while)...")
        op = {
            "operation": "fetch_and_create_from_api",
            "fetch_and_create_data": {
                "api_config": {"type": "sparql", "query": "gemeinden", "country": "DE"},
                "entity_type": "territorial-entity",
                "create_entity_type": False,
                "hierarchy_level": 2,
                "parent_field": "bundeslandLabel",
                "create_data_sources": True
            }
        }
        result = await execute_write_command(session, op)
        print(f"   Created: {result.get('created_count', 0)}, Success: {result.get('success')}")
        if not result.get("success"):
            print(f"   Error: {result.get('error', result.get('message', ''))[:200]}")
        await session.commit()
        
        # Step 4: Create windpark type
        print("\n4. Creating windpark type...")
        op = {
            "operation": "create_entity_type",
            "entity_type_data": {
                "name": "Windpark",
                "name_plural": "Windparks",
                "slug": "windpark",
                "supports_hierarchy": False,
                "is_public": True
            }
        }
        result = await execute_write_command(session, op)
        print(f"   Success: {result.get('success')}, Message: {result.get('message', '')[:80]}")
        await session.commit()
        
        # Step 5: Import Windparks
        print("\n5. Importing Windparks from Caeli API...")
        op = {
            "operation": "fetch_and_create_from_api",
            "fetch_and_create_data": {
                "api_config": {"type": "rest", "template": "caeli_auction_windparks", "country": "DE"},
                "entity_type": "windpark",
                "create_entity_type": False,
                "create_data_sources": True,
                "match_to_gemeinde": True
            }
        }
        result = await execute_write_command(session, op)
        print(f"   Created: {result.get('created_count', 0)}, Success: {result.get('success')}")
        await session.commit()
        
        print("\n" + "=" * 60)
        print("DONE")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_step_by_step())
