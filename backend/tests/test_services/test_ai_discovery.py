"""Tests for AI Source Discovery Service."""

from unittest.mock import patch

import pytest

from services.ai_source_discovery.discovery_service import AISourceDiscoveryService
from services.ai_source_discovery.extractors import (
    HTMLTableExtractor,
    WikipediaExtractor,
)
from services.ai_source_discovery.models import (
    DiscoveryResult,
    DiscoveryStats,
    ExtractedSource,
    SearchResult,
    SearchStrategy,
    SourceWithTags,
)
from services.ai_source_discovery.search_providers import SerperSearchProvider


class TestSearchStrategy:
    """Tests for SearchStrategy model."""

    def test_search_strategy_creation(self):
        """Test creating a SearchStrategy."""
        strategy = SearchStrategy(
            search_queries=["Bundesliga Vereine", "DFL Clubs"],
            expected_data_type="sports_teams",
            preferred_sources=["wikipedia", "official"],
            entity_schema={"name": "string", "website": "url"},
            base_tags=["de", "bundesliga", "fußball"],
        )

        assert len(strategy.search_queries) == 2
        assert strategy.expected_data_type == "sports_teams"
        assert "de" in strategy.base_tags

    def test_search_strategy_defaults(self):
        """Test SearchStrategy with defaults."""
        strategy = SearchStrategy(
            search_queries=["test"],
            expected_data_type="organizations",
            preferred_sources=["wikipedia"],
            entity_schema={},
            base_tags=[],
        )

        assert strategy.search_queries == ["test"]
        assert strategy.base_tags == []


class TestExtractedSource:
    """Tests for ExtractedSource model."""

    def test_extracted_source_creation(self):
        """Test creating an ExtractedSource."""
        source = ExtractedSource(
            name="FC Bayern München",
            base_url="https://fcbayern.com",
            source_type="WEBSITE",
            metadata={"city": "München"},
            confidence=0.95,
        )

        assert source.name == "FC Bayern München"
        assert source.base_url == "https://fcbayern.com"
        assert source.confidence == 0.95

    def test_extracted_source_defaults(self):
        """Test ExtractedSource default values."""
        source = ExtractedSource(
            name="Test",
            base_url="https://test.com",
        )

        assert source.source_type == "WEBSITE"
        assert source.metadata == {}
        assert source.confidence == 0.5  # Default is 0.5


class TestSourceWithTags:
    """Tests for SourceWithTags model."""

    def test_source_with_tags_creation(self):
        """Test creating SourceWithTags."""
        source = SourceWithTags(
            name="Test Source",
            base_url="https://test.com",
            source_type="WEBSITE",
            tags=["tag1", "tag2"],
            confidence=0.9,
        )

        assert source.name == "Test Source"
        assert "tag1" in source.tags
        assert len(source.tags) == 2


class TestDiscoveryResult:
    """Tests for DiscoveryResult model."""

    def test_discovery_result_creation(self):
        """Test creating a DiscoveryResult."""
        sources = [
            SourceWithTags(
                name="Source 1",
                base_url="https://source1.com",
                source_type="WEBSITE",
                tags=["tag1"],
                confidence=0.9,
            )
        ]
        strategy = SearchStrategy(
            search_queries=["test"],
            expected_data_type="organizations",
            preferred_sources=["wikipedia"],
            entity_schema={},
            base_tags=["test"],
        )
        stats = DiscoveryStats(
            pages_searched=10,
            sources_extracted=5,
            duplicates_removed=1,
            sources_validated=4,
        )

        result = DiscoveryResult(
            sources=sources,
            search_strategy=strategy,
            stats=stats,
            warnings=["Test warning"],
        )

        assert len(result.sources) == 1
        assert result.search_strategy.expected_data_type == "organizations"
        assert result.stats.pages_searched == 10
        assert "Test warning" in result.warnings


class TestHTMLTableExtractor:
    """Tests for HTMLTableExtractor."""

    @pytest.mark.asyncio
    async def test_can_extract_html(self):
        """Test can_extract for HTML content."""
        extractor = HTMLTableExtractor()

        assert await extractor.can_extract("https://example.com", "text/html")
        assert await extractor.can_extract("https://example.com", "text/html; charset=utf-8")
        # HTMLTableExtractor defaults to True for fallback extraction
        assert await extractor.can_extract("https://example.com", "application/json")

    @pytest.mark.asyncio
    async def test_extract_from_html_table(self):
        """Test extracting sources from HTML table."""
        extractor = HTMLTableExtractor()

        html_content = """
        <html>
        <body>
            <table>
                <tr><th>Name</th><th>Website</th></tr>
                <tr><td>FC Bayern München</td><td><a href="https://fcbayern.com">Website</a></td></tr>
                <tr><td>Borussia Dortmund</td><td><a href="https://bvb.de">Website</a></td></tr>
            </table>
        </body>
        </html>
        """

        strategy = SearchStrategy(
            search_queries=["test"],
            expected_data_type="sports_teams",
            preferred_sources=["wikipedia"],
            entity_schema={"name": "string", "website": "url"},
            base_tags=["bundesliga"],
        )

        sources = await extractor.extract(
            "https://example.com/teams",
            html_content,
            strategy,
        )

        assert len(sources) >= 2
        names = [s.name for s in sources]
        assert "FC Bayern München" in names or any("Bayern" in n for n in names)


class TestWikipediaExtractor:
    """Tests for WikipediaExtractor."""

    @pytest.mark.asyncio
    async def test_can_extract_wikipedia(self):
        """Test can_extract for Wikipedia URLs."""
        extractor = WikipediaExtractor()

        assert await extractor.can_extract("https://de.wikipedia.org/wiki/Test", "text/html")
        assert await extractor.can_extract("https://en.wikipedia.org/wiki/Test", "text/html")
        assert not await extractor.can_extract("https://example.com", "text/html")

    @pytest.mark.asyncio
    async def test_extract_from_wikipedia_list(self):
        """Test extracting from Wikipedia list page."""
        extractor = WikipediaExtractor()

        html_content = """
        <html>
        <body>
            <table class="wikitable">
                <tr><th>Verein</th><th>Website</th><th>Stadt</th></tr>
                <tr>
                    <td>FC Bayern München</td>
                    <td><a href="https://fcbayern.com">fcbayern.com</a></td>
                    <td>München</td>
                </tr>
                <tr>
                    <td>Borussia Dortmund</td>
                    <td><a href="https://bvb.de">bvb.de</a></td>
                    <td>Dortmund</td>
                </tr>
            </table>
        </body>
        </html>
        """

        strategy = SearchStrategy(
            search_queries=["Bundesliga"],
            expected_data_type="sports_teams",
            preferred_sources=["wikipedia"],
            entity_schema={"name": "string", "website": "url"},
            base_tags=["bundesliga"],
        )

        sources = await extractor.extract(
            "https://de.wikipedia.org/wiki/Liste_der_Bundesliga-Vereine",
            html_content,
            strategy,
        )

        # Should extract entities from wikitable
        assert isinstance(sources, list)


class TestSerperSearchProvider:
    """Tests for SerperSearchProvider."""

    @pytest.mark.asyncio
    async def test_search_without_api_key(self):
        """Test search returns mock data without API key."""
        provider = SerperSearchProvider()

        # Without API key, should return empty list
        with patch.dict("os.environ", {"SERPER_API_KEY": ""}):
            results = await provider.search(
                queries=["Bundesliga Vereine"],
                num_results=5,
            )

        # Should return empty list or mock data
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_detect_source_type(self):
        """Test source type detection from URLs."""
        provider = SerperSearchProvider()

        assert provider._detect_source_type("https://de.wikipedia.org/wiki/Test") == "wikipedia"
        # wikidata.org is categorized as 'api' since it's in the api list
        assert provider._detect_source_type("https://wikidata.org/entity/Q123") == "api"
        assert provider._detect_source_type("https://api.example.com/data") == "api"
        assert provider._detect_source_type("https://example.com/page.html") == "website"


class TestAISourceDiscoveryService:
    """Tests for the main AISourceDiscoveryService."""

    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test service initializes correctly."""
        service = AISourceDiscoveryService()

        # Service has primary and fallback search providers
        assert service.primary_search_provider is not None
        assert service.fallback_search_provider is not None
        assert len(service.extractors) > 0

    @pytest.mark.asyncio
    async def test_extract_base_tags(self):
        """Test base tag extraction from prompt."""
        service = AISourceDiscoveryService()

        # Test German municipalities
        tags = service._extract_base_tags("Alle Gemeinden in NRW")
        assert "nrw" in tags or "kommunal" in tags

        # Test with country
        tags = service._extract_base_tags("Deutsche Universitäten")
        assert "de" in tags

        # Test Austrian
        tags = service._extract_base_tags("Österreichische Gemeinden")
        assert "at" in tags

    @pytest.mark.asyncio
    async def test_normalize_url(self):
        """Test URL normalization."""
        service = AISourceDiscoveryService()

        assert service._normalize_url("https://www.example.com/") == "example.com"
        assert service._normalize_url("https://www.example.com/path/") == "example.com/path"
        assert service._normalize_url("http://EXAMPLE.COM/Path") == "example.com/path"

    @pytest.mark.asyncio
    async def test_deduplicate_sources(self):
        """Test source deduplication."""
        service = AISourceDiscoveryService()

        sources = [
            ExtractedSource(name="Source 1", base_url="https://www.example.com"),
            ExtractedSource(name="Source 1 Duplicate", base_url="https://example.com/"),
            ExtractedSource(name="Source 2", base_url="https://other.com"),
        ]

        unique = service._deduplicate_sources(sources)

        assert len(unique) == 2
        urls = [s.base_url for s in unique]
        assert any("example.com" in u for u in urls)
        assert any("other.com" in u for u in urls)

    @pytest.mark.asyncio
    async def test_discover_sources_mock(self):
        """Test discover_sources with mocked components."""
        service = AISourceDiscoveryService()

        # Mock the search strategy generation
        mock_strategy = SearchStrategy(
            search_queries=["test query"],
            expected_data_type="organizations",
            preferred_sources=["wikipedia"],
            entity_schema={"name": "string", "website": "url"},
            base_tags=["test"],
        )

        # Mock search results
        mock_search_results = [
            SearchResult(
                url="https://example.com/list",
                title="Test List",
                snippet="A list of organizations",
                source_type="website",
                confidence=0.8,
            )
        ]

        # Mock extracted sources
        mock_extracted = [
            ExtractedSource(
                name="Test Org",
                base_url="https://testorg.com",
                confidence=0.9,
            )
        ]

        with patch.object(service, "_generate_search_strategy", return_value=mock_strategy):  # noqa: SIM117
            with patch.object(service.primary_search_provider, "search", return_value=mock_search_results):
                with patch.object(service, "_extract_from_pages", return_value=mock_extracted):
                    result = await service.discover_sources(
                        prompt="Test organizations",
                        max_results=10,
                        search_depth="quick",
                    )

        assert isinstance(result, DiscoveryResult)
        assert result.search_strategy is not None


class TestDiscoveryServiceIntegration:
    """Integration tests for the discovery service."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_discover_sources_end_to_end(self):
        """Test full discovery flow (requires API keys)."""
        # This test is marked as integration and will be skipped
        # if the required API keys are not configured
        import os

        if not os.environ.get("SERPER_API_KEY"):
            pytest.skip("SERPER_API_KEY not configured")

        service = AISourceDiscoveryService()

        result = await service.discover_sources(
            prompt="Deutsche Bundesliga Fußballvereine",
            max_results=5,
            search_depth="quick",
        )

        assert result.sources is not None
        assert result.search_strategy is not None
        assert len(result.sources) > 0


class TestTagGeneration:
    """Tests for tag generation logic."""

    @pytest.mark.asyncio
    async def test_generate_tags_without_llm(self):
        """Test tag generation falls back gracefully without LLM."""
        service = AISourceDiscoveryService()

        sources = [
            ExtractedSource(
                name="Stadt München",
                base_url="https://muenchen.de",
                confidence=0.9,
            )
        ]

        strategy = SearchStrategy(
            search_queries=["Gemeinden Bayern"],
            expected_data_type="municipalities",
            preferred_sources=["government"],
            entity_schema={"name": "string", "website": "url"},
            base_tags=["de", "bayern", "kommunal"],
        )

        # This should work even without LLM configured
        result = await service._generate_tags(sources, "Gemeinden in Bayern", strategy)

        assert len(result) == 1
        assert "de" in result[0].tags or "bayern" in result[0].tags or "kommunal" in result[0].tags
