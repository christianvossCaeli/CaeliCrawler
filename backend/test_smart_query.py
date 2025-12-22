#!/usr/bin/env python3
"""Full Smart Query test via backend."""
import asyncio
from app.database import get_session
from services.smart_query.smart_query_service import SmartQueryService

async def test():
    async for session in get_session():
        service = SmartQueryService(session)

        prompt = """Ich möchte Windenergie-Projekte und Potenziale für Windflächen in Deutschland analysieren. Dafür brauche ich:

- Alle 16 deutschen Bundesländer mit Einwohnerzahl und Fläche - bitte auch Datenquellen einrichten damit die Zahlen aktuell bleiben
- Alle deutschen Gemeinden, verknüpft mit ihrem jeweiligen Bundesland
- Einen Typ "Windpark" der zu Gemeinden gehört - die Windparks sollen aus der Caeli Auction API importiert und automatisch mit der passenden Gemeinde verknüpft werden
- Für alle sollen die passenden Facetten nutzbar sein

Kannst du das einrichten?"""

        print("Testing Smart Query with natural language prompt...")
        print("=" * 60)

        result = await service.execute_write_query(
            question=prompt,
            preview_only=False,
            confirmed=True,
        )

        print("Success:", result.get("success"))
        msg = result.get("message", "")
        if len(msg) > 200:
            msg = msg[:200] + "..."
        print("Message:", msg)

        if result.get("results"):
            print("\nOperation Results:")
            for r in result.get("results", []):
                status = "OK" if r.get("success", True) else "FAIL"
                op_msg = r.get("message", "")
                if len(op_msg) > 80:
                    op_msg = op_msg[:80] + "..."
                print(f"  [{status}] {r.get('operation')}: {op_msg}")

        if result.get("errors"):
            print("\nErrors:")
            for e in result.get("errors", [])[:5]:
                err_str = str(e)
                if len(err_str) > 100:
                    err_str = err_str[:100] + "..."
                print(f"  - {err_str}")

        print("\n" + "=" * 60)
        break

if __name__ == "__main__":
    asyncio.run(test())
