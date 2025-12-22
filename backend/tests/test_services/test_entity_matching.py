"""Tests for Entity Matching Service and Similarity utilities."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.utils.similarity import (
    calculate_name_similarity,
    _normalize_for_comparison,
    is_likely_duplicate,
)
from services.entity_matching_service import EntityMatchingService


class TestNameSimilarity:
    """Tests for name similarity calculations."""

    def test_exact_match(self):
        """Test that identical names return 1.0."""
        assert calculate_name_similarity("München", "München") == 1.0
        assert calculate_name_similarity("Berlin", "Berlin") == 1.0

    def test_umlaut_equivalence(self):
        """Test that umlaut variations are considered similar."""
        score = calculate_name_similarity("München", "Muenchen")
        assert score >= 0.9, f"Expected >= 0.9, got {score}"

        score = calculate_name_similarity("Köln", "Koeln")
        assert score >= 0.9, f"Expected >= 0.9, got {score}"

        score = calculate_name_similarity("Düsseldorf", "Duesseldorf")
        assert score >= 0.9, f"Expected >= 0.9, got {score}"

    def test_prefix_removal(self):
        """Test that common prefixes don't affect similarity."""
        score = calculate_name_similarity("Stadt München", "München")
        assert score >= 0.85, f"Expected >= 0.85, got {score}"

        score = calculate_name_similarity("Gemeinde Rosenheim", "Rosenheim")
        assert score >= 0.85, f"Expected >= 0.85, got {score}"

        score = calculate_name_similarity("Landkreis Freising", "Freising")
        assert score >= 0.85, f"Expected >= 0.85, got {score}"

    def test_suffix_removal(self):
        """Test that common suffixes don't affect similarity."""
        score = calculate_name_similarity("München Stadt", "München")
        assert score >= 0.85, f"Expected >= 0.85, got {score}"

    def test_different_names(self):
        """Test that different names have low similarity."""
        score = calculate_name_similarity("Berlin", "Hamburg")
        assert score < 0.5, f"Expected < 0.5, got {score}"

        score = calculate_name_similarity("München", "Frankfurt")
        assert score < 0.5, f"Expected < 0.5, got {score}"

    def test_substring_boost(self):
        """Test substring matching boost."""
        score = calculate_name_similarity("Bad Homburg", "Bad Homburg vor der Höhe")
        assert score >= 0.85, f"Expected >= 0.85, got {score}"

    def test_case_insensitivity(self):
        """Test that comparison is case-insensitive."""
        assert calculate_name_similarity("MÜNCHEN", "münchen") == 1.0
        assert calculate_name_similarity("Berlin", "BERLIN") == 1.0


class TestNormalizeForComparison:
    """Tests for the internal normalization function."""

    def test_lowercase(self):
        """Test that result is lowercase."""
        result = _normalize_for_comparison("MÜNCHEN")
        assert result.islower() or result == ""

    def test_prefix_removal(self):
        """Test common prefix removal."""
        assert _normalize_for_comparison("stadt münchen") == "muenchen"
        assert _normalize_for_comparison("gemeinde rosenheim") == "rosenheim"
        assert _normalize_for_comparison("landkreis freising") == "freising"

    def test_suffix_removal(self):
        """Test common suffix removal."""
        assert _normalize_for_comparison("münchen stadt") == "muenchen"
        assert _normalize_for_comparison("rosenheim gemeinde") == "rosenheim"

    def test_umlaut_replacement(self):
        """Test umlaut to ASCII conversion."""
        assert "ue" in _normalize_for_comparison("München")  # ü → ue
        assert "oe" in _normalize_for_comparison("Köln")     # ö → oe
        assert "ue" in _normalize_for_comparison("Düsseldorf")  # ü → ue
        assert "ss" in _normalize_for_comparison("Straße")   # ß → ss
        assert "ae" in _normalize_for_comparison("Gräfenhausen")  # ä → ae


class TestIsDuplicate:
    """Tests for the quick duplicate check."""

    def test_exact_match_is_duplicate(self):
        """Test exact match detection."""
        assert is_likely_duplicate("München", "München") is True

    def test_normalized_match_is_duplicate(self):
        """Test normalized match detection."""
        assert is_likely_duplicate("München", "Muenchen", strict_threshold=0.9) is True

    def test_different_names_not_duplicate(self):
        """Test different names aren't duplicates."""
        assert is_likely_duplicate("Berlin", "Hamburg") is False


class TestEntityMatchingService:
    """Tests for the EntityMatchingService."""

    @pytest.mark.asyncio
    async def test_get_or_create_entity_finds_existing(self, session):
        """Test that existing entity is found."""
        service = EntityMatchingService(session)

        entity_type_id = uuid4()
        entity_id = uuid4()

        # Mock entity type
        mock_entity_type = MagicMock()
        mock_entity_type.id = entity_type_id
        mock_entity_type.slug = "territorial_entity"

        # Mock existing entity
        mock_entity = MagicMock()
        mock_entity.id = entity_id
        mock_entity.name = "München"
        mock_entity.name_normalized = "muenchen"

        with patch.object(service, '_get_entity_type', new_callable=AsyncMock) as mock_get_type:
            mock_get_type.return_value = mock_entity_type

            with patch.object(service, '_find_by_normalized_name', new_callable=AsyncMock) as mock_find:
                mock_find.return_value = mock_entity

                result = await service.get_or_create_entity(
                    entity_type_slug="territorial_entity",
                    name="München",
                )

        assert result is not None
        assert result.id == entity_id

    @pytest.mark.asyncio
    async def test_get_or_create_entity_returns_none_for_invalid_type(self, session):
        """Test that None is returned for invalid entity type."""
        service = EntityMatchingService(session)

        with patch.object(service, '_get_entity_type', new_callable=AsyncMock) as mock_get_type:
            mock_get_type.return_value = None

            result = await service.get_or_create_entity(
                entity_type_slug="nonexistent",
                name="Test Entity",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_or_create_entity_creates_new(self, session):
        """Test that new entity is created when not found."""
        service = EntityMatchingService(session)

        entity_type_id = uuid4()

        # Mock entity type
        mock_entity_type = MagicMock()
        mock_entity_type.id = entity_type_id
        mock_entity_type.slug = "territorial_entity"

        with patch.object(service, '_get_entity_type', new_callable=AsyncMock) as mock_get_type:
            mock_get_type.return_value = mock_entity_type

            with patch.object(service, '_find_by_normalized_name', new_callable=AsyncMock) as mock_find:
                mock_find.return_value = None

                with patch.object(service, '_create_entity_safe', new_callable=AsyncMock) as mock_create:
                    mock_new_entity = MagicMock()
                    mock_new_entity.id = uuid4()
                    mock_new_entity.name = "New Entity"
                    mock_create.return_value = mock_new_entity

                    result = await service.get_or_create_entity(
                        entity_type_slug="territorial_entity",
                        name="New Entity",
                    )

        assert result is not None
        assert result.name == "New Entity"
        mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_entity_uses_external_id(self, session):
        """Test that external_id is used for matching when provided."""
        service = EntityMatchingService(session)

        entity_type_id = uuid4()
        entity_id = uuid4()

        mock_entity_type = MagicMock()
        mock_entity_type.id = entity_type_id

        mock_entity = MagicMock()
        mock_entity.id = entity_id
        mock_entity.external_id = "EXT-123"

        with patch.object(service, '_get_entity_type', new_callable=AsyncMock) as mock_get_type:
            mock_get_type.return_value = mock_entity_type

            with patch.object(service, '_find_by_external_id', new_callable=AsyncMock) as mock_find_ext:
                mock_find_ext.return_value = mock_entity

                result = await service.get_or_create_entity(
                    entity_type_slug="territorial_entity",
                    name="München",
                    external_id="EXT-123",
                )

        assert result is not None
        assert result.id == entity_id
        mock_find_ext.assert_called_once()

    @pytest.mark.asyncio
    async def test_similarity_matching_enabled(self, session):
        """Test that similarity matching is used when threshold < 1.0."""
        service = EntityMatchingService(session)

        entity_type_id = uuid4()

        mock_entity_type = MagicMock()
        mock_entity_type.id = entity_type_id

        mock_similar_entity = MagicMock()
        mock_similar_entity.id = uuid4()
        mock_similar_entity.name = "München"

        with patch.object(service, '_get_entity_type', new_callable=AsyncMock) as mock_get_type:
            mock_get_type.return_value = mock_entity_type

            with patch.object(service, '_find_by_normalized_name', new_callable=AsyncMock) as mock_find:
                mock_find.return_value = None

                with patch.object(service, '_find_similar_entity', new_callable=AsyncMock) as mock_find_similar:
                    mock_find_similar.return_value = mock_similar_entity

                    result = await service.get_or_create_entity(
                        entity_type_slug="territorial_entity",
                        name="Muenchen",
                        similarity_threshold=0.85,
                    )

        assert result is not None
        assert result.id == mock_similar_entity.id
        mock_find_similar.assert_called_once()


class TestBatchOperations:
    """Tests for batch entity operations."""

    @pytest.mark.asyncio
    async def test_batch_get_or_create_entities(self, session):
        """Test batch entity lookup and creation."""
        service = EntityMatchingService(session)

        entity_type_id = uuid4()

        mock_entity_type = MagicMock()
        mock_entity_type.id = entity_type_id
        mock_entity_type.slug = "territorial_entity"

        # Mock existing entity
        mock_existing = MagicMock()
        mock_existing.id = uuid4()
        mock_existing.name = "München"
        mock_existing.name_normalized = "muenchen"

        with patch.object(service, '_get_entity_type', new_callable=AsyncMock) as mock_get_type:
            mock_get_type.return_value = mock_entity_type

            with patch.object(session, 'execute', new_callable=AsyncMock) as mock_execute:
                mock_result = MagicMock()
                mock_result.scalars.return_value.all.return_value = [mock_existing]
                mock_execute.return_value = mock_result

                with patch.object(service, '_create_entity_safe', new_callable=AsyncMock) as mock_create:
                    mock_new = MagicMock()
                    mock_new.id = uuid4()
                    mock_new.name = "Berlin"
                    mock_new.name_normalized = "berlin"
                    mock_create.return_value = mock_new

                    result = await service.batch_get_or_create_entities(
                        entity_type_slug="territorial_entity",
                        names=["München", "Berlin"],
                    )

        assert "München" in result
        assert result["München"].id == mock_existing.id


class TestRaceConditionSafety:
    """Tests for race condition handling."""

    @pytest.mark.asyncio
    async def test_integrity_error_handling(self, session):
        """Test that IntegrityError is handled gracefully."""
        from sqlalchemy.exc import IntegrityError

        service = EntityMatchingService(session)

        entity_type_id = uuid4()

        mock_entity_type = MagicMock()
        mock_entity_type.id = entity_type_id
        mock_entity_type.slug = "territorial_entity"

        # After rollback, find the existing entity
        mock_existing = MagicMock()
        mock_existing.id = uuid4()
        mock_existing.name = "München"

        # Make flush raise IntegrityError with the constraint name
        session.flush = AsyncMock(side_effect=IntegrityError(
            "statement",
            {},
            Exception("uq_entity_type_name_normalized violation")
        ))

        # Mock the rollback
        session.rollback = AsyncMock()

        # Mock the session.get for parent lookup
        session.get = AsyncMock(return_value=None)

        with patch.object(service, '_find_by_normalized_name', new_callable=AsyncMock) as mock_find:
            # After IntegrityError and rollback, return existing entity
            mock_find.return_value = mock_existing

            result = await service._create_entity_safe(
                entity_type=mock_entity_type,
                name="München",
                name_normalized="muenchen",
                slug="muenchen",
            )

        # Should return the existing entity after handling the race condition
        assert result is mock_existing
        session.rollback.assert_called_once()
