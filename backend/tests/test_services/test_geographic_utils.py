"""Tests for geographic utilities including fuzzy matching."""

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
    """Test fuzzy matching for geographic aliases."""

    @pytest.mark.asyncio
    async def test_suggest_correction_typo(self):
        """Test correction suggestion for typos."""
        from services.smart_query.geographic_utils import find_all_geo_suggestions

        # NWR is a common typo for NRW
        suggestions = find_all_geo_suggestions("NWR")

        assert len(suggestions) > 0
        # Suggestions are tuples: (alias, canonical, distance)
        suggestion_values = [s[1] for s in suggestions]  # canonical names
        assert any("Nordrhein" in s for s in suggestion_values)

    @pytest.mark.asyncio
    async def test_suggest_correction_case_insensitive(self):
        """Test that matching is case insensitive."""
        from services.smart_query.geographic_utils import find_all_geo_suggestions

        suggestions_lower = find_all_geo_suggestions("nrw")
        suggestions_upper = find_all_geo_suggestions("NRW")

        # Both should find the same result (empty because it's an exact match)
        assert len(suggestions_lower) == 0  # Exact match - no suggestion needed
        assert len(suggestions_upper) == 0

    @pytest.mark.asyncio
    async def test_no_suggestion_for_valid_alias(self):
        """Test that no suggestion is made for valid aliases."""
        from services.smart_query.geographic_utils import resolve_geographic_alias

        # Valid alias should resolve directly
        resolved = resolve_geographic_alias("NRW")

        assert resolved == "Nordrhein-Westfalen"

    @pytest.mark.asyncio
    async def test_suggest_correction_threshold(self):
        """Test that suggestions respect the threshold."""
        from services.smart_query.geographic_utils import find_all_geo_suggestions

        # Very different string should not match
        suggestions = find_all_geo_suggestions("XXXYYY")

        # Should be empty (no suggestions within threshold)
        assert len(suggestions) == 0


class TestResolveLocationAliases:
    """Test location alias resolution."""

    @pytest.mark.asyncio
    async def test_resolve_bundesland_alias(self):
        """Test resolving Bundesland alias."""
        from services.smart_query.geographic_utils import resolve_geographic_alias

        resolved = resolve_geographic_alias("NRW")
        assert resolved == "Nordrhein-Westfalen"

        resolved = resolve_geographic_alias("BY")
        assert resolved == "Bayern"

    @pytest.mark.asyncio
    async def test_resolve_multiple_aliases(self):
        """Test resolving multiple aliases."""
        from services.smart_query.geographic_utils import resolve_geographic_alias

        resolved_nrw = resolve_geographic_alias("NRW")
        resolved_by = resolve_geographic_alias("BY")
        resolved_bw = resolve_geographic_alias("BW")

        assert resolved_nrw == "Nordrhein-Westfalen"
        assert resolved_by == "Bayern"
        assert resolved_bw == "Baden-Württemberg"

    @pytest.mark.asyncio
    async def test_resolve_preserves_unknown(self):
        """Test that unknown values are preserved."""
        from services.smart_query.geographic_utils import resolve_geographic_alias

        resolved = resolve_geographic_alias("UnknownLocation")

        # Unknown locations should be passed through unchanged
        assert resolved == "UnknownLocation"


class TestGeoAliases:
    """Test geographic alias definitions."""

    def test_bundesland_aliases_exist(self):
        """Test that Bundesland aliases are defined."""
        from services.smart_query.geographic_utils import GERMAN_STATE_ALIASES

        # Check some common aliases exist (keys are lowercase)
        assert "nrw" in GERMAN_STATE_ALIASES
        assert "by" in GERMAN_STATE_ALIASES

    def test_bundesland_aliases_map_correctly(self):
        """Test that aliases map to correct full names."""
        from services.smart_query.geographic_utils import GERMAN_STATE_ALIASES

        # Check NRW alias maps correctly
        assert GERMAN_STATE_ALIASES["nrw"] == "Nordrhein-Westfalen"
        assert GERMAN_STATE_ALIASES["by"] == "Bayern"
        assert GERMAN_STATE_ALIASES["bw"] == "Baden-Württemberg"
