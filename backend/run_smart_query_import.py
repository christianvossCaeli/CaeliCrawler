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
    async for session in get_session():
        # Step 1: Interpret the command
        interpretation = await interpret_write_command(PROMPT, session)

        # Check for combined operations
        if interpretation.get("operation") == "combined":
            operations = interpretation.get("combined_operations", [])
        else:
            operations = [interpretation]

        for _i, op in enumerate(operations):
            op.get("operation", "unknown")

        # Step 2: Execute the operations

        total_results = []
        for _i, operation in enumerate(operations):
            operation.get("operation", "unknown")

            try:
                # FIXED: session first, then command
                result = await execute_write_command(session, operation)
                total_results.append(result)

                if result.get("success"):
                    result.get("created_count", 0)
                    result.get("updated_count", 0)
                    msg = result.get("message", "")[:80]
                    if msg:
                        pass
                else:
                    result.get("error", "Unknown error")
            except Exception:
                import traceback

                traceback.print_exc()

        await session.commit()

        # Summary

        sum(1 for r in total_results if r.get("success"))

        return total_results


if __name__ == "__main__":
    asyncio.run(run_import())
