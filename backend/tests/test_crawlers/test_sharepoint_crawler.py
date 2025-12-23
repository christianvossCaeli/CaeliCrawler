"""Tests for SharePoint crawler functionality."""

import pytest

from crawlers.sharepoint_crawler import SharePointCrawler
from external_apis.clients.sharepoint_client import SharePointFile


class TestSharePointCrawlerFilterFiles:
    """Tests for SharePointCrawler._filter_files method."""

    @pytest.fixture
    def crawler(self):
        """Create a SharePointCrawler instance."""
        return SharePointCrawler()

    @pytest.fixture
    def sample_files(self):
        """Create sample SharePointFile objects for testing."""
        base_kwargs = {
            "size": 1000,
            "mime_type": "application/pdf",
            "web_url": "https://test.sharepoint.com/file",
            "download_url": None,
            "created_at": None,
            "modified_at": None,
            "created_by": None,
            "modified_by": None,
            "parent_path": "/",
            "site_id": "site-1",
            "drive_id": "drive-1",
        }
        return [
            SharePointFile(id="1", name="report.pdf", **base_kwargs),
            SharePointFile(id="2", name="~$temp.docx", **base_kwargs),
            SharePointFile(id="3", name="document.docx", **base_kwargs),
            SharePointFile(id="4", name="backup.tmp", **base_kwargs),
            SharePointFile(id="5", name=".DS_Store", **base_kwargs),
            SharePointFile(id="6", name="presentation.pptx", **base_kwargs),
            SharePointFile(id="7", name="~$locked.xlsx", **base_kwargs),
            SharePointFile(id="8", name="data.xlsx", **base_kwargs),
        ]

    def test_filter_excludes_temp_files(self, crawler, sample_files):
        """Test that ~$ prefixed files are excluded."""
        patterns = ["~$*"]
        result = crawler._filter_files(sample_files, patterns)

        names = [f.name for f in result]
        assert "~$temp.docx" not in names
        assert "~$locked.xlsx" not in names
        assert "report.pdf" in names
        assert "document.docx" in names

    def test_filter_excludes_tmp_files(self, crawler, sample_files):
        """Test that .tmp files are excluded."""
        patterns = ["*.tmp"]
        result = crawler._filter_files(sample_files, patterns)

        names = [f.name for f in result]
        assert "backup.tmp" not in names
        assert "report.pdf" in names

    def test_filter_excludes_ds_store(self, crawler, sample_files):
        """Test that .DS_Store files are excluded."""
        patterns = [".DS_Store"]
        result = crawler._filter_files(sample_files, patterns)

        names = [f.name for f in result]
        assert ".DS_Store" not in names
        assert "report.pdf" in names

    def test_filter_multiple_patterns(self, crawler, sample_files):
        """Test filtering with multiple patterns."""
        patterns = ["~$*", "*.tmp", ".DS_Store"]
        result = crawler._filter_files(sample_files, patterns)

        names = [f.name for f in result]
        assert len(result) == 4
        assert "report.pdf" in names
        assert "document.docx" in names
        assert "presentation.pptx" in names
        assert "data.xlsx" in names

    def test_filter_case_insensitive(self, crawler):
        """Test that filtering is case-insensitive."""
        base_kwargs = {
            "size": 1000,
            "mime_type": "text/plain",
            "web_url": "",
            "download_url": None,
            "created_at": None,
            "modified_at": None,
            "created_by": None,
            "modified_by": None,
            "parent_path": "/",
            "site_id": "site-1",
            "drive_id": "drive-1",
        }
        files = [
            SharePointFile(id="1", name="FILE.TMP", **base_kwargs),
            SharePointFile(id="2", name="file.tmp", **base_kwargs),
            SharePointFile(id="3", name="File.Tmp", **base_kwargs),
            SharePointFile(id="4", name="document.txt", **base_kwargs),
        ]
        patterns = ["*.tmp"]
        result = crawler._filter_files(files, patterns)

        names = [f.name for f in result]
        assert len(result) == 1
        assert "document.txt" in names

    def test_filter_empty_patterns_returns_all(self, crawler, sample_files):
        """Test that empty patterns list returns all files."""
        result = crawler._filter_files(sample_files, [])
        assert len(result) == len(sample_files)

    def test_filter_no_matching_patterns(self, crawler, sample_files):
        """Test that non-matching patterns don't filter anything."""
        patterns = ["*.xyz", "*.abc"]
        result = crawler._filter_files(sample_files, patterns)
        assert len(result) == len(sample_files)


class TestSharePointCrawlerSupportedExtensions:
    """Tests for SharePointCrawler.SUPPORTED_EXTENSIONS."""

    @pytest.fixture
    def crawler(self):
        """Create a SharePointCrawler instance."""
        return SharePointCrawler()

    def test_supported_extensions_includes_pdf(self, crawler):
        """Test PDF is supported."""
        assert ".pdf" in crawler.SUPPORTED_EXTENSIONS
        assert crawler.SUPPORTED_EXTENSIONS[".pdf"] == "PDF"

    def test_supported_extensions_includes_word(self, crawler):
        """Test Word documents are supported."""
        assert ".docx" in crawler.SUPPORTED_EXTENSIONS
        assert ".doc" in crawler.SUPPORTED_EXTENSIONS
        assert crawler.SUPPORTED_EXTENSIONS[".docx"] == "DOCX"
        assert crawler.SUPPORTED_EXTENSIONS[".doc"] == "DOC"

    def test_supported_extensions_includes_excel(self, crawler):
        """Test Excel files are supported."""
        assert ".xlsx" in crawler.SUPPORTED_EXTENSIONS
        assert ".xls" in crawler.SUPPORTED_EXTENSIONS

    def test_supported_extensions_includes_powerpoint(self, crawler):
        """Test PowerPoint files are supported."""
        assert ".pptx" in crawler.SUPPORTED_EXTENSIONS
        assert ".ppt" in crawler.SUPPORTED_EXTENSIONS

    def test_supported_extensions_includes_html(self, crawler):
        """Test HTML files are supported."""
        assert ".html" in crawler.SUPPORTED_EXTENSIONS
        assert ".htm" in crawler.SUPPORTED_EXTENSIONS
        assert crawler.SUPPORTED_EXTENSIONS[".html"] == "HTML"
        assert crawler.SUPPORTED_EXTENSIONS[".htm"] == "HTML"

    def test_supported_extensions_includes_text(self, crawler):
        """Test text files are supported."""
        assert ".txt" in crawler.SUPPORTED_EXTENSIONS
        assert crawler.SUPPORTED_EXTENSIONS[".txt"] == "TXT"

    def test_supported_extensions_includes_rtf(self, crawler):
        """Test RTF files are supported."""
        assert ".rtf" in crawler.SUPPORTED_EXTENSIONS


class TestSharePointCrawlerBatchSettings:
    """Tests for SharePointCrawler batch processing settings."""

    @pytest.fixture
    def crawler(self):
        """Create a SharePointCrawler instance."""
        return SharePointCrawler()

    def test_batch_size_is_reasonable(self, crawler):
        """Test that BATCH_SIZE is a reasonable value."""
        assert crawler.BATCH_SIZE > 0
        assert crawler.BATCH_SIZE <= 50  # Not too large to avoid memory issues

    def test_max_concurrent_downloads_is_reasonable(self, crawler):
        """Test that MAX_CONCURRENT_DOWNLOADS is reasonable."""
        assert crawler.MAX_CONCURRENT_DOWNLOADS > 0
        assert crawler.MAX_CONCURRENT_DOWNLOADS <= 20  # Not too many connections

    def test_batch_size_greater_than_concurrent(self, crawler):
        """Test that batch size >= concurrent downloads makes sense."""
        # Batch size should be >= concurrent downloads for efficiency
        assert crawler.BATCH_SIZE >= crawler.MAX_CONCURRENT_DOWNLOADS
