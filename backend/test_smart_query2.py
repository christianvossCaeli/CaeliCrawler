#!/usr/bin/env python3
"""Full Smart Query test via backend."""
import asyncio
from app.database import get_session
from services.smart_query import interpret_write_command, execute_write_command

async def test():
    async for session in get_session():
        prompt = """Ich möchte Windenergie-Projekte und Potenziale für Windflächen in Deutschland analysieren. Dafür brauche ich:

- Alle 16 deutschen Bundesländer mit Einwohnerzahl und Fläche - bitte auch Datenquellen einrichten damit die Zahlen aktuell bleiben
- Alle deutschen Gemeinden, verknüpft mit ihrem jeweiligen Bundesland
- Einen Typ "Windpark" der zu Gemeinden gehört - die Windparks sollen aus der Caeli Auction API importiert und automatisch mit der passenden Gemeinde verknüpft werden
- Für alle sollen die passenden Facetten nutzbar sein

Kannst du das einrichten?"""

        print("Testing Smart Query with natural language prompt...")
        print("=" * 60)

        # First interpret the command
        print("1. Interpreting command...")
        command = await interpret_write_command(prompt, session)
        print("Command operation:", command.get("operation") if command else "None")

        if command and command.get("operation", "none") != "none":
            # Execute the command
            print("\n2. Executing command...")
            result = await execute_write_command(command, session, preview_only=False)
            
            print("Success:", result.get("success"))
            msg = result.get("message", "")
            if len(msg) > 300:
                msg = msg[:300] + "..."
            print("Message:", msg)

            if result.get("results"):
                print("\nOperation Results:")
                for r in result.get("results", []):
                    status = "OK" if r.get("success", True) else "FAIL"
                    op_msg = r.get("message", "")
                    if len(op_msg) > 80:
                        op_msg = op_msg[:80] + "..."
                    print(f"  [{status}] {r.get('operation')}: {op_msg}")
        else:
            print("Failed to interpret command:", command)

        print("\n" + "=" * 60)
        break

if __name__ == "__main__":
    asyncio.run(test())
