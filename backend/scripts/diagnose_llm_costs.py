#!/usr/bin/env python3
"""Diagnose LLM cost calculation issues.

This script analyzes why LLM costs might be showing as 0.

Usage:
    python -m scripts.diagnose_llm_costs
"""

import asyncio
import sys
from collections import defaultdict
from pathlib import Path

import structlog

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.llm_usage import LLMUsageRecord

logger = structlog.get_logger(__name__)


async def diagnose_costs(session: AsyncSession) -> None:
    """Diagnose LLM cost calculation issues."""
    from services.llm_usage_tracker import MODEL_PRICING, get_model_pricing

    print("\n" + "=" * 70)
    print("LLM Cost Diagnosis")
    print("=" * 70)

    # 1. Get distinct models in the database
    print("\n1. Models in Database:")
    print("-" * 50)
    result = await session.execute(
        select(
            LLMUsageRecord.model,
            func.count(LLMUsageRecord.id).label("count"),
            func.sum(LLMUsageRecord.prompt_tokens).label("total_prompt"),
            func.sum(LLMUsageRecord.completion_tokens).label("total_completion"),
            func.sum(LLMUsageRecord.estimated_cost_cents).label("total_cost"),
        )
        .group_by(LLMUsageRecord.model)
        .order_by(func.count(LLMUsageRecord.id).desc())
    )

    models_data = []
    for row in result.all():
        model_name = row.model or "NULL"
        count = row.count
        prompt_tokens = row.total_prompt or 0
        completion_tokens = row.total_completion or 0
        stored_cost = row.total_cost or 0

        # Get pricing
        pricing = get_model_pricing(model_name)
        calculated_cost = int(
            ((prompt_tokens / 1_000_000) * pricing["input"] +
             (completion_tokens / 1_000_000) * pricing["output"]) * 100 + 0.5
        )

        models_data.append({
            "model": model_name,
            "count": count,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "stored_cost": stored_cost,
            "calculated_cost": calculated_cost,
            "pricing": pricing,
        })

        print(f"\n  Model: {model_name}")
        print(f"    Records: {count}")
        print(f"    Prompt Tokens: {prompt_tokens:,}")
        print(f"    Completion Tokens: {completion_tokens:,}")
        print(f"    Stored Cost: ${stored_cost / 100:.2f}")
        print(f"    Calculated Cost: ${calculated_cost / 100:.2f}")
        print(f"    Pricing Used: input=${pricing['input']}/1M, output=${pricing['output']}/1M")

        if stored_cost == 0 and calculated_cost > 0:
            print(f"    >>> ISSUE: Stored cost is 0 but should be ${calculated_cost / 100:.2f}")
        elif model_name != "NULL" and pricing == MODEL_PRICING.get("default"):
            print(f"    >>> WARNING: Using fallback pricing for model '{model_name}'")

    # 2. Check for NULL token counts
    print("\n\n2. Records with NULL/0 Token Counts:")
    print("-" * 50)
    result = await session.execute(
        select(func.count(LLMUsageRecord.id)).where(
            (LLMUsageRecord.prompt_tokens.is_(None)) |
            (LLMUsageRecord.prompt_tokens == 0)
        )
    )
    null_prompt = result.scalar() or 0

    result = await session.execute(
        select(func.count(LLMUsageRecord.id)).where(
            (LLMUsageRecord.completion_tokens.is_(None)) |
            (LLMUsageRecord.completion_tokens == 0)
        )
    )
    null_completion = result.scalar() or 0

    result = await session.execute(select(func.count(LLMUsageRecord.id)))
    total_records = result.scalar() or 0

    print(f"  Total Records: {total_records}")
    print(f"  Records with NULL/0 prompt_tokens: {null_prompt} ({null_prompt/max(total_records,1)*100:.1f}%)")
    print(f"  Records with NULL/0 completion_tokens: {null_completion} ({null_completion/max(total_records,1)*100:.1f}%)")

    # 3. Check hardcoded pricing vs database pricing
    print("\n\n3. Pricing Configuration:")
    print("-" * 50)
    print("  Hardcoded Models in MODEL_PRICING:")
    for model, pricing in sorted(MODEL_PRICING.items()):
        print(f"    {model}: input=${pricing['input']}/1M, output=${pricing['output']}/1M")

    # 4. Recommendations
    print("\n\n4. Recommendations:")
    print("-" * 50)

    has_issues = False
    for data in models_data:
        if data["stored_cost"] == 0 and data["calculated_cost"] > 0:
            has_issues = True
            print(f"  - Recalculate costs for model '{data['model']}' ({data['count']} records)")

    if not has_issues:
        if null_prompt > 0 or null_completion > 0:
            print("  - Some records have no token counts - this is likely correct for embeddings")
        else:
            print("  - No issues detected with cost calculation")
    else:
        print("\n  To fix, run the recalculation:")
        print("    - Via Admin UI: /admin/llm-usage -> 'Kosten neu berechnen'")
        print("    - Via API: POST /admin/llm-usage/recalculate-costs?only_zero_costs=true")


async def main():
    """Main entry point."""
    async with async_session_factory() as session:
        await diagnose_costs(session)


if __name__ == "__main__":
    asyncio.run(main())
