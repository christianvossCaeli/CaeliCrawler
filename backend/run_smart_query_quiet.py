#!/usr/bin/env python3
"""Smart Query Import Script - Quiet Version"""
import asyncio
import sys
import logging

# Disable all SQL logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

# Add app to path
sys.path.insert(0, '/app')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

PROMPT = """Ich möchte Windenergie-Projekte und Potenziale für Windflächen in Deutschland analysieren. Dafür brauche ich:

- Alle 16 deutschen Bundesländer mit Einwohnerzahl und Fläche - bitte auch Datenquellen einrichten damit die Zahlen aktuell bleiben
- Alle deutschen Gemeinden, verknüpft mit ihrem jeweiligen Bundesland
- Einen Typ "Windpark" der zu Gemeinden gehört - die Windparks sollen aus der Caeli Auction API importiert und automatisch mit der passenden Gemeinde verknüpft werden
- Für alle sollen die passenden Facetten nutzbar sein

Verknüpfe das Ganze mit den passenden bestehenden Analysethemen.

Kannst du das einrichten?"""

async def main():
    print("=" * 60)
    print("Smart Query Import (Quiet Mode)")
    print("=" * 60)
    
    # Create engine without echo
    engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI), echo=False)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        from services.smart_query import SmartQueryService
        service = SmartQueryService(db)
        
        print(f"\nPrompt: {PROMPT[:100]}...")
        print("\nInterpreting query...")
        
        result = await service.interpret_query(PROMPT)
        
        print(f"\nInterpretation complete.")
        print(f"Steps to execute: {len(result.get('steps', []))}")
        
        if result.get('needs_confirmation'):
            print("\nExecuting steps...")
            exec_result = await service.execute_steps(result['steps'])
            print(f"\nExecution complete!")
            print(f"Success: {exec_result.get('success', False)}")
            if exec_result.get('results'):
                for r in exec_result['results']:
                    print(f"  - {r.get('step_name', 'Unknown')}: {r.get('message', 'No message')}")
        else:
            print(f"\nDirect result: {result}")
            
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
