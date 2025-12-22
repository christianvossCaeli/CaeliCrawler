#!/usr/bin/env python3
import asyncio
import sys
import os
import logging

# Disable SQL logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
os.environ['SQLALCHEMY_ECHO'] = 'false'

PROMPT = """Ich möchte Windenergie-Projekte und Potenziale für Windflächen in Deutschland analysieren. Dafür brauche ich:

- Alle 16 deutschen Bundesländer mit Einwohnerzahl und Fläche - bitte auch Datenquellen einrichten damit die Zahlen aktuell bleiben
- Alle deutschen Gemeinden, verknüpft mit ihrem jeweiligen Bundesland
- Einen Typ "Windpark" der zu Gemeinden gehört - die Windparks sollen aus der Caeli Auction API importiert und automatisch mit der passenden Gemeinde verknüpft werden
- Für alle sollen die passenden Facetten nutzbar sein

Verknüpfe das Ganze mit den passenden bestehenden Analysethemen.

Kannst du das einrichten?"""

async def main():
    print("=" * 60)
    print("Smart Query Import")
    print("=" * 60)
    
    from app.core.database import SessionLocal
    db = SessionLocal()
    
    try:
        from services.smart_query import SmartQueryService
        service = SmartQueryService(db)
        
        print(f"\nPrompt: {PROMPT[:80]}...")
        print("\n1. Interpreting query...")
        
        result = await service.interpret_query(PROMPT)
        
        print(f"   Steps: {len(result.get('steps', []))}")
        for i, step in enumerate(result.get('steps', []), 1):
            print(f"   {i}. {step.get('name', 'Unknown')}")
        
        if result.get('needs_confirmation'):
            print("\n2. Executing steps...")
            exec_result = await service.execute_steps(result['steps'])
            print(f"\n3. Done!")
            print(f"   Success: {exec_result.get('success', False)}")
            if exec_result.get('results'):
                for r in exec_result['results']:
                    status = "✓" if r.get('success') else "✗"
                    print(f"   {status} {r.get('step_name', 'Unknown')}: {r.get('message', '')[:60]}")
        else:
            print(f"\nResult: {result.get('message', str(result))[:200]}")
            
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
