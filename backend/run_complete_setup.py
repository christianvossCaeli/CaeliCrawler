#!/usr/bin/env python3
"""Complete setup via category_setup functions."""

import asyncio

from app.database import get_session
from services.smart_query.category_setup import (
    setup_germany_bundeslaender_category,
    setup_germany_gemeinden_category,
    setup_windpark_category,
)


async def run_setup():
    async for session in get_session():
        # Step 1: Bundesländer
        try:
            await setup_germany_bundeslaender_category(session)
        except Exception:
            import traceback

            traceback.print_exc()

        await session.commit()

        # Step 2: Gemeinden
        try:
            await setup_germany_gemeinden_category(session)
        except Exception:
            import traceback

            traceback.print_exc()

        await session.commit()

        # Step 3: Windparks
        try:
            await setup_windpark_category(session)
        except Exception:
            import traceback

            traceback.print_exc()

        await session.commit()


if __name__ == "__main__":
    asyncio.run(run_setup())
