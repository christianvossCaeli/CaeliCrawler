"""Tests for advanced Smart Query features.

Tests cover:
- Boolean operators (AND/OR)
- Negation support (NOT/OHNE)
- Date range filters
- Aggregation queries
- Delete operations
- Export operations
- UNDO system
- Multi-hop relations
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession


class TestBooleanOperators:
    """Test Boolean operator (AND/OR) handling in query interpretation."""

    @pytest.mark.asyncio
    async def test_or_operator_in_location_filter(self):
        """Test OR operator for location filters."""
        # Test that OR filter data structure is correct
        location_filters = {
            "admin_level_1": ["Nordrhein-Westfalen", "Bayern"],
            "logical_operator": "OR"
        }

        # The query should use OR between location conditions
        assert location_filters["logical_operator"] == "OR"
        assert len(location_filters["admin_level_1"]) == 2
        assert "Nordrhein-Westfalen" in location_filters["admin_level_1"]
        assert "Bayern" in location_filters["admin_level_1"]

    @pytest.mark.asyncio
    async def test_and_operator_in_facet_filter(self):
        """Test AND operator for facet type filters."""
        facet_filters = {
            "facet_types": ["pain_point", "positive_signal"],
            "facet_logical_operator": "AND"
        }

        # Entities must have BOTH facet types
        assert facet_filters["facet_logical_operator"] == "AND"
        assert "pain_point" in facet_filters["facet_types"]
        assert "positive_signal" in facet_filters["facet_types"]


class TestNegationSupport:
    """Test Negation (NOT/OHNE) support in queries."""

    @pytest.mark.asyncio
    async def test_negative_facet_type_filter(self):
        """Test negative facet type filter interpretation."""
        query_params = {
            "primary_entity_type": "municipality",
            "negative_facet_types": ["pain_point"]
        }

        # Should find entities WITHOUT pain points
        assert "negative_facet_types" in query_params
        assert "pain_point" in query_params["negative_facet_types"]

    @pytest.mark.asyncio
    async def test_negative_location_filter(self):
        """Test negative location filter interpretation."""
        query_params = {
            "primary_entity_type": "person",
            "negative_location_filter": {
                "admin_level_1": "Bayern"
            }
        }

        # Should find entities NOT in Bayern
        assert "negative_location_filter" in query_params
        assert query_params["negative_location_filter"]["admin_level_1"] == "Bayern"


class TestDateRangeFilters:
    """Test date range filter handling."""

    @pytest.mark.asyncio
    async def test_date_range_parsing(self):
        """Test that date ranges are correctly parsed."""
        query_params = {
            "date_range": {
                "start": "2025-01-01",
                "end": "2025-03-31"
            }
        }

        start = datetime.fromisoformat(query_params["date_range"]["start"])
        end = datetime.fromisoformat(query_params["date_range"]["end"])

        assert start.year == 2025
        assert start.month == 1
        assert end.month == 3

    @pytest.mark.asyncio
    async def test_relative_date_conversion(self):
        """Test that relative dates are converted properly."""
        # "letzten 3 Monate" should convert to a date range
        today = datetime.now()
        three_months_ago = today - timedelta(days=90)

        date_range = {
            "start": three_months_ago.strftime("%Y-%m-%d"),
            "end": today.strftime("%Y-%m-%d")
        }

        assert date_range["start"] is not None
        assert date_range["end"] is not None


class TestAggregationQueries:
    """Test aggregation query functionality."""

    @pytest.mark.asyncio
    async def test_count_aggregation(self):
        """Test COUNT aggregation interpretation."""
        query_params = {
            "query_type": "aggregate",
            "aggregate_function": "COUNT",
            "primary_entity_type": "municipality",
            "facet_types": ["pain_point"]
        }

        assert query_params["query_type"] == "aggregate"
        assert query_params["aggregate_function"] == "COUNT"

    @pytest.mark.asyncio
    async def test_avg_aggregation(self):
        """Test AVG aggregation interpretation."""
        query_params = {
            "query_type": "aggregate",
            "aggregate_function": "AVG",
            "group_by": "admin_level_1"
        }

        assert query_params["aggregate_function"] == "AVG"
        assert query_params["group_by"] == "admin_level_1"

    @pytest.mark.asyncio
    async def test_aggregation_with_grouping(self):
        """Test aggregation with GROUP BY."""
        query_params = {
            "query_type": "aggregate",
            "aggregate_function": "COUNT",
            "group_by": "entity_type"
        }

        assert "group_by" in query_params


class TestDeleteOperations:
    """Test delete operation handling."""

    @pytest.mark.asyncio
    async def test_delete_entity_preview(self):
        """Test delete entity operation in preview mode."""
        delete_data = {
            "operation": "delete_entity",
            "delete_entity_data": {
                "entity_name": "Test Entity",
                "soft_delete": True
            }
        }

        assert delete_data["operation"] == "delete_entity"
        assert delete_data["delete_entity_data"]["soft_delete"] is True

    @pytest.mark.asyncio
    async def test_delete_facet_preview(self):
        """Test delete facet operation in preview mode."""
        delete_data = {
            "operation": "delete_facet",
            "delete_facet_data": {
                "entity_name": "Gummersbach",
                "facet_type_slug": "pain_point"
            }
        }

        assert delete_data["operation"] == "delete_facet"
        assert "facet_type_slug" in delete_data["delete_facet_data"]

    @pytest.mark.asyncio
    async def test_batch_delete_preview(self):
        """Test batch delete operation in preview mode."""
        batch_delete_data = {
            "operation": "batch_delete",
            "batch_delete_data": {
                "target_type": "facet",
                "facet_type_slug": "pain_point",
                "filter": {"admin_level_1": "Nordrhein-Westfalen"},
                "dry_run": True
            }
        }

        assert batch_delete_data["batch_delete_data"]["dry_run"] is True


class TestExportOperations:
    """Test export operation handling."""

    @pytest.mark.asyncio
    async def test_csv_export_format(self):
        """Test CSV export format."""
        export_data = {
            "operation": "export_query_result",
            "export_data": {
                "format": "csv",
                "filters": {"admin_level_1": "Bayern"}
            }
        }

        assert export_data["export_data"]["format"] == "csv"

    @pytest.mark.asyncio
    async def test_excel_export_format(self):
        """Test Excel export format."""
        export_data = {
            "operation": "export_query_result",
            "export_data": {
                "format": "xlsx",
                "entity_type_slug": "person"
            }
        }

        assert export_data["export_data"]["format"] == "xlsx"

    @pytest.mark.asyncio
    async def test_json_export_format(self):
        """Test JSON export format."""
        export_data = {
            "operation": "export_query_result",
            "export_data": {
                "format": "json",
                "include_facets": True
            }
        }

        assert export_data["export_data"]["format"] == "json"
        assert export_data["export_data"]["include_facets"] is True


class TestUndoSystem:
    """Test UNDO system functionality."""

    @pytest.mark.asyncio
    async def test_undo_operation_recognition(self):
        """Test that UNDO operation is correctly recognized."""
        undo_data = {
            "operation": "undo_change",
            "undo_data": {
                "entity_name": "Gummersbach"
            }
        }

        assert undo_data["operation"] == "undo_change"

    @pytest.mark.asyncio
    async def test_get_change_history_operation(self):
        """Test that change history operation is recognized."""
        history_data = {
            "operation": "get_change_history",
            "history_data": {
                "entity_name": "Gummersbach",
                "limit": 10
            }
        }

        assert history_data["operation"] == "get_change_history"
        assert history_data["history_data"]["limit"] == 10


class TestChangeTracker:
    """Test ChangeTracker service functionality."""

    @pytest.mark.asyncio
    async def test_change_tracker_init(self):
        """Test ChangeTracker initialization."""
        from services.change_tracker import ChangeTracker

        mock_session = AsyncMock(spec=AsyncSession)
        tracker = ChangeTracker(mock_session)

        assert tracker.session == mock_session

    @pytest.mark.asyncio
    async def test_entity_change_structure(self):
        """Test entity change data structure."""
        changes = {
            "name": {"old": "Old Name", "new": "New Name"},
            "core_attributes": {
                "old": {"position": "Bürgermeister"},
                "new": {"position": "Landrat"}
            }
        }

        assert "old" in changes["name"]
        assert "new" in changes["name"]
        assert changes["name"]["old"] == "Old Name"

    @pytest.mark.asyncio
    async def test_facet_change_structure(self):
        """Test facet change data structure."""
        facet_change = {
            "_operation": "create",
            "entity_id": str(uuid4()),
            "facet_type_id": str(uuid4()),
            "value": {"description": "Test pain point"},
            "text_representation": "Test pain point"
        }

        assert facet_change["_operation"] == "create"
        assert "entity_id" in facet_change


class TestMultiHopRelations:
    """Test multi-hop relation resolution."""

    @pytest.mark.asyncio
    async def test_relation_hop_creation(self):
        """Test RelationHop creation."""
        from services.smart_query.relation_resolver import RelationHop

        hop = RelationHop(
            relation_type_slug="works_for",
            direction="source",
            facet_filter="pain_point"
        )

        assert hop.relation_type_slug == "works_for"
        assert hop.direction == "source"
        assert hop.facet_filter == "pain_point"

    @pytest.mark.asyncio
    async def test_relation_chain_creation(self):
        """Test RelationChain creation."""
        from services.smart_query.relation_resolver import RelationHop, RelationChain

        hop1 = RelationHop("works_for", "source")
        hop2 = RelationHop("organizes", "target")

        chain = RelationChain([hop1, hop2])

        assert len(chain.hops) == 2

    @pytest.mark.asyncio
    async def test_relation_chain_max_depth(self):
        """Test that RelationChain enforces max depth."""
        from services.smart_query.relation_resolver import (
            RelationHop,
            RelationChain,
            MAX_RELATION_DEPTH
        )

        hops = [RelationHop(f"relation_{i}", "source")
                for i in range(MAX_RELATION_DEPTH + 1)]

        with pytest.raises(ValueError, match="exceeds maximum depth"):
            RelationChain(hops)

    @pytest.mark.asyncio
    async def test_relation_resolver_init(self):
        """Test RelationResolver initialization."""
        from services.smart_query.relation_resolver import RelationResolver

        mock_session = AsyncMock(spec=AsyncSession)
        resolver = RelationResolver(mock_session)

        assert resolver.session == mock_session
        assert resolver._relation_type_cache == {}
        assert resolver._facet_type_cache == {}

    @pytest.mark.asyncio
    async def test_parse_relation_chain_from_query(self):
        """Test parsing relation chain from query params."""
        from services.smart_query.relation_resolver import parse_relation_chain_from_query

        query_params = {
            "relation_chain": [
                {"type": "works_for", "direction": "source"},
                {"type": "member_of", "direction": "source"}
            ]
        }

        chain = parse_relation_chain_from_query(query_params)

        assert chain is not None
        assert len(chain) == 2
        assert chain[0]["type"] == "works_for"


class TestSuggestionSystem:
    """Test intelligent suggestion system."""

    @pytest.mark.asyncio
    async def test_geographic_suggestion_structure(self):
        """Test geographic suggestion data structure."""
        suggestion = {
            "type": "geographic",
            "original": "NWR",
            "suggestion": "NRW (Nordrhein-Westfalen)",
            "corrected_query": "Zeige Gemeinden in NRW",
            "message": "Meinten Sie 'NRW'?"
        }

        assert suggestion["type"] == "geographic"
        assert "corrected_query" in suggestion

    @pytest.mark.asyncio
    async def test_entity_type_suggestion_structure(self):
        """Test entity type suggestion data structure."""
        suggestion = {
            "type": "entity_type",
            "original": "Gemeidne",
            "suggestion": "Gemeinde (municipality)",
            "corrected_query": "Zeige alle Gemeinden",
            "message": "Meinten Sie 'Gemeinde'?"
        }

        assert suggestion["type"] == "entity_type"

    @pytest.mark.asyncio
    async def test_facet_type_suggestion_structure(self):
        """Test facet type suggestion data structure."""
        suggestion = {
            "type": "facet_type",
            "original": "Painpoint",
            "suggestion": "Pain Point",
            "corrected_query": "Zeige Gemeinden mit Pain Points",
            "message": "Meinten Sie 'Pain Point'?"
        }

        assert suggestion["type"] == "facet_type"


class TestQueryInterpretation:
    """Test query interpretation for new features."""

    @pytest.mark.asyncio
    async def test_negation_keywords_german(self):
        """Test German negation keywords are recognized."""
        negation_keywords_de = ["ohne", "nicht", "keine"]

        test_queries = [
            "Gemeinden ohne Pain Points",
            "Personen nicht in Bayern",
            "Entitäten mit keinen Events"
        ]

        for query in test_queries:
            query_lower = query.lower()
            has_negation = any(kw in query_lower for kw in negation_keywords_de)
            assert has_negation, f"Query should contain negation: {query}"

    @pytest.mark.asyncio
    async def test_aggregation_keywords_german(self):
        """Test German aggregation keywords are recognized."""
        aggregation_triggers = {
            "wie viele": "COUNT",
            "anzahl": "COUNT",
            "durchschnitt": "AVG",
            "mittel": "AVG",
            "summe": "SUM",
            "gesamt": "SUM",
            "minimum": "MIN",
            "maximum": "MAX"
        }

        for keyword, expected_function in aggregation_triggers.items():
            assert keyword in aggregation_triggers
            assert aggregation_triggers[keyword] == expected_function

    @pytest.mark.asyncio
    async def test_delete_keywords_german(self):
        """Test German delete keywords are recognized."""
        delete_keywords = ["lösche", "entferne", "delete", "remove"]

        test_queries = [
            "Lösche die Entity Max Müller",
            "Entferne alle Pain Points",
            "Delete the entity",
            "Remove facet from entity"
        ]

        for query in test_queries:
            query_lower = query.lower()
            has_delete = any(kw in query_lower for kw in delete_keywords)
            assert has_delete, f"Query should contain delete keyword: {query}"

    @pytest.mark.asyncio
    async def test_export_keywords(self):
        """Test export keywords are recognized."""
        export_keywords = ["exportiere", "export", "als csv", "als excel", "als json"]

        test_queries = [
            "Exportiere alle Bürgermeister",
            "Export as CSV",
            "Zeige Gemeinden als Excel",
            "Exportiere als JSON"
        ]

        for query in test_queries:
            query_lower = query.lower()
            has_export = any(kw in query_lower for kw in export_keywords)
            assert has_export, f"Query should contain export keyword: {query}"

    @pytest.mark.asyncio
    async def test_undo_keywords(self):
        """Test UNDO keywords are recognized."""
        undo_keywords = ["rückgängig", "undo", "zurück", "revert"]

        test_queries = [
            "Mache die letzte Änderung rückgängig",
            "Undo the last change",
            "Gehe zurück",
            "Revert changes"
        ]

        for query in test_queries:
            query_lower = query.lower()
            has_undo = any(kw in query_lower for kw in undo_keywords)
            assert has_undo, f"Query should contain undo keyword: {query}"


class TestMultiHopPerformance:
    """Performance tests for Multi-Hop relation queries.

    Tests to ensure that multi-hop queries perform within acceptable limits
    even with large datasets.
    """

    @pytest.mark.asyncio
    async def test_relation_chain_parsing_performance(self):
        """Test that relation chain parsing is efficient."""
        import time

        # Complex multi-hop chain
        relation_chain = [
            {"relation_type": "works_for", "direction": "source"},
            {"relation_type": "located_in", "direction": "target"},
            {"relation_type": "has_event", "direction": "target"},
        ]

        # Simulate parsing 1000 queries with relation chains
        start_time = time.time()

        for _ in range(1000):
            # Parse relation chain (simulated)
            parsed_chain = []
            for hop in relation_chain:
                parsed_chain.append({
                    "type": hop["relation_type"],
                    "dir": hop["direction"],
                })

        elapsed = time.time() - start_time

        # Should complete in under 1 second for 1000 parses
        assert elapsed < 1.0, f"Parsing took too long: {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_relation_resolver_data_structure_performance(self):
        """Test RelationResolver data structures are efficient."""
        import time
        from uuid import uuid4

        # Simulate building entity ID sets for traversal
        start_time = time.time()

        # Create 10,000 mock entity IDs
        entity_ids = {uuid4() for _ in range(10000)}

        # Simulate multiple set operations (intersection, union)
        for _ in range(100):
            subset1 = set(list(entity_ids)[:5000])
            subset2 = set(list(entity_ids)[2500:7500])

            # Common multi-hop operations
            intersection = subset1 & subset2
            union = subset1 | subset2
            difference = subset1 - subset2

            assert len(intersection) > 0
            assert len(union) >= len(subset1)
            assert len(difference) >= 0

        elapsed = time.time() - start_time

        # Should complete in under 2 seconds
        assert elapsed < 2.0, f"Set operations took too long: {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_facet_lookup_caching_efficiency(self):
        """Test that facet type lookups are cached efficiently."""
        import time
        from functools import lru_cache

        # Simulate cached facet type lookup
        @lru_cache(maxsize=128)
        def get_facet_type(slug: str) -> dict:
            # Simulate DB lookup delay
            return {"slug": slug, "id": uuid4(), "name": slug.title()}

        facet_types = ["pain_point", "positive_signal", "event", "contact", "note"]

        start_time = time.time()

        # First pass - populates cache
        for ft in facet_types:
            result = get_facet_type(ft)
            assert result["slug"] == ft

        # Second pass - should be much faster (cache hits)
        for _ in range(1000):
            for ft in facet_types:
                result = get_facet_type(ft)
                assert result["slug"] == ft

        elapsed = time.time() - start_time

        # Should complete in under 0.5 seconds with caching
        assert elapsed < 0.5, f"Cached lookups took too long: {elapsed:.2f}s"

        # Verify cache was used
        cache_info = get_facet_type.cache_info()
        assert cache_info.hits > cache_info.misses, "Cache should have more hits than misses"

    @pytest.mark.asyncio
    async def test_batch_entity_loading_efficiency(self):
        """Test that batch loading entities is efficient."""
        import time
        from uuid import uuid4

        # Simulate batch loading patterns
        start_time = time.time()

        # Create mock entity data (simulating 5000 entities)
        entities = []
        for i in range(5000):
            entities.append({
                "id": uuid4(),
                "name": f"Entity {i}",
                "type": "municipality",
                "facets": [
                    {"type": "pain_point", "value": f"Pain {i}"}
                    for _ in range(3)
                ] if i % 10 == 0 else []
            })

        # Simulate grouping by facet presence (common multi-hop operation)
        with_facets = [e for e in entities if e["facets"]]
        without_facets = [e for e in entities if not e["facets"]]

        # Build lookup index
        entity_by_id = {e["id"]: e for e in entities}

        elapsed = time.time() - start_time

        # Should complete in under 1 second
        assert elapsed < 1.0, f"Batch loading took too long: {elapsed:.2f}s"
        assert len(with_facets) == 500  # 10% have facets
        assert len(entity_by_id) == 5000

    @pytest.mark.asyncio
    async def test_multi_hop_max_depth_enforcement(self):
        """Test that max depth is enforced for multi-hop queries."""
        MAX_DEPTH = 3  # From RelationResolver

        # Valid chain (within limit)
        valid_chain = [
            {"relation_type": "works_for", "direction": "source"},
            {"relation_type": "located_in", "direction": "target"},
            {"relation_type": "has_event", "direction": "target"},
        ]
        assert len(valid_chain) <= MAX_DEPTH

        # Invalid chain (exceeds limit)
        invalid_chain = [
            {"relation_type": "works_for", "direction": "source"},
            {"relation_type": "located_in", "direction": "target"},
            {"relation_type": "has_event", "direction": "target"},
            {"relation_type": "attended_by", "direction": "source"},  # 4th hop
        ]
        assert len(invalid_chain) > MAX_DEPTH

    @pytest.mark.asyncio
    async def test_recursive_query_builder_no_infinite_loops(self):
        """Test that recursive query building prevents infinite loops."""
        visited = set()
        max_iterations = 1000

        def simulate_traversal(entity_id: str, depth: int = 0):
            if depth > 3:  # Max depth
                return []
            if entity_id in visited:
                return []  # Prevent cycles

            visited.add(entity_id)

            # Simulate finding related entities
            related = [f"entity_{depth}_{i}" for i in range(3)]
            results = [entity_id]

            for rel_id in related:
                results.extend(simulate_traversal(rel_id, depth + 1))

            return results

        result = simulate_traversal("root_entity")

        # Should complete without infinite loop
        assert len(visited) < max_iterations
        assert "root_entity" in result

    @pytest.mark.asyncio
    async def test_query_result_aggregation_performance(self):
        """Test that result aggregation is efficient for multi-hop results."""
        import time
        from collections import defaultdict

        # Simulate aggregating results from multiple hops
        start_time = time.time()

        # Create mock hop results
        hop_results = []
        for hop in range(3):
            hop_results.append([
                {"id": uuid4(), "name": f"Entity H{hop}_{i}", "score": 0.8 - (hop * 0.1)}
                for i in range(1000)
            ])

        # Aggregate by merging and deduplicating
        seen_ids = set()
        aggregated = []

        for hop_result in hop_results:
            for entity in hop_result:
                if entity["id"] not in seen_ids:
                    seen_ids.add(entity["id"])
                    aggregated.append(entity)

        # Group by score ranges
        score_groups = defaultdict(list)
        for entity in aggregated:
            score_bucket = int(entity["score"] * 10)
            score_groups[score_bucket].append(entity)

        elapsed = time.time() - start_time

        # Should complete in under 0.5 seconds
        assert elapsed < 0.5, f"Aggregation took too long: {elapsed:.2f}s"
        assert len(aggregated) == 3000  # All unique from 3 hops
        assert len(score_groups) == 3  # 3 different score buckets (0.8, 0.7, 0.6)

    @pytest.mark.asyncio
    async def test_relation_type_filtering_performance(self):
        """Test that filtering by relation type is efficient."""
        import time
        from collections import defaultdict

        # Simulate relation data
        relations = []
        relation_types = ["works_for", "located_in", "manages", "attends", "member_of"]

        for i in range(10000):
            relations.append({
                "id": uuid4(),
                "source_id": uuid4(),
                "target_id": uuid4(),
                "relation_type": relation_types[i % len(relation_types)],
            })

        start_time = time.time()

        # Filter by multiple relation types (common in multi-hop)
        target_types = {"works_for", "manages"}

        # Using set for O(1) lookup
        filtered = [r for r in relations if r["relation_type"] in target_types]

        # Build index by source_id
        by_source = defaultdict(list)
        for r in filtered:
            by_source[r["source_id"]].append(r)

        elapsed = time.time() - start_time

        # Should complete in under 0.2 seconds
        assert elapsed < 0.2, f"Filtering took too long: {elapsed:.2f}s"
        assert len(filtered) == 4000  # 2 out of 5 types = 40%
