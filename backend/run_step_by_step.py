#!/usr/bin/env python3
"""Step-by-step setup."""

import asyncio

from app.database import get_session
from services.smart_query.write_executor import execute_write_command


async def run_step_by_step():
    async for session in get_session():
        # Step 1: Create territorial-entity type
        op = {
            "operation": "create_entity_type",
            "entity_type_data": {
                "name": "Gebietskörperschaft",
                "name_plural": "Gebietskörperschaften",
                "slug": "territorial-entity",
                "supports_hierarchy": True,
                "is_public": True,
            },
        }
        result = await execute_write_command(session, op)
        await session.commit()

        # Step 2: Import Bundesländer
        op = {
            "operation": "fetch_and_create_from_api",
            "fetch_and_create_data": {
                "api_config": {"type": "sparql", "query": "bundeslaender", "country": "DE"},
                "entity_type": "territorial-entity",
                "create_entity_type": False,
                "hierarchy_level": 1,
                "create_data_sources": True,
            },
        }
        result = await execute_write_command(session, op)
        if not result.get("success"):
            pass
        await session.commit()

        # Step 3: Import Gemeinden
        op = {
            "operation": "fetch_and_create_from_api",
            "fetch_and_create_data": {
                "api_config": {"type": "sparql", "query": "gemeinden", "country": "DE"},
                "entity_type": "territorial-entity",
                "create_entity_type": False,
                "hierarchy_level": 2,
                "parent_field": "bundeslandLabel",
                "create_data_sources": True,
            },
        }
        result = await execute_write_command(session, op)
        if not result.get("success"):
            pass
        await session.commit()

        # Step 4: Create windpark type
        op = {
            "operation": "create_entity_type",
            "entity_type_data": {
                "name": "Windpark",
                "name_plural": "Windparks",
                "slug": "windpark",
                "supports_hierarchy": False,
                "is_public": True,
            },
        }
        result = await execute_write_command(session, op)
        await session.commit()

        # Step 5: Import Windparks
        op = {
            "operation": "fetch_and_create_from_api",
            "fetch_and_create_data": {
                "api_config": {"type": "rest", "template": "caeli_auction_windparks", "country": "DE"},
                "entity_type": "windpark",
                "create_entity_type": False,
                "create_data_sources": True,
                "match_to_gemeinde": True,
            },
        }
        result = await execute_write_command(session, op)
        await session.commit()


if __name__ == "__main__":
    asyncio.run(run_step_by_step())
