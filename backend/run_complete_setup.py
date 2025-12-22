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
    print("=" * 60)
    print("Complete Setup")
    print("=" * 60)
    
    async for session in get_session():
        # Step 1: Bundesländer
        print("\n1. Setting up Bundesländer...")
        try:
            result = await setup_germany_bundeslaender_category(session)
            print(f"   Success: {result.get('message', '')[:80]}")
            print(f"   Created: {result.get('created_count', 0)} entities")
        except Exception as e:
            print(f"   Error: {str(e)[:100]}")
            import traceback
            traceback.print_exc()
        
        await session.commit()
        
        # Step 2: Gemeinden  
        print("\n2. Setting up Gemeinden...")
        try:
            result = await setup_germany_gemeinden_category(session)
            print(f"   Success: {result.get('message', '')[:80]}")
            print(f"   Created: {result.get('created_count', 0)} entities")
        except Exception as e:
            print(f"   Error: {str(e)[:100]}")
            import traceback
            traceback.print_exc()
        
        await session.commit()
        
        # Step 3: Windparks
        print("\n3. Setting up Windparks...")
        try:
            result = await setup_windpark_category(session)
            print(f"   Success: {result.get('message', '')[:80]}")
            print(f"   Created: {result.get('created_count', 0)} entities")
        except Exception as e:
            print(f"   Error: {str(e)[:100]}")
            import traceback
            traceback.print_exc()
        
        await session.commit()
        
        print("\n" + "=" * 60)
        print("SETUP COMPLETE")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_setup())
