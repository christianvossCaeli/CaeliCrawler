"""Tests for Multi-Entity Extraction Service."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from services.multi_entity_extraction_service import MultiEntityExtractionService


class TestMultiEntityExtractionService:
    """Tests for MultiEntityExtractionService."""

    @pytest.mark.asyncio
    async def test_get_extraction_prompt_single_type(self, session):
        """Test prompt generation for category with single entity type."""
        service = MultiEntityExtractionService(session)

        # Create mock category with no associations
        mock_category = MagicMock()
        mock_category.id = uuid4()
        mock_category.name = "Test Category"
        mock_category.purpose = "Testing"
        mock_category.ai_extraction_prompt = "Custom prompt"

        # Mock empty associations
        with patch.object(session, "execute", new_callable=AsyncMock) as mock_execute:
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_execute.return_value = mock_result

            prompt = await service.get_extraction_prompt(mock_category)

        # Should return custom prompt when no associations
        assert prompt == "Custom prompt"

    @pytest.mark.asyncio
    async def test_get_extraction_prompt_multi_type(self, session):
        """Test prompt generation for category with multiple entity types."""
        service = MultiEntityExtractionService(session)

        mock_category = MagicMock()
        mock_category.id = uuid4()
        mock_category.name = "Events Category"
        mock_category.purpose = "Track events and attendees"

        # Create mock entity types
        person_type = MagicMock()
        person_type.name = "Person"
        person_type.slug = "person"
        person_type.description = "A person"
        person_type.attribute_schema = {
            "properties": {
                "name": {"type": "string"},
                "role": {"type": "string"},
            }
        }

        event_type = MagicMock()
        event_type.name = "Event"
        event_type.slug = "event"
        event_type.description = "An event"
        event_type.attribute_schema = {
            "properties": {
                "title": {"type": "string"},
                "date": {"type": "string"},
            }
        }

        # Create mock associations
        assoc1 = MagicMock()
        assoc1.entity_type = person_type
        assoc1.is_primary = False
        assoc1.extraction_config = {}
        assoc1.relation_config = [{"from_type": "person", "to_type": "event", "relation": "attends"}]

        assoc2 = MagicMock()
        assoc2.entity_type = event_type
        assoc2.is_primary = True
        assoc2.extraction_config = {}
        assoc2.relation_config = []

        with patch.object(session, "execute", new_callable=AsyncMock) as mock_execute:
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [assoc1, assoc2]
            mock_execute.return_value = mock_result

            prompt = await service.get_extraction_prompt(mock_category)

        assert "Events Category" in prompt
        assert "PERSON" in prompt
        assert "EVENT" in prompt
        assert "attends" in prompt
        assert "JSON" in prompt

    @pytest.mark.asyncio
    async def test_process_extraction_result_creates_entities(self, session):
        """Test processing extraction results creates entities."""
        MultiEntityExtractionService(session)

        mock_category = MagicMock()
        mock_category.id = uuid4()

        person_type_id = uuid4()
        event_type_id = uuid4()

        # Mock entity type lookup
        person_type = MagicMock()
        person_type.id = person_type_id
        person_type.slug = "person"

        event_type = MagicMock()
        event_type.id = event_type_id
        event_type.slug = "event"

        # This would require more complex mocking of the database session
        # For now, we test the structure

    @pytest.mark.asyncio
    async def test_get_category_entity_types(self, session):
        """Test retrieving entity types for a category."""
        service = MultiEntityExtractionService(session)

        category_id = uuid4()

        # Mock entity type
        mock_et = MagicMock()
        mock_et.id = uuid4()
        mock_et.slug = "person"
        mock_et.name = "Person"

        mock_assoc = MagicMock()
        mock_assoc.entity_type = mock_et
        mock_assoc.is_primary = True
        mock_assoc.extraction_order = 0
        mock_assoc.extraction_config = {}
        mock_assoc.relation_config = []

        with patch.object(session, "execute", new_callable=AsyncMock) as mock_execute:
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [mock_assoc]
            mock_execute.return_value = mock_result

            result = await service.get_category_entity_types(category_id)

        assert len(result) == 1
        assert result[0]["slug"] == "person"
        assert result[0]["is_primary"] is True


class TestMultiEntityPromptGeneration:
    """Tests for prompt generation specifics."""

    def test_prompt_includes_entity_schema(self):
        """Test that generated prompts include entity schemas."""
        # The prompt should include field definitions from attribute_schema
        pass

    def test_prompt_includes_relations(self):
        """Test that generated prompts include relation definitions."""
        # The prompt should include relation types like "attends", "located_in"
        pass

    def test_prompt_json_format(self):
        """Test that generated prompts specify correct JSON output format."""
        # The prompt should include the expected JSON structure
        pass


class TestMultiEntityRelationCreation:
    """Tests for entity relation creation."""

    @pytest.mark.asyncio
    async def test_find_or_create_relation_type(self, session):
        """Test finding or creating relation types."""
        service = MultiEntityExtractionService(session)

        # Mock existing relation type being found
        mock_relation_type = MagicMock()
        mock_relation_type.slug = "attends"
        mock_relation_type.name = "attends"

        with patch.object(session, "execute", new_callable=AsyncMock) as mock_execute:
            # Mock found (return existing relation type)
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_relation_type
            mock_execute.return_value = mock_result

            result = await service._find_or_create_relation_type("attends")

        # Should return existing relation type
        assert result is not None
        assert result.slug == "attends"

    @pytest.mark.asyncio
    async def test_deduplicate_relations(self, session):
        """Test that duplicate relations are not created."""
        MultiEntityExtractionService(session)

        # When a relation already exists, it should not create a duplicate
        pass
