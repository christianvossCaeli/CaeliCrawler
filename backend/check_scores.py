import asyncio
from sqlalchemy import select
from app.database import async_session_factory
from app.models import Document, DataSource, DataSourceCategory, Category, ExtractedData

async def check():
    async with async_session_factory() as session:
        cat = (await session.execute(
            select(Category).where(Category.slug == "regionalplaene-wind")
        )).scalar_one_or_none()

        # Get ExtractedData for this category
        extractions = (await session.execute(
            select(ExtractedData)
            .where(ExtractedData.category_id == cat.id)
            .limit(100)
        )).scalars().all()

        print("EXTRACTED DATA ANALYSE")
        print("=" * 60)
        print(f"Gesamt: {len(extractions)} Extraktionen")

        # Confidence Score Verteilung
        confidence_scores = {}
        relevance_scores = {}

        for ext in extractions:
            if ext.confidence_score is not None:
                c = int(ext.confidence_score * 100)
                confidence_scores[c] = confidence_scores.get(c, 0) + 1
            if ext.relevance_score is not None:
                r = int(ext.relevance_score * 100)
                relevance_scores[r] = relevance_scores.get(r, 0) + 1

        print()
        print("Confidence Score Verteilung:")
        for s in sorted(confidence_scores.keys()):
            bar = "#" * (confidence_scores[s] // 2)
            print(f"  {s:3d}%: {confidence_scores[s]:3d} {bar}")

        print()
        print("Relevance Score Verteilung:")
        for s in sorted(relevance_scores.keys()):
            bar = "#" * (relevance_scores[s] // 2)
            print(f"  {s:3d}%: {relevance_scores[s]:3d} {bar}")

        # Beispiele
        print()
        print("Beispiele:")
        for ext in extractions[:5]:
            c = int(ext.confidence_score * 100) if ext.confidence_score else 0
            r = int(ext.relevance_score * 100) if ext.relevance_score else 0
            print(f"  Conf: {c:3d}%, Rel: {r:3d}% - Type: {ext.extraction_type}")

if __name__ == "__main__":
    asyncio.run(check())
