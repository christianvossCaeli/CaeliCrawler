#!/usr/bin/env python3
"""Smoke test for recent fixes.

Tests:
1. Location substring duplicate detection
2. SKIP_FIELDS contains all internal fields
3. LLM cost calculation
4. Smart Query configuration

Usage:
    python -m scripts.smoke_test_fixes

    Or from project root:
    uv run python backend/scripts/smoke_test_fixes.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    # Fallback if structlog not available
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


class SmokeTests:
    """Collection of smoke tests for recent fixes."""

    def __init__(self):
        self.results: list[tuple[str, bool, str]] = []

    def test(self, name: str, passed: bool, message: str = ""):
        """Record a test result."""
        status = "PASS" if passed else "FAIL"
        self.results.append((name, passed, message))
        print(f"  [{status}] {name}")
        if message:
            print(f"         {message}")

    async def test_location_substring_detection(self):
        """Test that substring locations are detected as duplicates."""
        print("\n1. Testing Location Substring Detection")
        print("-" * 50)

        from app.utils.similarity_functions import find_similar_locations_by_name

        # Create mock locations
        class MockLocation:
            def __init__(self, id: str, name: str, name_normalized: str):
                self.id = id
                self.name = name
                self.name_normalized = name_normalized

        existing = [
            MockLocation("1", "Hannover", "hannover"),
            MockLocation("2", "Berlin", "berlin"),
            MockLocation("3", "München", "muenchen"),
        ]

        # Test: "Region Hannover" should match "Hannover"
        matches = find_similar_locations_by_name(
            "Region Hannover", "Deutschland", existing
        )

        if matches:
            self.test(
                "Substring detection: 'Region Hannover' finds 'Hannover'",
                True,
                f"Match: {matches[0][0].name} (score: {matches[0][1]:.2f})"
            )
        else:
            self.test(
                "Substring detection: 'Region Hannover' finds 'Hannover'",
                False,
                "No match found!"
            )

        # Test: "Hannover" should match "Region Hannover" (reverse)
        existing_with_region = [
            MockLocation("1", "Region Hannover", "region hannover"),
        ]
        matches = find_similar_locations_by_name(
            "Hannover", "Deutschland", existing_with_region
        )

        if matches:
            self.test(
                "Reverse substring: 'Hannover' finds 'Region Hannover'",
                True,
                f"Match: {matches[0][0].name} (score: {matches[0][1]:.2f})"
            )
        else:
            self.test(
                "Reverse substring: 'Hannover' finds 'Region Hannover'",
                False,
                "No match found!"
            )

    async def test_skip_fields(self):
        """Test that SKIP_FIELDS contains all internal fields."""
        print("\n2. Testing SKIP_FIELDS Configuration")
        print("-" * 50)

        from services.entity_facet_service import convert_extraction_to_facets

        # Get SKIP_FIELDS from the function (it's defined inside)
        # We'll check the source code instead
        import inspect
        source = inspect.getsource(convert_extraction_to_facets)

        required_fields = [
            "suggested_additional_pages",
            "source_page",
            "source_pages",
            "page_numbers",
            "analyzed_pages",
            "total_pages",
        ]

        for field in required_fields:
            found = f'"{field}"' in source
            self.test(
                f"SKIP_FIELDS contains '{field}'",
                found,
                "" if found else "Missing from SKIP_FIELDS!"
            )

    async def test_llm_pricing(self):
        """Test LLM pricing configuration."""
        print("\n3. Testing LLM Pricing")
        print("-" * 50)

        from services.llm_usage_tracker import MODEL_PRICING, get_model_pricing

        # Test default pricing exists
        default = MODEL_PRICING.get("default")
        self.test(
            "Default pricing exists",
            default is not None,
            f"input=${default['input'] if default else 'N/A'}/1M" if default else ""
        )

        # Test common models have pricing
        common_models = [
            "gpt-4o",
            "gpt-4o-mini",
            "claude-3-5-sonnet",
            "text-embedding-3-large",
        ]

        for model in common_models:
            pricing = get_model_pricing(model)
            is_default = pricing == MODEL_PRICING.get("default")
            self.test(
                f"Pricing for '{model}'",
                not is_default,
                f"input=${pricing['input']}/1M, output=${pricing['output']}/1M" if not is_default else "Using fallback!"
            )

        # Test cost calculation
        pricing = get_model_pricing("gpt-4o")
        test_cost = int(
            ((1000 / 1_000_000) * pricing["input"] +
             (500 / 1_000_000) * pricing["output"]) * 100 + 0.5
        )
        self.test(
            "Cost calculation works",
            test_cost > 0,
            f"1000 in + 500 out tokens = ${test_cost/100:.4f}"
        )

    async def test_llm_purposes(self):
        """Test LLM purpose configuration."""
        print("\n4. Testing LLM Purpose Configuration")
        print("-" * 50)

        from app.models.user_api_credentials import LLMPurpose

        required_purposes = [
            "DOCUMENT_ANALYSIS",
            "ASSISTANT",
            "EMBEDDINGS",
            "PLAN_MODE",
        ]

        for purpose in required_purposes:
            has_purpose = hasattr(LLMPurpose, purpose)
            self.test(
                f"LLMPurpose.{purpose} exists",
                has_purpose,
                ""
            )

    async def run_all(self):
        """Run all smoke tests."""
        print("\n" + "=" * 70)
        print("Smoke Test Suite for Recent Fixes")
        print("=" * 70)

        await self.test_location_substring_detection()
        await self.test_skip_fields()
        await self.test_llm_pricing()
        await self.test_llm_purposes()

        # Summary
        print("\n" + "=" * 70)
        print("Summary")
        print("=" * 70)

        passed = sum(1 for _, p, _ in self.results if p)
        failed = sum(1 for _, p, _ in self.results if not p)
        total = len(self.results)

        print(f"\n  Total:  {total}")
        print(f"  Passed: {passed}")
        print(f"  Failed: {failed}")

        if failed > 0:
            print("\n  Failed Tests:")
            for name, p, msg in self.results:
                if not p:
                    print(f"    - {name}")
                    if msg:
                        print(f"      {msg}")

        print("\n" + "=" * 70)
        return failed == 0


async def main():
    """Main entry point."""
    tests = SmokeTests()
    success = await tests.run_all()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
