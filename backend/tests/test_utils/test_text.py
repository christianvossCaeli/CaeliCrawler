"""Tests for app.utils.text module."""

import pytest

from app.utils.text import is_valid_person_name


class TestIsValidPersonName:
    """Tests for is_valid_person_name function."""

    @pytest.mark.parametrize(
        "name",
        [
            "Hans Müller",
            "Dr. Hans Müller",
            "Prof. Dr. Maria Schmidt",
            "Max Mustermann",
            "Anna-Maria von Hohenheim",
            "Müller, Hans",
            "Schmidt, Maria, Dr.",
            "李明",  # Chinese name
            "Jean-Pierre Dupont",  # French name with hyphen
        ],
    )
    def test_valid_person_names(self, name: str) -> None:
        """Test that valid person names are accepted."""
        assert is_valid_person_name(name) is True, f"Should accept: {name}"

    @pytest.mark.parametrize(
        "name",
        [
            # Administrative terms
            "Amt für Stadtentwicklung",
            "Region Hannover",
            "Landkreis München",
            "Stadtverwaltung Köln",
            "Ministerium für Umwelt",
            "Bauamt",
            "Finanzamt Frankfurt",
            # Organizations
            "Muster GmbH",
            "Beispiel AG",
            "Verein e.V.",
            "Feuerwehr Berlin",
            "Polizei Hamburg",
            "Universität Heidelberg",
            # Placeholders
            "Kontaktinformationen nicht verfügbar",
            "Ansprechpartner",
            "N/A",
            "unbekannt",
            "Kontakt",
            "info@example.com",
            # Too long (more than 60 chars)
            "A" * 61,
            # Too many commas
            "A, B, C, D",
            # Too many words (more than 6)
            "Prof. Dr. Dr. h.c. mult. Hans Peter Müller Schmidt",
            # Empty or None-like
            "",
            "  ",
        ],
    )
    def test_invalid_person_names(self, name: str) -> None:
        """Test that invalid person names are rejected."""
        assert is_valid_person_name(name) is False, f"Should reject: {name}"

    def test_none_input(self) -> None:
        """Test that None input returns False."""
        assert is_valid_person_name(None) is False  # type: ignore[arg-type]

    def test_non_string_input(self) -> None:
        """Test that non-string input returns False."""
        assert is_valid_person_name(123) is False  # type: ignore[arg-type]
        assert is_valid_person_name(["Hans", "Müller"]) is False  # type: ignore[arg-type]

    def test_whitespace_handling(self) -> None:
        """Test that whitespace is properly handled."""
        assert is_valid_person_name("  Hans Müller  ") is True
        assert is_valid_person_name("  ") is False

    def test_case_insensitivity(self) -> None:
        """Test that administrative term detection is case-insensitive."""
        assert is_valid_person_name("AMT für Bau") is False
        assert is_valid_person_name("amt für bau") is False
        assert is_valid_person_name("Amt für Bau") is False
