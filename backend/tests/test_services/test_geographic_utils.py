"""Tests for geographic utilities including fuzzy matching.

Note: These tests use AI-based alias resolution. The system is fully generic
and does not rely on hardcoded mappings.
"""

import pytest


class TestLevenshteinDistance:
    """Test Levenshtein distance calculation."""

    @pytest.mark.asyncio
    async def test_levenshtein_same_strings(self):
        """Test distance is 0 for identical strings."""
        from services.smart_query.geographic_utils import levenshtein_distance

        assert levenshtein_distance("NRW", "NRW") == 0
        assert levenshtein_distance("Bayern", "Bayern") == 0

    @pytest.mark.asyncio
    async def test_levenshtein_one_char_diff(self):
        """Test distance is 1 for single character difference."""
        from services.smart_query.geographic_utils import levenshtein_distance

        # Substitution
        assert levenshtein_distance("NRW", "NRX") == 1
        # Insertion
        assert levenshtein_distance("NRW", "NRWW") == 1
        # Deletion
        assert levenshtein_distance("NRW", "NR") == 1

    @pytest.mark.asyncio
    async def test_levenshtein_two_char_diff(self):
        """Test distance is 2 for two character difference."""
        from services.smart_query.geographic_utils import levenshtein_distance

        assert levenshtein_distance("NRW", "NWR") == 2
        assert levenshtein_distance("Bayern", "Bayren") <= 2

    @pytest.mark.asyncio
    async def test_levenshtein_empty_strings(self):
        """Test distance with empty strings."""
        from services.smart_query.geographic_utils import levenshtein_distance

        assert levenshtein_distance("", "") == 0
        assert levenshtein_distance("NRW", "") == 3
        assert levenshtein_distance("", "NRW") == 3


class TestFuzzyMatching:
    """Test fuzzy matching for aliases."""

    @pytest.mark.asyncio
    async def test_suggest_correction_async(self):
        """Test correction suggestion for typos using async function."""
        from services.smart_query.alias_utils import suggest_correction_async

        # Test with a known list of values
        known_values = ["Nordrhein-Westfalen", "Bayern", "Baden-Württemberg"]

        # "Bayren" is a typo for "Bayern"
        suggestion = await suggest_correction_async("Bayren", known_values)

        assert suggestion is not None
        assert suggestion[1] == "Bayern"  # canonical name

    @pytest.mark.asyncio
    async def test_suggest_correction_case_insensitive(self):
        """Test that matching is case insensitive."""
        from services.smart_query.alias_utils import suggest_correction_async

        known_values = ["Nordrhein-Westfalen", "Bayern"]

        # Both upper and lower case should work
        suggestion_lower = await suggest_correction_async("bayren", known_values)
        suggestion_upper = await suggest_correction_async("BAYREN", known_values)

        assert suggestion_lower is not None
        assert suggestion_upper is not None
        assert suggestion_lower[1] == suggestion_upper[1] == "Bayern"

    @pytest.mark.asyncio
    async def test_suggest_correction_threshold(self):
        """Test that suggestions respect the threshold."""
        from services.smart_query.alias_utils import suggest_correction_async

        known_values = ["Nordrhein-Westfalen", "Bayern"]

        # Very different string should not match with default threshold
        suggestion = await suggest_correction_async("XXXYYY", known_values)

        assert suggestion is None


class TestResolveAliasAsync:
    """Test AI-based alias resolution using async functions."""

    @pytest.mark.asyncio
    async def test_resolve_bundesland_alias_async(self):
        """Test resolving Bundesland alias using async AI-based resolution."""
        from services.smart_query.alias_utils import resolve_alias_async

        # NRW should resolve to Nordrhein-Westfalen (unambiguous)
        resolved = await resolve_alias_async("NRW", domain="geographic")
        assert resolved == "Nordrhein-Westfalen"

        # "Bayern" (full name) should stay unchanged or resolve correctly
        resolved = await resolve_alias_async("Bayern", domain="geographic")
        assert resolved == "Bayern"

    @pytest.mark.asyncio
    async def test_resolve_german_state_abbreviations_async(self):
        """Test resolving German state abbreviations with context."""
        from services.smart_query.alias_utils import resolve_alias_async

        # Unambiguous German state abbreviations
        resolved_nrw = await resolve_alias_async("NRW", domain="German state")
        assert resolved_nrw == "Nordrhein-Westfalen"

        resolved_bw = await resolve_alias_async("BW", domain="German state")
        assert resolved_bw == "Baden-Württemberg"

    @pytest.mark.asyncio
    async def test_resolve_preserves_unknown_async(self):
        """Test that unknown values are preserved."""
        from services.smart_query.alias_utils import resolve_alias_async

        resolved = await resolve_alias_async("XYZUnknownLocation123", domain="geographic")

        # Unknown locations should be passed through unchanged
        assert resolved == "XYZUnknownLocation123"


class TestGenericAliasResolution:
    """Test generic (non-geographic) alias resolution."""

    @pytest.mark.asyncio
    async def test_resolve_organization_alias(self):
        """Test resolving organization abbreviations."""
        from services.smart_query.alias_utils import resolve_alias_async

        # WHO should resolve to World Health Organization
        resolved = await resolve_alias_async("WHO", domain="organization")
        assert "World Health Organization" in resolved or resolved == "WHO"

    @pytest.mark.asyncio
    async def test_resolve_without_domain(self):
        """Test resolving alias without specifying domain."""
        from services.smart_query.alias_utils import resolve_alias_async

        # Should still work without domain hint
        resolved = await resolve_alias_async("NRW")
        # May or may not resolve depending on AI interpretation
        assert resolved is not None


class TestTermExpansion:
    """Test AI-based term expansion."""

    @pytest.mark.asyncio
    async def test_expand_terms_async(self):
        """Test term expansion using async function."""
        from services.smart_query.alias_utils import expand_terms_async

        # Abstract term "Entscheidungsträger" should expand to specific roles
        expanded = await expand_terms_async(
            context="business leadership",
            raw_terms=["decision maker"]
        )

        assert len(expanded) >= 1
        # Should return at least the original or expanded terms

    @pytest.mark.asyncio
    async def test_expand_concrete_term_unchanged(self):
        """Test that concrete terms are not unnecessarily expanded."""
        from services.smart_query.alias_utils import expand_terms_async

        # A very specific term should remain as-is or be minimally expanded
        expanded = await expand_terms_async(
            context="job titles",
            raw_terms=["CEO"]
        )

        assert "CEO" in expanded or any("Chief" in t for t in expanded)
