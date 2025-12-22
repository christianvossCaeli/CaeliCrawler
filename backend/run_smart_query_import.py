#!/usr/bin/env python3
"""Full Smart Query import via backend."""
import asyncio
from app.database import get_session
from services.smart_query.query_interpreter import interpret_write_command
from services.smart_query.write_executor import execute_write_command

PROMPT = """Ich möchte Windenergie-Projekte und Potenziale für Windflächen in Deutschland analysieren. Dafür brauche ich:

- Alle 16 deutschen Bundesländer mit Einwohnerzahl und Fläche - bitte auch Datenquellen einrichten damit die Zahlen aktuell bleiben
- Alle deutschen Gemeinden, verknüpft mit ihrem jeweiligen Bundesland
- Einen Typ "Windpark" der zu Gemeinden gehört - die Windparks sollen aus der Caeli Auction API importiert und automatisch mit der passenden Gemeinde verknüpft werden
- Für alle sollen die passenden Facetten nutzbar sein

Verknüpfe das Ganze mit den passenden bestehenden Analysethemen.

Kannst du das einrichten?"""

async def run_import():
    print("=" * 60)
    print("Starting Smart Query Import")
    print("=" * 60)
    
    async for session in get_session():
        # Step 1: Interpret the command
        print("\n1. Interpreting command...")
        interpretation = await interpret_write_command(PROMPT, session)
        
        # Check for combined operations
        if interpretation.get("operation") == "combined":
            operations = interpretation.get("combined_operations", [])
        else:
            operations = [interpretation]
        
        print(f"   Operations planned: {len(operations)}")
        for i, op in enumerate(operations):
            op_type = op.get("operation", "unknown")
            print(f"   - {i+1}. {op_type}")
        
        # Step 2: Execute the operations
        print("\n2. Executing operations...")
        
        total_results = []
        for i, operation in enumerate(operations):
            op_type = operation.get("operation", "unknown")
            print(f"\n   [{i+1}/{len(operations)}] {op_type}...")
            
            try:
                # FIXED: session first, then command
                result = await execute_write_command(session, operation)
                total_results.append(result)
                
                if result.get("success"):
                    created = result.get("created_count", 0)
                    updated = result.get("updated_count", 0)
                    msg = result.get("message", "")[:80]
                    print(f"       Success: {created} created, {updated} updated")
                    if msg:
                        print(f"         {msg}")
                else:
                    error = result.get("error", "Unknown error")
                    print(f"       Failed: {error[:100]}")
            except Exception as e:
                print(f"       Exception: {str(e)[:100]}")
                import traceback
                traceback.print_exc()
        
        await session.commit()
        
        # Summary
        print("\n" + "=" * 60)
        print("IMPORT COMPLETE")
        print("=" * 60)
        
        success_count = sum(1 for r in total_results if r.get("success"))
        print(f"Operations: {success_count}/{len(total_results)} successful")
        
        return total_results

if __name__ == "__main__":
    asyncio.run(run_import())
