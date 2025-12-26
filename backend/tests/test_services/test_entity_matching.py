"""Tests for Entity Matching Service - Composite Entity Detection."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from services.entity_matching_service import (
    EntityMatchingService,
    detect_composite_entity_name,
    CompositeEntityMatch,
)


class TestCompositeEntityDetection:
    """Tests for composite entity name detection."""

    def test_gemeinden_und_pattern(self):
        """Test detection of 'Gemeinden X und Y' pattern."""
        result = detect_composite_entity_name(
            "Region Oberfranken-West, Gemeinden Litzendorf und Buttenheim, Landkreis Bamberg"
        )
        assert result.is_composite is True
        assert result.pattern_type == "gemeinden_und"
        assert "Litzendorf" in result.extracted_names
        assert "Buttenheim" in result.extracted_names

    def test_region_gemeinde_pattern(self):
        """Test detection of 'Region X, Gemeinde Y' pattern."""
        result = detect_composite_entity_name(
            "Region Oberfranken-West, Gemeinde Litzendorf"
        )
        assert result.is_composite is True
        assert result.pattern_type == "region_gemeinde"
        assert "Litzendorf" in result.extracted_names

    def test_region_stadt_pattern(self):
        """Test detection of 'Region X, Stadt Y' pattern."""
        result = detect_composite_entity_name(
            "Region Oberfranken-Ost, Stadt Creußen, Landkreis Bayreuth"
        )
        assert result.is_composite is True
        assert result.pattern_type == "region_gemeinde"
        assert "Creußen" in result.extracted_names

    def test_region_markt_pattern(self):
        """Test detection of 'Region X, Markt Y' pattern."""
        result = detect_composite_entity_name(
            "Region Oberfranken-Ost, Markt Schnabelwaid, Landkreis Bayreuth"
        )
        assert result.is_composite is True
        assert result.pattern_type == "region_gemeinde"
        assert "Schnabelwaid" in result.extracted_names

    def test_insbesondere_pattern(self):
        """Test detection of 'insbesondere Gemeinde X' pattern."""
        result = detect_composite_entity_name(
            "Region Oberfranken-West, insbesondere Gemeinde Bad Rodach, Landkreis Coburg"
        )
        assert result.is_composite is True
        assert result.pattern_type == "insbesondere"
        assert "Bad Rodach" in result.extracted_names

    def test_normal_entity_name(self):
        """Test that normal entity names are not detected as composite."""
        result = detect_composite_entity_name("München")
        assert result.is_composite is False
        assert result.extracted_names == []

        result = detect_composite_entity_name("Markt Buttenheim")
        assert result.is_composite is False
        assert result.extracted_names == []

        result = detect_composite_entity_name("Litzendorf")
        assert result.is_composite is False
        assert result.extracted_names == []

    def test_region_without_gemeinde(self):
        """Test that region names without Gemeinde/Stadt/Markt are not composite."""
        result = detect_composite_entity_name("Region Oberfranken-West")
        assert result.is_composite is False

    def test_staedte_und_pattern(self):
        """Test detection of 'Städte X und Y' pattern."""
        result = detect_composite_entity_name(
            "Städte München und Augsburg"
        )
        assert result.is_composite is True
        assert result.pattern_type == "gemeinden_und"
        assert "München" in result.extracted_names
        assert "Augsburg" in result.extracted_names

    def test_gemeinde_singular_und_pattern(self):
        """Test detection of 'Gemeinde X und Y' (singular) pattern."""
        result = detect_composite_entity_name(
            "Gemeinde Haag und Creußen"
        )
        assert result.is_composite is True
        assert result.pattern_type == "gemeinden_und"
        assert "Haag" in result.extracted_names
        assert "Creußen" in result.extracted_names

    def test_cleans_trailing_landkreis(self):
        """Test that trailing Landkreis info is cleaned from extracted names."""
        result = detect_composite_entity_name(
            "Gemeinden Litzendorf und Buttenheim, Landkreis Bamberg"
        )
        assert result.is_composite is True
        # Should not include "Landkreis Bamberg" in the second name
        assert "Buttenheim" in result.extracted_names
        assert not any("Landkreis" in name for name in result.extracted_names)

    def test_speziell_pattern(self):
        """Test detection of 'speziell Gemeinde X' pattern."""
        result = detect_composite_entity_name(
            "Region Bayern, speziell Gemeinde Rosenheim"
        )
        assert result.is_composite is True
        assert result.pattern_type == "insbesondere"
        assert "Rosenheim" in result.extracted_names


class TestCompositeEntityResolution:
    """Tests for composite entity resolution in EntityMatchingService."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()
        session.get = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_composite_entity_resolved_to_existing(self, mock_session):
        """Test that composite names are resolved to existing entities."""
        service = EntityMatchingService(mock_session)

        entity_type_id = uuid4()
        existing_entity_id = uuid4()

        mock_entity_type = MagicMock()
        mock_entity_type.id = entity_type_id
        mock_entity_type.slug = "territorial_entity"

        mock_existing_entity = MagicMock()
        mock_existing_entity.id = existing_entity_id
        mock_existing_entity.name = "Litzendorf"

        with patch.object(service, '_get_entity_type', new_callable=AsyncMock) as mock_get_type:
            mock_get_type.return_value = mock_entity_type

            with patch.object(service, '_find_by_normalized_name', new_callable=AsyncMock) as mock_find:
                # First call for exact match returns None
                # Second call for composite resolution returns existing entity
                mock_find.side_effect = [None, mock_existing_entity]

                with patch.object(service, '_resolve_composite_entity', new_callable=AsyncMock) as mock_resolve:
                    mock_resolve.return_value = mock_existing_entity

                    result = await service.get_or_create_entity(
                        entity_type_slug="territorial_entity",
                        name="Region Oberfranken-West, Gemeinde Litzendorf",
                    )

        assert result is not None
        assert result.id == existing_entity_id
        assert result.name == "Litzendorf"

    @pytest.mark.asyncio
    async def test_composite_entity_creates_new_if_no_components_exist(self, mock_session):
        """Test that new entity is created if no component entities exist."""
        service = EntityMatchingService(mock_session)

        entity_type_id = uuid4()

        mock_entity_type = MagicMock()
        mock_entity_type.id = entity_type_id
        mock_entity_type.slug = "territorial_entity"

        with patch.object(service, '_get_entity_type', new_callable=AsyncMock) as mock_get_type:
            mock_get_type.return_value = mock_entity_type

            with patch.object(service, '_find_by_normalized_name', new_callable=AsyncMock) as mock_find:
                mock_find.return_value = None

                with patch.object(service, '_resolve_composite_entity', new_callable=AsyncMock) as mock_resolve:
                    mock_resolve.return_value = None

                    with patch.object(service, '_create_entity_safe', new_callable=AsyncMock) as mock_create:
                        mock_new_entity = MagicMock()
                        mock_new_entity.id = uuid4()
                        mock_new_entity.name = "Region X, Gemeinde New"
                        mock_create.return_value = mock_new_entity

                        result = await service.get_or_create_entity(
                            entity_type_slug="territorial_entity",
                            name="Region X, Gemeinde New",
                        )

        assert result is not None
        mock_create.assert_called_once()


class TestEntityMatchingServiceBasic:
    """Basic tests for the EntityMatchingService."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()
        session.get = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_get_or_create_entity_finds_existing(self, mock_session):
        """Test that existing entity is found."""
        service = EntityMatchingService(mock_session)

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
    async def test_get_or_create_entity_returns_none_for_invalid_type(self, mock_session):
        """Test that None is returned for invalid entity type."""
        service = EntityMatchingService(mock_session)

        with patch.object(service, '_get_entity_type', new_callable=AsyncMock) as mock_get_type:
            mock_get_type.return_value = None

            result = await service.get_or_create_entity(
                entity_type_slug="nonexistent",
                name="Test Entity",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_or_create_entity_creates_new(self, mock_session):
        """Test that new entity is created when not found."""
        service = EntityMatchingService(mock_session)

        entity_type_id = uuid4()

        # Mock entity type
        mock_entity_type = MagicMock()
        mock_entity_type.id = entity_type_id
        mock_entity_type.slug = "territorial_entity"

        with patch.object(service, '_get_entity_type', new_callable=AsyncMock) as mock_get_type:
            mock_get_type.return_value = mock_entity_type

            with patch.object(service, '_find_by_normalized_name', new_callable=AsyncMock) as mock_find:
                mock_find.return_value = None

                with patch.object(service, '_resolve_composite_entity', new_callable=AsyncMock) as mock_resolve:
                    mock_resolve.return_value = None

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
